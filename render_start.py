"""h2 on Render - entry point (polling mode, no gradio needed).
Injects TiDB shim + TG proxy before importing Hbi, starts file/web sync,
then runs the bot's polling loop (same as Hbi.__main__).
"""
import os
import sys
import time
import threading
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
log = logging.getLogger("h2_render")

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

# sqlite3 -> TiDB shim MUST be injected before Hbi import
import tidb_shim  # noqa: E402
sys.modules["sqlite3"] = tidb_shim

# Telegram API (Render usually can reach api.telegram.org; keep proxy override)
import telebot  # noqa: E402

proxy = os.environ.get("TG_API_PROXY", "").rstrip("/")
if proxy:
    if not proxy.endswith("/bot"):
        proxy = proxy + "/bot"
    telebot.apihelper.API_URL = proxy + "{0}/{1}"
    telebot.apihelper.FILE_URL = proxy.replace("/bot", "/file/bot") + "{0}/{1}"
    telebot.apihelper.TIMEOUT = 60
    log.info("Outbound API_URL via proxy: %s", telebot.apihelper.API_URL)
else:
    telebot.apihelper.TIMEOUT = 60
    log.info("Using direct api.telegram.org (no proxy)")

# import bot module (registers handlers; init_db()+load_data() at module level)
import Hbi as hx  # noqa: E402

# persistent file store: upload_bots/ mirrored into TiDB
import file_sync  # noqa: E402

file_sync.ensure_schema()
file_sync.migrate_encrypt()
try:
    _restored = file_sync.restore_all(hx.BASE_DIR)
    log.info("File store restored %d files from TiDB", _restored)
except Exception as e:
    log.error("file restore failed: %s", e)
file_sync.start_thread(hx.BASE_DIR)

# web hosting persistence
import web_sync  # noqa: E402

web_sync.ensure_schema()
_web_dir = os.path.join(hx.BASE_DIR, "web_files")
os.makedirs(_web_dir, exist_ok=True)
try:
    _restored_web = web_sync.restore_files(_web_dir)
    log.info("Web files restored %d from TiDB", _restored_web)
except Exception as e:
    log.error("web restore failed: %s", e)
web_sync.start_thread(_web_dir)

# scrub secrets from env so hosted scripts can't leak them
_SENS = ("TOKEN", "TIDB", "SECRET", "PASSWORD", "_PASS", "PASS=", "PROXY",
         "API_KEY", "HF_", "GITHUB", "AWS_", "CLOUDFLARE")
_scrubbed = [k for k in os.environ if any(m in k.upper() for m in _SENS)]
for _k in _scrubbed:
    del os.environ[_k]
log.info("Scrubbed %d secret env vars", len(_scrubbed))


def _keep_alive_self_ping():
    # ping own health route (Flask serve /health on PORT) to avoid free-tier sleep
    import urllib.request
    port = int(os.environ.get("PORT", 8080))
    url = f"http://127.0.0.1:{port}/health"
    while True:
        time.sleep(240)
        try:
            urllib.request.urlopen(url, timeout=8)
        except Exception:
            pass


# add a /health route on Hbi's Flask app
@hx.app.route("/health")
def _h2_health():
    return "ok"


@hx.app.route("/web/<name>/", defaults={"sub": ""})
@hx.app.route("/web/<name>/<path:sub>")
def _h2_web_site(name, sub):
    import os as _os
    import pathlib as _pl
    from flask import send_from_directory, abort
    site_dir = _os.path.join(hx.WEB_FILES_DIR, name)
    if not _os.path.isdir(site_dir):
        abort(404)
    if not sub:
        sub = "index.html"
    rel = _pl.PurePosixPath(sub)
    if rel.is_absolute() or ".." in rel.parts:
        abort(404)
    full = _os.path.join(site_dir, rel.as_posix())
    if not _os.path.isfile(full):
        abort(404)
    return send_from_directory(site_dir, rel.as_posix())


@hx.app.route("/web/")
def _h2_web_index():
    from flask import Response
    rows = "".join(f'<li><a href="{n}/">{n}</a></li>' for n in sorted(hx.web_manifest))
    html = ('<!DOCTYPE html><html><head><meta charset="utf-8"><title>ZEX WEB HOST</title>'
            '<style>body{background:#0b0f1a;color:#7df9ff;font-family:monospace;text-align:center;padding-top:60px}'
            'a{color:#ffd166}ul{list-style:none;padding:0}</style></head>'
            '<body><h1>🌐 ZEX WEB HOST</h1><p>live sites:</p><ul>' + rows + '</ul>'
            '<p style="color:#666">powered by zex hosting bot</p></body></html>')
    return Response(html, mimetype="text/html")


if __name__ == "__main__":
    threading.Thread(target=_keep_alive_self_ping, daemon=True).start()
    log.info("Self-ping keep-alive started (every 240s).")
    hx.keep_alive()
    log.info("Starting polling on Render...")
    try:
        threading.Thread(target=hx._restore_after_reboot, daemon=True).start()
    except Exception as e:
        log.error("reboot restore thread failed: %s", e)
    import requests
    while True:
        try:
            hx.bot.infinity_polling(logger_level=logging.INFO, timeout=60, long_polling_timeout=30)
        except requests.exceptions.ReadTimeout:
            log.warning("ReadTimeout. Restart in 5s...")
            time.sleep(5)
        except requests.exceptions.ConnectionError:
            log.error("ConnectionError. Retry 15s...")
            time.sleep(15)
        except Exception as e:
            log.critical("Polling error: %s", e)
            time.sleep(30)
        finally:
            log.warning("Polling attempt ended, restarting if in loop.")
            time.sleep(1)