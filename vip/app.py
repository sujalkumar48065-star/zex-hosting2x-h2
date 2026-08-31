import asyncio
import os
import sys
import threading
import logging
import time
import urllib.request

os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, 'src')

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger(__name__)

# Persist bot data under the Space's persistent volume so projects/uploads and
# the SQLite fallback survive restarts.
DATA_DIR = os.environ.get('HOSTING_DATA_DIR', '/data/hosting_data')
os.environ['HOSTING_DATA_DIR'] = DATA_DIR
os.makedirs(DATA_DIR, exist_ok=True)
for sub in ('projects', 'logs', 'tmp'):
    os.makedirs(os.path.join(DATA_DIR, sub), exist_ok=True)

# Outbound Telegram Bot API calls (sendMessage, editMessage, setWebhook, ...)
# are routed through a proxy because HF infra cannot reach api.telegram.org
# directly (connections time out from the container). Updates themselves are
# delivered INBOUND via webhook (Telegram -> HF public URL), so there is no
# getUpdates polling and therefore no 409 file-conflict problem.
TG_PROXY = (os.environ.get('TG_API_PROXY') or 'https://tgproxy-pages.pages.dev').strip().rstrip('/')
if TG_PROXY:
    from telegram.ext import ApplicationBuilder
    from telegram._utils.defaultvalue import DefaultValue

    _orig_build = ApplicationBuilder.build

    def _patched_build(self):
        if isinstance(self._base_url, DefaultValue):
            self._base_url = TG_PROXY + '/bot'
        if isinstance(self._base_file_url, DefaultValue):
            self._base_file_url = TG_PROXY + '/file/bot'
        return _orig_build(self)

    ApplicationBuilder.build = _patched_build
    logger.info("Telegram API routed via proxy: %s", TG_PROXY)

import tidb_aiosqlite
import main as bot_module


def run_bot():
    async def _boot():
        ti_enabled = await tidb_aiosqlite.bootstrap()
        logger.info("TiDB async failover: %s",
                    "ENABLED" if ti_enabled else "OFF (local SQLite fallback)")
        await bot_module._run_async()

    try:
        asyncio.run(_boot())
    except Exception as exc:
        logger.error("Bot fatal error: %s", exc, exc_info=True)
def _bot_supervisor():
    """Remote self-healing: if the bot thread dies (crash, exception, poller
    exit), restart it automatically with a short backoff so the panel never
    stays dead until the next manual redeploy."""
    failures = 0
    while True:
        t = threading.Thread(target=run_bot, daemon=True)
        t.start()
        t.join()
        failures += 1
        delay = min(10 * failures, 120)
        logger.error("Bot thread exited (failure #%s); restarting in %ss", failures, delay)
        time.sleep(delay)
        if failures >= 12:
            failures = 0


threading.Thread(target=_bot_supervisor, daemon=True).start()

from flask import Flask, jsonify, request

app = Flask(__name__)


@app.route('/')
def home():
    return 'HOSTING BOT is running 24/7'


@app.route('/webhook/<secret>', methods=['POST'])
def webhook(secret):
    if secret != bot_module.WEBHOOK_SECRET:
        return jsonify(status='invalid_secret'), 403
    payload = request.get_json(silent=True)
    if not payload:
        return jsonify(status='no_payload'), 400
    ok = bot_module.deliver_webhook_update(payload)
    return jsonify(status='ok' if ok else 'processing_failed'), (200 if ok else 503)


@app.route('/health')
def health():
    try:
        db_ok = bot_module.health_db_ok()
    except Exception:
        db_ok = False
    if bot_module.bot_polling_alive():
        return jsonify(status='ok', bot='running', polling=True, db=bool(db_ok))
    if db_ok:
        return jsonify(status='ok', bot='starting', polling=False, db=True)
    return jsonify(status='degraded', bot='restarting', polling=False, db=False)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 7860))

    def keep_alive():
        """Inbuilt uptime robot: periodically hit our own health endpoint so the
        Space never looks idle to HF's auto-sleep watchdog (replaces UptimeRobot).
        Hits both localhost and the public URL so one path keeps working even if
        the other is unreachable. Pings every 60s and logs any failure."""
        public = (os.environ.get('HOST_URL') or 'https://sujajl-788-ghhjj.hf.space').rstrip('/')
        targets = ['http://127.0.0.1:%d/health' % port, public + '/health']
        ok = 0
        while True:
            for target in targets:
                try:
                    urllib.request.urlopen(target, timeout=15).read()
                    ok += 1
                except Exception as exc:
                    ok = 0
                    logger.error("keep-alive ping %s FAILED: %s", target, exc)
            if ok % 20 == 0 and ok > 0:
                logger.info("uptime robot alive, pings ok=%s", ok)
            time.sleep(60)

    threading.Thread(target=keep_alive, daemon=True).start()
    logger.info("Health server + internal keep-alive on port %s", port)
    app.run(host='0.0.0.0', port=port)
