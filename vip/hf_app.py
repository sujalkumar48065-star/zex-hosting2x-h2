import os, sys, threading, logging, time, urllib.request, ssl

os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, 'src')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from dotenv import load_dotenv
load_dotenv()

import main as bot_module

HF_SPACE_URL = os.environ.get('SPACE_URL', 'https://hohjhjj-k.hf.space')

def keep_alive():
    while True:
        try:
            ctx = ssl._create_unverified_context()
            for path in ['/', '/health']:
                try:
                    urllib.request.urlopen(f'{HF_SPACE_URL}{path}', timeout=15, context=ctx)
                except:
                    pass
                time.sleep(2)
            try:
                bot_module.bot.get_me()
            except:
                pass
            logger.info(f'Keep-alive pinged {HF_SPACE_URL}')
        except:
            pass
        time.sleep(240)

threading.Thread(target=keep_alive, daemon=True).start()

def start_bot():
    try:
        bot_module.init_db()
        bot_module.load_data()
        bot_module.tidb_store.init_sync()
        if bot_module.tidb_store.enabled():
            try: bot_module.tidb_store.backup_sqlite(bot_module.DB_PATH)
            except Exception: pass
        bot_module.clear_old_data()
        bot_module.tidb_restore_all()
        bot_module.keep_alive()
        logger.info("Bot started in polling mode via Pages proxy (TiDB self-heal active)")
        while True:
            try:
                bot_module.bot.infinity_polling(timeout=30, long_polling_timeout=30)
            except Exception as e:
                logger.error(f"Polling error: {e}", exc_info=True)
                time.sleep(10)
    except Exception as e:
        logger.error(f"Bot error: {e}", exc_info=True)

threading.Thread(target=start_bot, daemon=True).start()

try:
    import gradio as gr
    with gr.Blocks(title="HostingBot") as demo:
        gr.Markdown("🤖 **HostingBot is running 24/7**")
        gr.Markdown("Powered by Cloudflare Pages proxy")
    demo.launch(server_port=int(os.environ.get('PORT', 7860)))
except:
    from flask import Flask
    app = Flask(__name__)
    @app.route('/')
    def home(): return 'Bot running'
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 7860)))
