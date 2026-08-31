#!/usr/bin/env python3
# render_app.py
# Render.com entry point for the Telegram Hosting Panel.
#
# Runs the bot in WEBHOOK mode on a Render web service:
#   - Flask serves the webhook + health endpoints on $PORT (Render sets it).
#   - Telegram sends updates INBOUND to  https://<service>.onrender.com/webhook/<secret>
#   - Outbound Telegram API calls go DIRECTLY to api.telegram.org (Render can
#     reach it, unlike HuggingFace Spaces), unless TG_API_PROXY is set.
#   - Data persists under the Render Persistent Disk (/var/data) via
#     HOSTING_DATA_DIR, or falls back to TiDB (2-account) if configured.
#   - A keep-alive thread pings /health so the service stays responsive; the
#     render.yaml cron job pings the public URL every 5 min so Render's free
#     web service never sleeps (~15 min idle timeout).

import asyncio
import logging
import os
import sys
import threading
import time
import urllib.request

os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, 'src')

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger(__name__)

# Persist bot data. On Render free there is usually NO persistent disk, so the
# requested mount (/var/data) may not exist or be writable. Try it first, then
# transparently fall back to a guaranteed-writable dir (app root or /tmp) so a
# permissions problem can never crash startup. Note: without a disk the data is
# ephemeral and wipes on redeploy; TiDB (if configured) survives regardless.
_DEFAULT_DATA = '/var/data/hosting_data'
_REQUESTED = os.environ.get('HOSTING_DATA_DIR', _DEFAULT_DATA)


def _resolve_data_dir() -> str:
    candidates = [_REQUESTED]
    if _REQUESTED != _DEFAULT_DATA:
        candidates.append(_DEFAULT_DATA)
    candidates += [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'hosting_data'),
        '/tmp/hosting_data',
    ]
    for cand in candidates:
        try:
            os.makedirs(cand, exist_ok=True)
            probe = os.path.join(cand, '.write_test')
            with open(probe, 'w') as fh:
                fh.write('ok')
            os.remove(probe)
            return cand
        except Exception:
            continue
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'hosting_data')


DATA_DIR = _resolve_data_dir()
os.environ['HOSTING_DATA_DIR'] = DATA_DIR
for sub in ('projects', 'logs', 'tmp'):
    os.makedirs(os.path.join(DATA_DIR, sub), exist_ok=True)
logger.info("HOSTING_DATA_DIR resolved to: %s", DATA_DIR)

# Outbound Telegram Bot API calls go directly to api.telegram.org on Render.
# Set TG_API_PROXY to route via a proxy instead (only for HF-like setups).
TG_PROXY = (os.environ.get('TG_API_PROXY') or '').strip().rstrip('/')
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
else:
    logger.info("Telegram API routed directly to api.telegram.org")

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
    """Remote self-healing: if the bot thread dies (crash, exception, webhook
    loop exit), restart it automatically with a short backoff so the panel never
    stays dead until the next manual deploy."""
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


def _public_base_url() -> str:
    """Resolve the external base URL, preferring Render's auto-injected env vars
    (no manual PUBLIC_BASE_URL needed), then explicit overrides. Returns '' when
    no URL is resolvable."""
    rext = (os.environ.get('RENDER_EXTERNAL_URL') or os.environ.get('RENDER_EXTERNAL_HOSTNAME') or '')
    manual = (os.environ.get('PUBLIC_BASE_URL') or os.environ.get('HOST_URL') or '')
    base = rext or manual
    base = base.strip()
    if not base:
        return ''
    if not base.startswith('http'):
        base = 'https://' + base
    return base.rstrip('/')


# Resolve and publish the public base URL at module level so it is available both
# when run directly and under gunicorn (gunicorn imports this module).
PORT = int(os.environ.get('PORT', 10000))
BASE_URL = _public_base_url()
bot_module.WEBHOOK_SECRET = os.environ.get('HOSTING_WEBHOOK_SECRET', 's3cret_wbhk')
if BASE_URL:
    os.environ.setdefault('PUBLIC_BASE_URL', BASE_URL)
    logger.info("Public base URL: %s (port %s)", BASE_URL, PORT)


def _keep_alive():
    """Inbuilt uptime robot: periodically hit our own health endpoint so the
    Render free web service never looks idle. A localhost hit alone does NOT
    keep Render awake — the ping MUST go out through the load balancer, so we
    always hit the external URL first (using Render's RENDER_EXTERNAL_URL).
    Pings every 60s and logs failures."""
    targets = ['http://127.0.0.1:%d/health' % PORT]
    if BASE_URL:
        targets.append(BASE_URL + '/health')
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


threading.Thread(target=_keep_alive, daemon=True).start()
logger.info("Inbuilt uptime robot started (pings /health every 60s)")

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
    # Direct run (single-process dev / Render when not using gunicorn).
    logger.info("Health server + internal keep-alive on port %s", PORT)
    app.run(host='0.0.0.0', port=PORT)
