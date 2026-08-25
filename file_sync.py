"""h2 file persistence: mirror upload_bots/ into TiDB so hosted files survive
Space restarts/rebuilds. Uses tidb_shim connections (pooling + failover).

- restore_all(): called once at startup - pulls every stored file back to disk
- sync_loop():   daemon thread - every SYNC_INTERVAL upserts new/changed files
                 and deletes rows for removed files
"""
import os
import base64
import threading
import time
import logging

import pymysql
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

log = logging.getLogger("h2_filesync")

SYNC_INTERVAL = 15
MAX_FILE_BYTES = 50 * 1024 * 1024  # skip > 50MB

_ENC_PREFIX = b"ENC1:"
_KEY = None


def _get_key():
    global _KEY
    if _KEY is None:
        raw = os.environ.get("FILE_CRYPT_KEY", "")
        if raw:
            _KEY = base64.urlsafe_b64decode(raw)
    return _KEY


def enc_bytes(data):
    k = _get_key()
    if not k or data.startswith(_ENC_PREFIX):
        return data
    nonce = os.urandom(12)
    return _ENC_PREFIX + nonce + AESGCM(k).encrypt(nonce, bytes(data), None)


def dec_bytes(data):
    if not data.startswith(_ENC_PREFIX):
        return data
    k = _get_key()
    if not k:
        raise RuntimeError("encrypted row but FILE_CRYPT_KEY missing")
    return AESGCM(k).decrypt(data[5:17], data[17:], None)


def migrate_encrypt():
    """One-time pass: encrypt any plaintext blobs already stored."""
    try:
        conn = _connect_retry()
    except Exception as e:
        log.error("migrate_encrypt: db connect failed: %s", e)
        return 0
    n = 0
    try:
        cur = conn.cursor()
        cur.execute("SELECT path, content FROM h2_files")
        for path, content in cur.fetchall():
            if content is None or content.startswith(_ENC_PREFIX):
                continue
            cur.execute(
                "UPDATE h2_files SET content=%s WHERE path=%s",
                (enc_bytes(content), path),
            )
            conn.commit()
            n += 1
        conn.close()
        log.info("migrate_encrypt: encrypted %d existing blobs", n)
    except Exception as e:
        log.error("migrate_encrypt failed: %s", e)
    return n

_SCHEMA = """
CREATE TABLE IF NOT EXISTS h2_files (
  path VARCHAR(512) PRIMARY KEY,
  content LONGBLOB,
  size BIGINT NOT NULL DEFAULT 0,
  mtime DOUBLE NOT NULL DEFAULT 0
)
"""

_stats = {"files": 0, "bytes": 0, "last_sync": None, "last_restore": None,
          "uploads": 0, "deletes": 0, "errors": 0}
_lock = threading.Lock()


def ensure_schema():
    conn = _connect_retry()
    cur = conn.cursor()
    cur.execute(_SCHEMA)
    conn.commit()
    conn.close()


def _connect_retry(attempts=3):
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import tidb_shim
    last = None
    for i in range(attempts):
        try:
            return tidb_shim.connect()
        except Exception as e:
            last = e
            time.sleep(2 * (i + 1))
    raise last


def _walk_files(base_dir):
    root = os.path.join(base_dir, "upload_bots")
    out = []
    if not os.path.isdir(root):
        return out
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        for fn in filenames:
            if fn.endswith(".pyc"):
                continue
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, base_dir).replace(os.sep, "/")
            out.append((rel, full))
    return out


def restore_all(base_dir):
    """Pull all stored files back to disk (called at startup)."""
    try:
        conn = _connect_retry()
    except Exception as e:
        log.error("restore_all: db connect failed: %s", e)
        return 0
    n = 0
    try:
        cur = conn.cursor()
        cur.execute("SELECT path, size, content FROM h2_files")
        for path, size, content in cur.fetchall():
            dest = os.path.join(base_dir, path)
            try:
                need = True
                if os.path.exists(dest) and os.path.getsize(dest) == size:
                    need = False  # already present (same build)
                if need and content is not None:
                    os.makedirs(os.path.dirname(dest), exist_ok=True)
                    with open(dest, "wb") as f:
                        f.write(dec_bytes(content))
                    n += 1
            except Exception as e:
                log.error("restore %s: %s", path, e)
        conn.close()
        with _lock:
            _stats["last_restore"] = time.time()
        log.info("Restored %d files from TiDB", n)
    except pymysql.err.MySQLError as e:
        if "1146" in str(e):  # table missing yet
            log.warning("restore_all: h2_files table missing (first boot)")
        else:
            log.error("restore_all query failed: %s", e)
            with _lock:
                _stats["errors"] += 1
    return n


def sync_once(base_dir):
    """One pass: upsert changed files, delete rows for removed files."""
    entries = _walk_files(base_dir)
    disk = {}
    conn = _connect_retry()
    try:
        # load lightweight index
        cur = conn.cursor()
        cur.execute("SELECT path, size, mtime FROM h2_files")
        index = {p: (s, m) for p, s, m in cur.fetchall()}
        conn.close()

        for rel, full in entries:
            try:
                st = os.stat(full)
            except FileNotFoundError:
                continue
            if st.st_size > MAX_FILE_BYTES:
                continue
            disk[rel] = (st.st_size, st.st_mtime)
            if index.get(rel) == (st.st_size, st.st_mtime):
                continue  # unchanged
            with open(full, "rb") as f:
                blob = f.read()
            conn = _connect_retry()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO h2_files (path, content, size, mtime) VALUES (%s,%s,%s,%s) "
                "ON DUPLICATE KEY UPDATE content=VALUES(content), size=VALUES(size), mtime=VALUES(mtime)",
                (rel, enc_bytes(blob), st.st_size, st.st_mtime),
            )
            conn.commit()
            conn.close()
            with _lock:
                _stats["uploads"] += 1

        # deletions
        gone = [p for p in index if p not in disk]
        for p in gone:
            conn = _connect_retry()
            cur = conn.cursor()
            cur.execute("DELETE FROM h2_files WHERE path = %s", (p,))
            conn.commit()
            conn.close()
            with _lock:
                _stats["deletes"] += 1

        with _lock:
            _stats["files"] = len(disk)
            _stats["bytes"] = sum(s for s, _ in disk.values())
            _stats["last_sync"] = time.time()
    except Exception as e:
        log.error("sync_once error: %s", e)
        with _lock:
            _stats["errors"] += 1


def start_thread(base_dir):
    def loop():
        time.sleep(5)
        while True:
            try:
                sync_once(base_dir)
            except Exception as e:
                log.error("loop: %s", e)
            time.sleep(SYNC_INTERVAL)

    t = threading.Thread(target=loop, daemon=True, name="h2-filesync")
    t.start()
    log.info("File sync thread started (interval %ss)", SYNC_INTERVAL)


def stats():
    with _lock:
        d = dict(_stats)
    if d["last_sync"]:
        d["last_sync_ago_s"] = round(time.time() - d["last_sync"])
    else:
        d["last_sync_ago_s"] = None
    d.pop("last_sync", None)
    if d["last_restore"]:
        d["last_restore_ago_s"] = round(time.time() - d["last_restore"])
    else:
        d["last_restore_ago_s"] = None
    d.pop("last_restore", None)
    return d
