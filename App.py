"""h2 - ZEX HOSTING BOT (@HOSTING2X_ROBOT) - runs inside HF Space 'Hosrrr' (gradio SDK).

Webhook mode (Telegram -> HF URL) + proxied outbound API calls.
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

# 1) sqlite3 -> TiDB shim MUST be injected before HOSTING2X import
import tidb_shim  # noqa: E402
sys.modules["sqlite3"] = tidb_shim

# 2) outbound Telegram API via proxy (HF cannot reach api.telegram.org)
import telebot  # noqa: E402

PROXY = os.environ.get("TG_API_PROXY", "https://tgproxy-pages.pages.dev").rstrip("/")
if not PROXY.endswith("/bot"):
    PROXY = PROXY + "/bot"
telebot.apihelper.API_URL = PROXY
telebot.apihelper.TIMEOUT = 60
log.info("Outbound API_URL: %s", telebot.apihelper.API_URL)

# 3) import bot module (registers handlers; init_db()+load_data() run at module level)
import HOSTING2X as hx  # noqa: E402

BOT = hx.bot
OWNER_ID = hx.OWNER_ID

WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "s3cret_wbhk2")
HOST_URL = os.environ.get("HOST_URL", "").rstrip("/")

from fastapi import FastAPI, Request  # noqa: E402
from fastapi.responses import JSONResponse, PlainTextResponse  # noqa: E402
import uvicorn  # noqa: E402

app = FastAPI()

_state = {"webhook": False, "last_update": 0.0, "updates_ok": 0, "updates_err": 0}
_t0 = time.time()


@app.get("/")
def home():
    return PlainTextResponse("ZEX HOSTING BOT (h2) - @HOSTING2X_ROBOT - RUNNING")


@app.get("/health")
def health():
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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    log.info("Starting uvicorn on 0.0.0.0:%s", port)
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")
