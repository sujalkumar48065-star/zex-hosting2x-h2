#!/usr/bin/env python3
"""
panel_bot.py - Multi-Bot Hosting Panel (On-Demand, Zero Hardcoding)
All messages and comments are in English.
"""

import asyncio
import logging
import os
import shutil
import sys
from datetime import datetime

from telegram import Update, Document
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ======================== CONFIGURATION ========================
BOT_TOKEN = "8887701014:AAHkkSoII_B707f8jwGQBRd2MMCsdV9-MmI"   # Get from @BotFather
OWNER_ID = 8799679469                       # Get from @userinfobot

BASE_DIR = "user_bots"                     # Parent folder for all bots

# Global dictionary to store running subprocesses per bot
processes = {}                             # {bot_name: subprocess}

# ======================== SETUP ========================
os.makedirs(BASE_DIR, exist_ok=True)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ======================== AUTHENTICATION ========================
def is_owner(update: Update) -> bool:
    return update.effective_user.id == OWNER_ID

# ======================== HELPERS ========================
def get_bot_dir(bot_name: str) -> str:
    return os.path.join(BASE_DIR, bot_name)

def get_bot_log_path(bot_name: str) -> str:
    return os.path.join(get_bot_dir(bot_name), "bot.log")

def get_current_bot(context: ContextTypes.DEFAULT_TYPE):
    """Return the currently selected bot name (or None)"""
    return context.user_data.get("current_bot")

def set_current_bot(context: ContextTypes.DEFAULT_TYPE, bot_name: str):
    context.user_data["current_bot"] = bot_name

def get_main_script(context: ContextTypes.DEFAULT_TYPE, bot_name: str):
    return context.user_data.get(f"main_script_{bot_name}")

def set_main_script(context: ContextTypes.DEFAULT_TYPE, bot_name: str, filename: str):
    context.user_data[f"main_script_{bot_name}"] = filename

async def ensure_bot_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check if a bot is selected; if not, send error and return False"""
    bot = get_current_bot(context)
    if bot is None:
        await update.message.reply_text(
            "⚠️ No bot selected. Use `/select_bot <name>` or `/new_bot <name>` first.",
            parse_mode="Markdown"
        )
        return False
    bot_dir = get_bot_dir(bot)
    if not os.path.exists(bot_dir):
        await update.message.reply_text(f"❌ Bot directory `{bot}` does not exist. Please create it with `/new_bot`.")
        set_current_bot(context, None)   # clear invalid selection
        return False
    return True

# ======================== FILE HANDLER ========================
async def handle_uploaded_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Upload .py or requirements.txt to the currently selected bot's folder."""
    if not is_owner(update):
        await update.message.reply_text("⛔ Access Denied.")
        return

    if not await ensure_bot_selected(update, context):
        return

    bot_name = get_current_bot(context)
    doc: Document = update.message.document
    file_name = doc.file_name

    if not (file_name.endswith('.py') or file_name == 'requirements.txt'):
        await update.message.reply_text(
            f"❌ Invalid file type: `{file_name}`\nOnly `.py` or `requirements.txt` allowed.",
            parse_mode="Markdown"
        )
        return

    try:
        file = await doc.get_file()
        dest_path = os.path.join(get_bot_dir(bot_name), file_name)
        await file.download_to_drive(dest_path)
        await update.message.reply_text(
            f"✅ `{file_name}` uploaded successfully to bot `{bot_name}`.",
            parse_mode="Markdown"
        )
        logger.info(f"File {file_name} uploaded to bot {bot_name}")
    except Exception as e:
        await update.message.reply_text(f"❌ Upload failed: `{str(e)}`", parse_mode="Markdown")

