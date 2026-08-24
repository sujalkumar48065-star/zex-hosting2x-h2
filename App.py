"""h2 - ZEX HOSTING BOT (@HOSTING2X_ROBOT) - HF Space 'Hosrrr' (gradio SDK / ZeroGPU).

Uses gradio 6 Server mode: FastAPI subclass with custom routes (/health,
/webhook/<secret>) + launch() so the ZeroGPU startup check passes.
Storage: TiDB (same accounts/db as h1) via sqlite3 shim.
"""
import os
import sys
import time
import threading
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
log = logging.getLogger("h2_app")

os.environ.setdefault("PORT", "7860")
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

# sqlite3 -> TiDB shim MUST be injected before HOSTING2X import
import tidb_shim  # noqa: E402
sys.modules["sqlite3"] = tidb_shim

# outbound Telegram API via proxy (HF cannot reach api.telegram.org)
import telebot  # noqa: E402

PROXY = os.environ.get("TG_API_PROXY", "https://tgproxy-pages.pages.dev").rstrip("/")
if not PROXY.endswith("/bot"):
    PROXY = PROXY + "/bot"
# pyTelegramBotAPI >= 4.x builds URLs via API_URL.format(token, method_name)
telebot.apihelper.API_URL = PROXY + "{0}/{1}"
telebot.apihelper.FILE_URL = PROXY.replace("/bot", "/file/bot") + "{0}/{1}"
telebot.apihelper.TIMEOUT = 60
log.info("Outbound API_URL: %s", telebot.apihelper.API_URL)

# import bot module (registers handlers; init_db()+load_data() run at module level)
import HOSTING2X as hx  # noqa: E402

BOT = hx.bot
OWNER_ID = hx.OWNER_ID

# persistent file store: upload_bots/ mirrored into TiDB
import file_sync  # noqa: E402

file_sync.ensure_schema()
_restored = file_sync.restore_all(hx.BASE_DIR)
log.info("File store restored %d files from TiDB", _restored)
file_sync.start_thread(hx.BASE_DIR)

WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "s3cret_wbhk2")
HOST_URL = os.environ.get("HOST_URL", "").rstrip("/")

# --- scrub secrets out of process environment (all modules above already
#     captured their values) so hosted scripts can't leak them via
#     os.environ OR /proc/<pid>/environ ---
_SENS = ("TOKEN", "TIDB", "SECRET", "PASSWORD", "_PASS", "PASS=", "PROXY",
         "API_KEY", "HF_", "GITHUB", "AWS_", "CLOUDFLARE")
_scrubbed = [k for k in os.environ if any(m in k.upper() for m in _SENS)]
for _k in _scrubbed:
    del os.environ[_k]
log.info("Scrubbed %d secret env vars from process: %s", len(_scrubbed),
         [k.split('_')[0] + '_***' for k in _scrubbed])

_state = {"webhook": False, "last_update": 0.0, "updates_ok": 0, "updates_err": 0}
_t0 = time.time()


def _setup_webhook():
    if not HOST_URL:
        log.warning("HOST_URL not set - skipping webhook registration")
        return
    url = f"{HOST_URL}/webhook/{WEBHOOK_SECRET}"
    for attempt in range(1, 13):
        try:
            me = BOT.get_me()
            log.info("getMe OK: @%s (attempt %s)", me.username, attempt)
            BOT.delete_webhook(drop_pending_updates=False)
            ok = BOT.set_webhook(url=url, allowed_updates=["message", "callback_query", "edited_message"],
                                 drop_pending_updates=False)
            if ok:
                _state["webhook"] = True
                log.info("Webhook SET: %s", url)
                try:
                    BOT.send_message(OWNER_ID, "✅ h2 (@%s) live ho gaya — webhook connected." % me.username)
                except Exception as e:
                    log.warning("startup notify failed: %s", e)
                return
        except Exception as e:
            log.warning("webhook setup attempt %s failed: %s", attempt, e)
        time.sleep(5)


threading.Thread(target=_setup_webhook, daemon=True).start()


# ---------------- gradio 6 Server mode ---------------------------------------
from gradio import Server  # noqa: E402
from fastapi.responses import JSONResponse, PlainTextResponse  # noqa: E402
from fastapi import Request  # noqa: E402

app = Server()


@app.get("/")
async def home():
    return PlainTextResponse("ZEX HOSTING BOT (h2) - @HOSTING2X_ROBOT - RUNNING")


@app.get("/health")
async def health():
    db_ok, db_msg = tidb_shim.ping()
    return JSONResponse({
        "bot": "running" if _state["webhook"] else "starting",
        "webhook_set": _state["webhook"],
        "db": db_ok,
        "db_msg": db_msg,
        "updates_ok": _state["updates_ok"],
        "updates_err": _state["updates_err"],
        "last_update_ago_s": round(time.time() - _state["last_update"]) if _state["last_update"] else None,
        "uptime_s": round(time.time() - _t0),
        "filesync": file_sync.stats(),
    })


@app.post("/webhook/{secret}")
async def webhook(secret: str, request: Request):
    if secret != WEBHOOK_SECRET:
        return JSONResponse({"ok": False}, status_code=403)
    try:
        data = await request.body()
        update = telebot.types.Update.de_json(data.decode("utf-8"))
        BOT.process_new_updates([update])
        _state["updates_ok"] += 1
        _state["last_update"] = time.time()
        return JSONResponse({"ok": True})
    except Exception as e:
        _state["updates_err"] += 1
        log.error("webhook processing error: %s", e, exc_info=True)
        return JSONResponse({"ok": False})


def _status_impl(dummy: str = "") -> str:
    db_ok, db_msg = tidb_shim.ping()
    return (f"h2 @{BOT.username if _state['webhook'] else 'starting'} | "
            f"db={db_ok} ({db_msg}) | updates_ok={_state['updates_ok']} | "
            f"updates_err={_state['updates_err']}")


_status_fn = _status_impl
if os.environ.get("SPACES_ZERO_GPU") == "1":
    try:
        import spaces

        _status_fn = spaces.GPU(_status_impl)
        log.info("ZeroGPU decorator applied to status_api impl")
    except Exception as e:
        log.warning("ZeroGPU decorate failed: %s", e)


@app.api(name="status")
def status_api(dummy: str = "") -> str:
    return _status_fn(dummy)


log.info("Server mode ready: routes /, /health, /webhook/{secret} + gpu api 'status'")

if __name__ == "__main__":
    app.launch(server_name="0.0.0.0", server_port=int(os.environ.get("PORT", 7860)), show_error=True)
