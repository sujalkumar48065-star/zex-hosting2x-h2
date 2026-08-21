"""Drop-in sqlite3 -> TiDB (MySQL) shim for HOSTING2X deployment.

Inject with:  sys.modules['sqlite3'] = tidb_shim   (before importing HOSTING2X)
Translates SQLite dialect SQL to MySQL and routes every query to
TiDB Cloud Serverless with dual-account failover (same accounts as h1).
"""
import logging
import os
import threading
import time

import pymysql
from pymysql.err import OperationalError, InterfaceError

log = logging.getLogger("tidb_shim")

DB_DEFAULT = os.getenv("TIDB_DEFAULT_DB", "zex_hosting")

def _acct(prefix):
    return {
        "host": os.getenv(prefix + "_HOST"),
        "port": int(os.getenv(prefix + "_PORT", "4000")),
        "user": os.getenv(prefix + "_USER"),
        "password": os.getenv(prefix + "_PASS"),
        "database": os.getenv(prefix + "_DB", DB_DEFAULT),
    }

def _load_accounts():
    out = []
    for p in ("TIDB1", "TIDB2"):
        a = _acct(p)
        if a["host"] and a["user"] and a["password"]:
            out.append(a)
    return out

_ACCOUNTS = _load_accounts()
_active = [0]
_switch_lock = threading.Lock()

FAILOVER_CODES = {2002, 2003, 2006, 2013, 2048, 2055, 4031}


class Error(Exception):
    pass


class IntegrityError(Error):
    pass


def _translate(sql):
    s = sql
    if "INSERT OR IGNORE INTO" in s:
        s = s.replace("INSERT OR IGNORE INTO", "INSERT IGNORE INTO")
    if "INSERT OR REPLACE INTO" in s:
        s = s.replace("INSERT OR REPLACE INTO", "REPLACE INTO")
    if "AUTOINCREMENT" in s:
        # id INTEGER PRIMARY KEY AUTOINCREMENT -> id BIGINT AUTO_INCREMENT PRIMARY KEY
        s = s.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "BIGINT AUTO_INCREMENT PRIMARY KEY")
    if "INTEGER PRIMARY KEY" in s:
        s = s.replace("INTEGER PRIMARY KEY", "BIGINT PRIMARY KEY")
    if "TEXT PRIMARY KEY" in s:
        s = s.replace("TEXT PRIMARY KEY", "VARCHAR(190) PRIMARY KEY")
    # composite PK columns declared as TEXT need a key length in MySQL
    for col in ("file_name", "channel_id"):
        s = s.replace(f"{col} TEXT", f"{col} VARCHAR(190)")
    if "?" in s:
        s = s.replace("?", "%s")
    return s


def _connect_account(idx):
    a = _ACCOUNTS[idx]
    return pymysql.connect(
        host=a["host"], port=a["port"], user=a["user"], password=a["password"],
        database=a["database"], connect_timeout=15,
        ssl_verify_cert=True, ssl_verify_identity=True,
        charset="utf8mb4", autocommit=False,
    )


def _raw_connect():
    if not _ACCOUNTS:
        raise Error("No TiDB credentials configured (TIDB1_*/TIDB2_*)")
    idx = _active[0]
    try:
        return _connect_account(idx)
    except (OperationalError, InterfaceError) as e:
        code = e.args[0] if e.args else None
        other = (idx + 1) % len(_ACCOUNTS)
        log.warning("TiDB account #%s failed (%s) - switching to #%s", idx + 1, code, other + 1)
        with _switch_lock:
            if _active[0] == idx:
                _active[0] = other
        return _connect_account(other)


class Cursor:
    def __init__(self, conn):
        self._conn = conn
        self._cur = None
        self.lastrowid = None

    def execute(self, sql, params=None):
        mysql_sql = _translate(sql)
        try:
            self._cur = self._conn._db.cursor()
            self._cur.execute(mysql_sql, params or None)
            self.lastrowid = getattr(self._cur, "lastrowid", None)
        except (OperationalError, InterfaceError) as e:
            code = e.args[0] if e.args else None
            if code in FAILOVER_CODES:
                other = (_active[0] + 1) % len(_ACCOUNTS) if _ACCOUNTS else 0
                with _switch_lock:
                    _active[0] = other
                log.warning("Query failed on account #%s (%s) - retrying on #%s",
                            _active[0] + 1 if _ACCOUNTS else "?", code, other + 1)
                new = _raw_connect()
                old = self._conn._db
                try:
                    old.close()
                except Exception:
                    pass
                self._conn._db = new
                self._cur = new.cursor()
                self._cur.execute(mysql_sql, params or None)
            else:
                raise
        return self

    def fetchall(self):
        return self._cur.fetchall() if self._cur else []

    def fetchone(self):
        return self._cur.fetchone() if self._cur else None

    def close(self):
        if self._cur:
            try:
                self._cur.close()
            except Exception:
                pass


class Connection:
    def __init__(self):
        self._db = _raw_connect()

    def cursor(self, *a, **k):
        return Cursor(self)

    def commit(self):
        try:
            self._db.commit()
        except Exception as e:
            log.error("commit error: %s", e)

    def rollback(self):
        try:
            self._db.rollback()
        except Exception:
            pass

    def close(self):
        try:
            self._db.close()
        except Exception:
            pass


def connect(path=None, check_same_thread=False, *a, **k):
    return Connection()


# --- health helper for /health endpoint ---
def ping():
    try:
        c = connect()
        cur = c.cursor()
        cur.execute("SELECT 1")
        cur.fetchall()
        c.close()
        return True, "ok"
    except Exception as e:
        return False, str(e)[:120]


# compatibility bits some code paths touch
paramstyle = "qmark"
threadsafety = 3
apilevel = "2.0"
version = "tidb-shim-1.0"
