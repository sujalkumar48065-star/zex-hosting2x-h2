"""h2 web hosting persistence: mirror web_files/ + web_sites.json into TiDB
so hosted websites survive Space restarts. Uses tidb_shim connections.
"""
import os
import json
import threading
import time
import logging

import pymysql

log = logging.getLogger("h2_websync")

SYNC_INTERVAL = 30

_SCHEMA_MANIFEST = """
CREATE TABLE IF NOT EXISTS web_manifest (
  name VARCHAR(255) PRIMARY KEY,
  data TEXT NOT NULL
)"""

_SCHEMA_FILES = """
CREATE TABLE IF NOT EXISTS web_files_data (
  name VARCHAR(255) NOT NULL,
  filename VARCHAR(512) NOT NULL,
  content LONGBLOB,
  PRIMARY KEY (name, filename)
)"""

_stats = {"sites": 0, "files": 0, "last_sync": None, "last_restore": None,
          "uploads": 0, "deletes": 0, "errors": 0}
_lock = threading.Lock()


def ensure_schema():
    conn = _connect_retry()
    cur = conn.cursor()
    cur.execute(_SCHEMA_MANIFEST)
    cur.execute(_SCHEMA_FILES)
    conn.commit()
    conn.close()


def _connect_retry(attempts=3):
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


def restore_manifest():
    """Pull web_manifest from TiDB into local web_sites.json."""
    try:
        conn = _connect_retry()
    except Exception as e:
        log.error("restore_manifest: db connect failed: %s", e)
        return {}
    manifest = {}
    try:
        cur = conn.cursor()
        cur.execute("SELECT name, data FROM web_manifest")
        for name, data in cur.fetchall():
            try:
                manifest[name] = json.loads(data)
            except Exception:
                pass
        conn.close()
        with _lock:
            _stats["last_restore"] = time.time()
        log.info("Restored %d web sites from TiDB", len(manifest))
    except pymysql.err.MySQLError as e:
        if "1146" in str(e):
            log.warning("restore_manifest: tables missing (first boot)")
        else:
            log.error("restore_manifest failed: %s", e)
            with _lock:
                _stats["errors"] += 1
    return manifest


def restore_files(web_files_dir):
    """Pull all stored web files from TiDB to disk."""
    try:
        conn = _connect_retry()
    except Exception as e:
        log.error("restore_files: db connect failed: %s", e)
        return 0
    n = 0
    try:
        cur = conn.cursor()
        cur.execute("SELECT name, filename, content FROM web_files_data")
        for name, filename, content in cur.fetchall():
            if content is None:
                continue
            dest = os.path.join(web_files_dir, name, filename)
            try:
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                with open(dest, "wb") as f:
                    f.write(content)
                n += 1
            except Exception as e:
                log.error("restore_files %s/%s: %s", name, filename, e)
        conn.close()
        log.info("Restored %d web files from TiDB", n)
    except pymysql.err.MySQLError as e:
        if "1146" in str(e):
            log.warning("restore_files: table missing")
        else:
            log.error("restore_files failed: %s", e)
            with _lock:
                _stats["errors"] += 1
    return n


def save_manifest(manifest):
    """Upsert entire manifest to TiDB."""
    try:
        conn = _connect_retry()
        cur = conn.cursor()
        for name, data in manifest.items():
            cur.execute(
                "INSERT INTO web_manifest (name, data) VALUES (%s, %s) "
                "ON DUPLICATE KEY UPDATE data=VALUES(data)",
                (name, json.dumps(data)),
            )
        conn.commit()
        conn.close()
    except Exception as e:
        log.error("save_manifest failed: %s", e)
        with _lock:
            _stats["errors"] += 1


def sync_files(web_files_dir):
    """One pass: upsert all web files to TiDB, delete orphans."""
    entries = {}
    if os.path.isdir(web_files_dir):
        for site_name in os.listdir(web_files_dir):
            site_dir = os.path.join(web_files_dir, site_name)
            if not os.path.isdir(site_dir):
                continue
            for root, _, files in os.walk(site_dir):
                for fn in files:
                    if fn.endswith(".pyc"):
                        continue
                    full = os.path.join(root, fn)
                    rel = os.path.relpath(full, web_files_dir).replace(os.sep, "/")
                    try:
                        st = os.stat(full)
                        entries[rel] = (site_name, fn, full, st.st_size, st.st_mtime)
                    except FileNotFoundError:
                        continue
    try:
        conn = _connect_retry()
        cur = conn.cursor()
        cur.execute("SELECT name, filename FROM web_files_data")
        db_keys = {(r[0], r[1]) for r in cur.fetchall()}
        conn.close()

        uploaded = 0
        for rel, (site_name, fn, full, size, mtime) in entries.items():
            with open(full, "rb") as f:
                blob = f.read()
            conn = _connect_retry()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO web_files_data (name, filename, content) VALUES (%s, %s, %s) "
                "ON DUPLICATE KEY UPDATE content=VALUES(content)",
                (site_name, fn, blob),
            )
            conn.commit()
            conn.close()
            uploaded += 1

        disk_keys = {(s, f) for s, f, _, _, _ in entries.values()}
        orphans = db_keys - disk_keys
        for site_name, fn in orphans:
            conn = _connect_retry()
            cur = conn.cursor()
            cur.execute("DELETE FROM web_files_data WHERE name=%s AND filename=%s", (site_name, fn))
            conn.commit()
            conn.close()

        with _lock:
            _stats["files"] = len(entries)
            _stats["sites"] = len(set(s for s, _, _, _, _ in entries.values()))
            _stats["uploads"] += uploaded
            _stats["deletes"] += len(orphans)
            _stats["last_sync"] = time.time()
    except Exception as e:
        log.error("sync_files error: %s", e)
        with _lock:
            _stats["errors"] += 1


def start_thread(web_files_dir):
    def loop():
        time.sleep(10)
        while True:
            try:
                sync_files(web_files_dir)
            except Exception as e:
                log.error("websync loop: %s", e)
            time.sleep(SYNC_INTERVAL)

    t = threading.Thread(target=loop, daemon=True, name="h2-websync")
    t.start()
    log.info("Web sync thread started (interval %ss)", SYNC_INTERVAL)


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