# ======================== COMMAND HANDLERS ========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        await update.message.reply_text("⛔ Access Denied.")
        return

    text = (
        "🤖 *Multi‑Bot Hosting Panel* (On‑Demand)\n\n"
        "📌 *How to use:*\n"
        "1. `/new_bot <name>` – create a new bot (folder)\n"
        "2. `/select_bot <name>` – select an existing bot\n"
        "3. Upload `.py` files and `requirements.txt`\n"
        "4. `/set_main <filename.py>` – set the main script\n"
        "5. `/install_deps` – install dependencies\n"
        "6. `/deploy` – start the bot\n\n"
        "🛠 *Available commands:*\n"
        "/start – this menu\n"
        "/new_bot <name> – create new bot\n"
        "/select_bot <name> – select a bot\n"
        "/list_bots – list all bots\n"
        "/delete_bot <name> – delete a bot (all files)\n"
        "/list_files – list files in current bot\n"
        "/set_main <file> – set main script\n"
        "/install_deps – install deps (pip)\n"
        "/deploy – run the bot\n"
        "/stop – stop the bot\n"
        "/status – bot status\n"
        "/logs – last 20 log lines\n"
        "/exec <command> – shell command"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

# ---------- Bot Management ----------
async def new_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        await update.message.reply_text("⛔ Access Denied.")
        return

    if not context.args:
        await update.message.reply_text("⚠️ Please provide a bot name: `/new_bot mybot`", parse_mode="Markdown")
        return

    bot_name = context.args[0].strip()
    # Security: only alphanumeric, underscore, hyphen
    if not bot_name.replace('-', '').replace('_', '').isalnum():
        await update.message.reply_text("❌ Bot name can only contain letters, digits, '-' and '_'.")
        return

    bot_dir = get_bot_dir(bot_name)
    if os.path.exists(bot_dir):
        await update.message.reply_text(f"⚠️ Bot `{bot_name}` already exists.")
        return

    os.makedirs(bot_dir, exist_ok=True)
    set_current_bot(context, bot_name)
    await update.message.reply_text(
        f"✅ Bot `{bot_name}` created and selected. You can now upload files for it.",
        parse_mode="Markdown"
    )

async def select_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        await update.message.reply_text("⛔ Access Denied.")
        return

    if not context.args:
        await update.message.reply_text("⚠️ Please provide a bot name: `/select_bot mybot`", parse_mode="Markdown")
        return

    bot_name = context.args[0].strip()
    bot_dir = get_bot_dir(bot_name)
    if not os.path.exists(bot_dir):
        await update.message.reply_text(f"❌ Bot `{bot_name}` does not exist. Use `/new_bot` to create it.")
        return

    set_current_bot(context, bot_name)
    await update.message.reply_text(f"✅ Now selected: `{bot_name}`. All operations will target this bot.", parse_mode="Markdown")

async def list_bots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        await update.message.reply_text("⛔ Access Denied.")
        return

    try:
        items = os.listdir(BASE_DIR)
        bots = [d for d in items if os.path.isdir(os.path.join(BASE_DIR, d))]
        if not bots:
            await update.message.reply_text("📂 No bots yet. Use `/new_bot` to create one.")
            return
        current = get_current_bot(context)
        msg = "📂 *All bots:*\n"
        for b in bots:
            mark = " ✅ (selected)" if b == current else ""
            msg += f"• `{b}`{mark}\n"
        await update.message.reply_text(msg, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Error listing bots: `{str(e)}`", parse_mode="Markdown")

async def delete_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        await update.message.reply_text("⛔ Access Denied.")
        return

    if not context.args:
        await update.message.reply_text("⚠️ Provide a bot name: `/delete_bot mybot`", parse_mode="Markdown")
        return

    bot_name = context.args[0].strip()
    bot_dir = get_bot_dir(bot_name)
    if not os.path.exists(bot_dir):
        await update.message.reply_text(f"❌ Bot `{bot_name}` does not exist.")
        return

    # Stop if running
    if bot_name in processes and processes[bot_name] and processes[bot_name].returncode is None:
        processes[bot_name].terminate()
        await asyncio.sleep(1)
        if processes[bot_name].returncode is None:
            processes[bot_name].kill()
        del processes[bot_name]

    # Remove directory
    try:
        shutil.rmtree(bot_dir)
        if get_current_bot(context) == bot_name:
            set_current_bot(context, None)
        await update.message.reply_text(f"🗑️ Bot `{bot_name}` deleted completely.")
    except Exception as e:
        await update.message.reply_text(f"❌ Deletion error: `{str(e)}`", parse_mode="Markdown")

# ---------- File Management ----------
async def list_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        await update.message.reply_text("⛔ Access Denied.")
        return

    if not await ensure_bot_selected(update, context):
        return

    bot_name = get_current_bot(context)
    try:
        files = os.listdir(get_bot_dir(bot_name))
        if not files:
            await update.message.reply_text(f"📂 Bot `{bot_name}` has no files.")
            return
        file_list = "\n".join([f"📄 {f}" for f in files])
        await update.message.reply_text(
            f"📂 *Files in `{bot_name}`:*\n\n{file_list}",
            parse_mode="Markdown"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error: `{str(e)}`", parse_mode="Markdown")

async def set_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        await update.message.reply_text("⛔ Access Denied.")
        return

    if not await ensure_bot_selected(update, context):
        return

    if not context.args:
        await update.message.reply_text("⚠️ Provide a filename: `/set_main mybot.py`", parse_mode="Markdown")
        return

    bot_name = get_current_bot(context)
    filename = context.args[0].strip()
    if not filename.endswith('.py'):
        await update.message.reply_text("❌ Only `.py` files can be set as main script.")
        return

    full_path = os.path.join(get_bot_dir(bot_name), filename)
    if not os.path.exists(full_path):
        await update.message.reply_text(f"❌ `{filename}` not found in bot `{bot_name}`.")
        return

    set_main_script(context, bot_name, filename)
    await update.message.reply_text(f"✅ `{filename}` set as main script for bot `{bot_name}`.", parse_mode="Markdown")

# ---------- Dependencies & Deployment ----------
async def install_deps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        await update.message.reply_text("⛔ Access Denied.")
        return

    if not await ensure_bot_selected(update, context):
        return

    bot_name = get_current_bot(context)
    req_path = os.path.join(get_bot_dir(bot_name), "requirements.txt")
    if not os.path.exists(req_path):
        await update.message.reply_text(f"❌ `requirements.txt` not found in bot `{bot_name}`.")
        return

    await update.message.reply_text(f"📦 Installing dependencies for `{bot_name}`... Please wait.")

    try:
        proc = await asyncio.create_subprocess_shell(
            f"pip install -r {req_path}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        out = stdout.decode().strip() or stderr.decode().strip()
        if out:
            if len(out) > 3000:
                out = out[:3000] + "\n... (truncated)"
            await update.message.reply_text(
                f"✅ *Installation completed:*\n\n```\n{out}\n```",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text("✅ Installation successful (no output).")
    except Exception as e:
        await update.message.reply_text(f"❌ Installation failed: `{str(e)}`", parse_mode="Markdown")

async def deploy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        await update.message.reply_text("⛔ Access Denied.")
        return

    if not await ensure_bot_selected(update, context):
        return

    bot_name = get_current_bot(context)
    main_script = get_main_script(context, bot_name)
    if not main_script:
        await update.message.reply_text(f"❌ Main script not set for `{bot_name}`. Use `/set_main`.")
        return

    script_path = os.path.join(get_bot_dir(bot_name), main_script)
    if not os.path.exists(script_path):
        await update.message.reply_text(f"❌ Script `{main_script}` not found in `{bot_name}`.")
        return

    # Stop previous instance if running
    if bot_name in processes and processes[bot_name] and processes[bot_name].returncode is None:
        processes[bot_name].terminate()
        await asyncio.sleep(2)
        if processes[bot_name].returncode is None:
            processes[bot_name].kill()
        await update.message.reply_text(f"🔄 Stopped old instance of `{bot_name}`.")

    log_path = get_bot_log_path(bot_name)
    log_fp = open(log_path, "a")
    log_fp.write(f"\n\n--- STARTED AT {datetime.now()} ---\n")
    log_fp.flush()

    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable, script_path,
            stdout=log_fp,
            stderr=log_fp,
            cwd=get_bot_dir(bot_name)
        )
        processes[bot_name] = proc
        await update.message.reply_text(
            f"✅ Bot `{bot_name}` is now *RUNNING* (PID: {proc.pid})\n"
            f"📄 Check logs with `/logs`.",
            parse_mode="Markdown"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Deployment failed: `{str(e)}`", parse_mode="Markdown")

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        await update.message.reply_text("⛔ Access Denied.")
        return

    if not await ensure_bot_selected(update, context):
        return

    bot_name = get_current_bot(context)
    proc = processes.get(bot_name)
    if proc is None or proc.returncode is not None:
        await update.message.reply_text(f"ℹ️ Bot `{bot_name}` is not running.")
        return

    proc.terminate()
    await asyncio.sleep(2)
    if proc.returncode is None:
        proc.kill()
    if bot_name in processes:
        del processes[bot_name]
    await update.message.reply_text(f"🛑 Bot `{bot_name}` (PID: {proc.pid}) stopped.")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        await update.message.reply_text("⛔ Access Denied.")
        return

    if not await ensure_bot_selected(update, context):
        return

    bot_name = get_current_bot(context)
    main_script = get_main_script(context, bot_name)
    msg = f"📌 *Bot:* `{bot_name}`\n"
    msg += f"📌 *Main script:* `{main_script if main_script else 'Not set'}`\n"

    proc = processes.get(bot_name)
    if proc is None:
        msg += "📌 *Status:* ❌ `Never started`"
    elif proc.returncode is None:
        msg += f"📌 *Status:* ✅ `RUNNING` (PID: {proc.pid})"
    else:
        msg += f"📌 *Status:* ❌ `Stopped` (Exit Code: {proc.returncode})"

    await update.message.reply_text(msg, parse_mode="Markdown")

async def logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        await update.message.reply_text("⛔ Access Denied.")
        return

    if not await ensure_bot_selected(update, context):
        return

    bot_name = get_current_bot(context)
    log_path = get_bot_log_path(bot_name)
    try:
        with open(log_path, "r") as f:
            lines = f.readlines()
            last_lines = lines[-20:] if len(lines) > 20 else lines
            log_text = "".join(last_lines)
        if not log_text.strip():
            await update.message.reply_text(f"ℹ️ Log file for `{bot_name}` is empty.")
            return
        if len(log_text) > 4000:
            log_text = log_text[:4000] + "\n... (truncated)"
        await update.message.reply_text(
            f"📜 *Last 20 lines of `{bot_name}` logs:*\n\n```\n{log_text}\n```",
            parse_mode="Markdown"
        )
    except FileNotFoundError:
        await update.message.reply_text(f"ℹ️ No log file found for `{bot_name}` (run `/deploy` first).")
    except Exception as e:
        await update.message.reply_text(f"❌ Log read error: `{str(e)}`", parse_mode="Markdown")

# ---------- Shell Command ----------
async def exec_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        await update.message.reply_text("⛔ Access Denied.")
        return

    if not context.args:
        await update.message.reply_text("⚠️ Provide a command: `/exec ls -la`", parse_mode="Markdown")
        return

    command = " ".join(context.args)
    await update.message.reply_text(f"⚙️ Running: `{command}`")
    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        output = stdout.decode().strip() or stderr.decode().strip()
        if len(output) > 4000:
            output = output[:4000] + "\n... (truncated)"
        await update.message.reply_text(f"📤 *Output:*\n\n```\n{output}\n```", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: `{str(e)}`", parse_mode="Markdown")

# ======================== MAIN ========================
def main():
    application = Application.builder().token(BOT_TOKEN).build()

    # Command Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("new_bot", new_bot))
    application.add_handler(CommandHandler("select_bot", select_bot))
    application.add_handler(CommandHandler("list_bots", list_bots))
    application.add_handler(CommandHandler("delete_bot", delete_bot))
    application.add_handler(CommandHandler("list_files", list_files))
    application.add_handler(CommandHandler("set_main", set_main))
    application.add_handler(CommandHandler("install_deps", install_deps))
    application.add_handler(CommandHandler("deploy", deploy))
    application.add_handler(CommandHandler("stop", stop))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("logs", logs))
    application.add_handler(CommandHandler("exec", exec_command))

    # File Upload Handler
    application.add_handler(MessageHandler(filters.Document.ALL, handle_uploaded_files))

    logger.info("🤖 Multi-Bot Panel is starting...")
    print("✅ Multi-Bot Panel LIVE! Send /start on Telegram.")
    application.run_polling()

if __name__ == "__main__":
    main()