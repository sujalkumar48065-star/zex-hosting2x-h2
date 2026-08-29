# -*- coding: utf-8 -*-
import telebot
import subprocess
import os
import zipfile
import io
import tempfile
import shutil
from telebot import types
import time
from datetime import datetime, timedelta
import psutil
import sqlite3
import json
import logging
import signal
import sys

for _pkg in ["psutil","requests","pyTelegramBotAPI","flask"]:
    try: __import__(_pkg.replace("pyTelegramBotAPI","telebot"))
    except ImportError: subprocess.run([sys.executable,"-m","pip","install",_pkg],capture_output=True)
import atexit
import requests
import threading
import re
def lilm_font(text):
    if not isinstance(text, str):
        return text

    links = re.findall(r'https?://\S+', text)
    users = re.findall(r'@\w+', text)
    cmds  = re.findall(r'/\w+', text)

    # placeholders: control chars + digits only (letters would get font-mangled)
    for i, l in enumerate(links):
        text = text.replace(l, f"\x01{1000 + i}\x02")

    for i, u in enumerate(users):
        text = text.replace(u, f"\x01{2000 + i}\x02")

    for i, c in enumerate(cmds):
        text = text.replace(c, f"\x01{3000 + i}\x02")

    normal = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    cute   = "ᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘǫʀꜱᴛᴜᴠᴡxʏᴢᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘǫʀꜱᴛᴜᴠᴡxʏᴢ"

    text = text.translate(str.maketrans(normal, cute))

    for i, l in enumerate(links):
        text = text.replace(f"\x01{1000 + i}\x02", l)

    for i, u in enumerate(users):
        text = text.replace(f"\x01{2000 + i}\x02", u)

    for i, c in enumerate(cmds):
        text = text.replace(f"\x01{3000 + i}\x02", c)

    return text


def _t(s):
    MAP={'a':'\u1D00','b':'\u0299','c':'\u1D04','d':'\u1D05','e':'\u1D07','f':'\ua730','g':'\u0262','h':'\u029c','i':'\u026a','j':'\u1d0a','k':'\u1d0b','l':'\u029f','m':'\u1d0d','n':'\u0274','o':'\u1d0f','p':'\u1d18','q':'\u01eb','r':'\u0280','s':'\ua731','t':'\u1d1b','u':'\u1d1c','v':'\u1d20','w':'\u1d21','x':'x','y':'\u028f','z':'\u1d22'}
    toks = re.findall(r'https?://\S+|@\w+|t\.me/\S+|[\w-]+\.netlify\.app\S*', str(s))
    for i, tok in enumerate(toks):
        s = s.replace(tok, f'\x00{i}\x00')
    out = ''.join(MAP.get(ch,ch) for ch in s)
    for i, tok in enumerate(toks):
        out = out.replace(f'\x00{i}\x00', tok)
    return out

sc_owner="👑 "+_t("developer")
sc_admin="🛡️ "+_t("admin")
sc_premium="💎 "+_t("premium")
sc_free="💠 "+_t("free user")
sc_free_expired="💠 "+_t("free (expired)")

# --- Flask Keep Alive ---
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "ZEX HOSTING BOT"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()
    print("Flask Keep-Alive server started.")
# --- End Flask Keep Alive ---

# --- Configuration (hardcoded, single-file setup) ---
TOKEN = os.environ.get('HOSTING2X_BOT_TOKEN', '8791924525:AAEgEU5gQ43hZrF_78VRGbWYvlrgeOyYh3A')
OWNER_ID = int(os.environ.get('OWNER_ID', '8799679469'))
ADMIN_ID = OWNER_ID
YOUR_USERNAME = '@duifioookn2'
UPDATE_CHANNEL = 'https://t.me/MIKKU_ERA'
NETLIFY_TOKEN = os.environ.get('NETLIFY_TOKEN', 'nfp_CgbbQNg4VSdyTTBVPQcF95w1rhiESKJn2917')

# --- GROK AI SECURITY KEYS (3 failover: 1 fail -> 2 -> 3) ---
GROK_KEYS = [
    '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',
    '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',
    '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'
]  # <- Groq API keys (failover: key1 → key2 → key3 → local fallback)
GROK_API = 'https://api.groq.com/openai/v1/chat/completions'
GROK_MODEL = 'allam-2-7b'
NETLIFY_API = 'https://api.netlify.com/api/v1'
WEB_FREE_LIMIT = 1  # free users ki website limit
NETLIFY_MAIN_SITE = 'hosting-2xbot'  # <- fallback only (https://hosting-2xbot.netlify.app/<sitename>)
RENDER_WEB_URL = os.environ.get('RENDER_WEB_URL', '').rstrip('/')  # e.g. https://zex-hosting2x.onrender.com

# Limits
FREE_USER_LIMIT = 2
SUBSCRIBED_USER_LIMIT = 100
ADMIN_LIMIT = 9999
OWNER_LIMIT = float('inf')

# --- Hosting Bot Version / Runtime metadata ---
BOT_VERSION = '1.0.0'
BOT_START_TIME = time.time()

# Folder setup
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_BOTS_DIR = os.path.join(BASE_DIR, 'upload_bots')
IROTECH_DIR = os.path.join(BASE_DIR, 'inf')
DATABASE_PATH = os.path.join(IROTECH_DIR, 'bot_data.db')

# Create necessary directories
os.makedirs(UPLOAD_BOTS_DIR, exist_ok=True)
os.makedirs(IROTECH_DIR, exist_ok=True)

# Initialize bot
bot = telebot.TeleBot(TOKEN)

# --- Global Blockquote Wrapper (har message colored quote me) ---
def _bq(text):
    t = str(text)
    t = t.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    t = re.sub(r'```(.*?)```', lambda m: '<pre>'+m.group(1)+'</pre>', t, flags=re.S)
    t = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', t, flags=re.S)
    t = re.sub(r'`([^`\n]+)`', r'<code>\1</code>', t)
    return '<blockquote>' + t + '</blockquote>'

_orig_send_message = bot.send_message
def _quoted_send_message(*args, **kwargs):
    if len(args) >= 2:
        args = (args[0], _bq(args[1])) + args[2:]
    elif 'text' in kwargs:
        kwargs['text'] = _bq(kwargs['text'])
    kwargs['parse_mode'] = 'HTML'
    return _orig_send_message(*args, **kwargs)
bot.send_message = _quoted_send_message

_orig_edit_message_text = bot.edit_message_text
def _quoted_edit_message_text(*args, **kwargs):
    if len(args) >= 1 and isinstance(args[0], str):
        args = (_bq(args[0]),) + args[1:]
    elif 'text' in kwargs:
        kwargs['text'] = _bq(kwargs['text'])
    kwargs['parse_mode'] = 'HTML'
    return _orig_edit_message_text(*args, **kwargs)
bot.edit_message_text = _quoted_edit_message_text
# --- End Global Blockquote Wrapper ---
telebot.apihelper.TIMEOUT = 120
# 👇 FINAL LAYER PATCH
original_send = bot.send_message

def send_message(chat_id, text, *args, **kwargs):
    if isinstance(text, str):
        text = lilm_font(text)
    return original_send(chat_id, text, *args, **kwargs)

bot.send_message = send_message

# --- Data structures ---
bot_scripts = {}
user_subscriptions = {}
user_files = {}
active_users = set()
admin_ids = {ADMIN_ID, OWNER_ID}
banned_users = set()
user_limits = {}  # Custom limits per user
bot_locked = False

# --- Manual Modules Installation System ---
pending_modules = {}  # {user_id: {module_name: package_name}}
manual_install_requests = {}  # {admin_id: {user_id: {module_name: package_name}}}

# --- Mandatory Channels/Groups ---
mandatory_channels = {}  # {channel_id: {'username': 'channel_username', 'name': 'Channel Name'}}

# Store pending ZIP files for approval
pending_zip_files = {}  # {user_id: {file_name: file_content}}

# --- Web Hosting State ---
web_sessions = {}     # {user_id: {'stage':'file'|'name', ...}}
deploy_sessions = {}  # {user_id: True} - script upload armed via DEPLOY button only
web_pending = {}      # {approval_key: {...}} waiting for admin decision
_web_counter = [0]

# --- Security Settings ---
SECURITY_CONFIG = {
    'blocked_modules': ['os.system', 'os', 'zipfile', 'subprocess.Popen', 'subprocess', 'eval', 'exec','compile', '__import__'],
    'max_file_size': 20 * 1024 * 1024,  # 20MB
    'max_script_runtime': 3600,  # 1 hour
    'allowed_extensions': ['.py', '.js'],
    'blocked_imports': ['shutil.rmtree', 'subprocess','os.remove', 'os.unlink']
}

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Command Button Layouts ---
COMMAND_BUTTONS_LAYOUT_USER_SPEC = [
    ["⬆️ ᴅᴇᴘʟᴏʏ ʙᴏᴛ", "🗂️ ᴍʏ ʙᴏᴛꜱ"],
    ["🌐 ᴡᴇʙ ʜᴏꜱᴛ", "🌐 ᴍʏ ᴡᴇʙ"],
    ["🧩 ɪɴꜱᴛᴀʟʟ", "🌀 ꜱᴘᴇᴇᴅ"],
    ["📊 ꜱᴛᴀᴛꜱ", "❔ ɢᴜɪᴅᴇ"],
    ["📡 ᴜᴘᴅᴀᴛᴇꜱ"],
    ["💬 ᴅᴇᴠᴇʟᴏᴘᴇʀ"]
]

ADMIN_COMMAND_BUTTONS_LAYOUT_USER_SPEC = [
    ["⬆️ ᴅᴇᴘʟᴏʏ ʙᴏᴛ", "🗂️ ᴍʏ ʙᴏᴛꜱ"],
    ["🌐 ᴡᴇʙ ʜᴏꜱᴛ", "🌐 ᴍʏ ᴡᴇʙ"],
    ["🧩 ɪɴꜱᴛᴀʟʟ", "🌀 ꜱᴘᴇᴇᴅ"],
    ["📊 ꜱᴛᴀᴛꜱ", "❔ ɢᴜɪᴅᴇ"],
    ["💳 ꜱᴜʙꜱ", "📮 ʙʀᴏᴀᴅᴄᴀꜱᴛ"],
    ["⛔ ʟᴏᴄᴋ", "♻️ ʀᴜɴ ᴀʟʟ"],
    ["🛡️ ᴀᴅᴍɪɴ", "👥 ᴜꜱᴇʀꜱ"],
    ["🔧 ꜱᴇᴛᴛɪɴɢ", "📡 ᴄʜᴀɴɴᴇʟ"],
    ["⏹ ꜱᴛᴏᴘ ᴀʟʟ", "🧹 ᴄʟᴇᴀɴᴜᴘ"],
    ["📡 ᴜᴘᴅᴀᴛᴇꜱ"],
    ["💬 ᴅᴇᴠᴇʟᴏᴘᴇʀ"]
]

# --- Database Setup ---
def init_db():
    """Initialize the database with required tables"""
    logger.info(f"Initializing database at: {DATABASE_PATH}")
    try:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS subscriptions
                     (user_id INTEGER PRIMARY KEY, expiry TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS user_files
                     (user_id INTEGER, file_name TEXT, file_type TEXT,
                      PRIMARY KEY (user_id, file_name))''')
        c.execute('''CREATE TABLE IF NOT EXISTS active_users
                     (user_id INTEGER PRIMARY KEY, join_date TEXT, last_seen TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS admins
                     (user_id INTEGER PRIMARY KEY, added_by INTEGER, added_date TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS banned_users
                     (user_id INTEGER PRIMARY KEY, reason TEXT, banned_by INTEGER, ban_date TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS user_limits
                     (user_id INTEGER PRIMARY KEY, file_limit INTEGER, set_by INTEGER, set_date TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS mandatory_channels
                     (channel_id TEXT PRIMARY KEY, 
                      channel_username TEXT,
                      channel_name TEXT,
                      added_by INTEGER,
                      added_date TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS install_logs
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      user_id INTEGER,
                      module_name TEXT,
                      package_name TEXT,
                      status TEXT,
                      log TEXT,
                      install_date TEXT)''')
        
        c.execute('INSERT OR IGNORE INTO admins (user_id, added_by, added_date) VALUES (?, ?, ?)', 
                  (OWNER_ID, OWNER_ID, datetime.now().isoformat()))
        if ADMIN_ID != OWNER_ID:
            c.execute('INSERT OR IGNORE INTO admins (user_id, added_by, added_date) VALUES (?, ?, ?)', 
                      (ADMIN_ID, OWNER_ID, datetime.now().isoformat()))
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error(f"❌ Database initialization error: {e}", exc_info=True)

def load_data():
    """Load data from database into memory"""
    logger.info("Loading data from database...")
    try:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()

        # Load subscriptions
        c.execute('SELECT user_id, expiry FROM subscriptions')
        for user_id, expiry in c.fetchall():
            try:
                user_subscriptions[user_id] = {'expiry': datetime.fromisoformat(expiry)}
            except ValueError:
                logger.warning(f"⚠️ Invalid expiry date format for user {user_id}: {expiry}. Skipping.")

        # Load user files
        c.execute('SELECT user_id, file_name, file_type FROM user_files')
        for user_id, file_name, file_type in c.fetchall():
            if user_id not in user_files:
                user_files[user_id] = []
            user_files[user_id].append((file_name, file_type))

        # Load active users
        c.execute('SELECT user_id FROM active_users')
        active_users.update(user_id for (user_id,) in c.fetchall())

        # Load admins
        c.execute('SELECT user_id FROM admins')
        admin_ids.update(user_id for (user_id,) in c.fetchall())

        # Load banned users
        c.execute('SELECT user_id FROM banned_users')
        banned_users.update(user_id for (user_id,) in c.fetchall())

        # Load user limits
        c.execute('SELECT user_id, file_limit FROM user_limits')
        for user_id, file_limit in c.fetchall():
            user_limits[user_id] = file_limit

        # Load mandatory channels
        c.execute('SELECT channel_id, channel_username, channel_name FROM mandatory_channels')
        for channel_id, channel_username, channel_name in c.fetchall():
            mandatory_channels[channel_id] = {
                'username': channel_username,
                'name': channel_name
            }

        conn.close()
        logger.info(f"Data loaded: {len(active_users)} users, {len(user_subscriptions)} subscriptions, {len(admin_ids)} admins, {len(banned_users)} banned users, {len(user_limits)} custom limits, {len(mandatory_channels)} mandatory channels.")
    except Exception as e:
        logger.error(f"❌ Error loading data: {e}", exc_info=True)

# Initialize DB and Load Data at startup
init_db()
load_data()

# --- Security Functions ---
# --- AI Security Analyzer (Local High-Level Engine) ---
class AISecurityAnalyzer:
    THREATS = [
        ("backdoor", 35, "🐛 ᴄᴀɴ ɢɪᴠᴇ ʀᴇᴍᴏᴛᴇ ᴀᴄᴄᴇꜱꜱ ᴛᴏ ʏᴏᴜʀ ꜱᴇʀᴠᴇʀ (ʙᴀᴄᴋᴅᴏᴏʀ)",
            [r'SOCK_STREAM', r'\.bind\s*\(', r'\.listen\s*\(', r'pty\.spawn', r'/bin/(ba)?sh\s*-i',
             r'cmd\.exe', r'net\.Socket', r'reverse[-_ ]?shell', r'connect\(\(.*\d{4}\)']),
        ("token_theft", 30, "🔑 ᴄᴀɴ ꜱᴛᴇᴀʟ ᴘᴀꜱꜱᴡᴏʀᴅꜱ, ᴛᴏᴋᴇɴꜱ ᴏʀ ᴄᴏᴏᴋɪᴇꜱ",
            [r'\.env\b', r'bot[_ ]?token', r'bearer\s+[a-z0-9]', r'/etc/(passwd|shadow)',
             r'keyring', r'cookies?(\.sqlite|\.txt|jar)?', r'credential', r'login_?data',
             r'local\s?state', r'keychain|keytar', r'getpass', r'password\s*=\s*[\'"]?[a-z0-9]{6}']),
        ("spy", 26, "🕵 ᴄᴀɴ ꜱᴘʏ ᴏɴ ʏᴏᴜ (ꜱᴄʀᴇᴇɴ, ᴋᴇʏꜱ, ᴄᴀᴍ ᴏʀ ᴍɪᴄ)",
            [r'pynput', r'keyboard\.(listener|hook|on_press)', r'mss|pyscreenshot', r'pyautogui\.screenshot',
             r'cv2\.videocapture', r'sounddevice|pyaudio', r'webcam', r'keylogger']),
        ("data_out", 24, "📡 ᴄᴀɴ ꜱᴇɴᴅ ʏᴏᴜʀ ᴘʀɪᴠᴀᴛᴇ ᴅᴀᴛᴀ ᴛᴏ ᴀɴᴏᴛʜᴇʀ ꜱᴇʀᴠᴇʀ",
            [r'requests\.(post|put)\s*\(', r'urlopen\s*\(', r'api/webhooks', r'discord(app)?\.com/api/webhooks',
             r'axios\.(post|put)', r'xmlhttprequest', r'aiohttp.{0,40}\.(post|put)', r'net\.request']),
        ("abuse", 22, "🔇 ᴄᴀɴ ꜱʟᴏᴡ ᴅᴏᴡɴ/ʜᴀʀᴍ ʏᴏᴜʀ ᴅᴇᴠɪᴄᴇ (ᴍɪɴɪɴɢ ᴏʀ ꜰʟᴏᴏᴅ)",
            [r'stratum', r'xmrig|minerd|coinhive|xmr-stak', r'\bddos\b', r'\bflood', r'hashlib\.pbkdf2']),
        ("file_damage", 28, "🗑 ᴄᴀɴ ᴅᴇʟᴇᴛᴇ ᴏʀ ʀᴜɪɴ ʏᴏᴜʀ ꜰɪʟᴇꜱ",
            [r'shutil\.rmtree', r'os\.(remove|unlink)\s*\(', r'rm\s+-rf', r'fs\.(rmsync|rmdirsync|unlinksync)',
             r'del\s+/[fq]', r'rd\s+/s', r'format\s+c:']),
        ("persist", 18, "🔁 ᴄᴀɴ ʀᴇ-ꜱᴛᴀʀᴛ ɪᴛꜱᴇʟꜰ ᴀᴜᴛᴏᴍᴀᴛɪᴄᴀʟʟʏ (ᴘᴇʀꜱɪꜱᴛᴇɴᴄᴇ)",
            [r'crontab', r'systemd|\.service\b', r'autostart', r'startup[ _]?folder', r'launchd',
             r'currentversion\\\\run', r'schtasks']),
        ("obfusc", 16, "👾 ᴄᴏᴅᴇ ɪꜱ ʜɪᴅᴅᴇɴ/ᴇɴᴄʀʏᴘᴛᴇᴅ — ᴀ ᴛʀɪᴄᴋ ᴜꜱᴇᴅ ɪɴ ʜᴀʀᴍꜰᴜʟ ꜱᴄʀɪᴘᴛꜱ",
            [r'b64decode|base64\.b64decode', r'atob\s*\(', r"buffer\.from\([^)]{0,40},\s*['\"]base64",
             r'zlib\.decompress', r'marshal\.loads', r'fromcharcode', r'(\\x[0-9a-f]{2}){12,}',
             r'rot13', r'exec\s*\(\s*compile']),
        ("forkbomb", 40, "💣 ᴄᴀɴ ꜰʀᴇᴇᴢᴇ/ᴄʀᴀꜱʜ ʏᴏᴜʀ ꜱᴇʀᴠᴇʀ (ꜰᴏʀᴋ ʙᴏᴍʙ)",
            [r'os\.fork\s*\(\s*\)', r'while\s+true.{0,60}os\.system', r'spawn.{0,30}while\s*\(?\s*(true|1)',
             r'child_process.{0,80}spawn.{0,80}while', r':(){ :|:& };:']),
        ("deser_exec", 34, "🧩 ᴄᴀɴ ʀᴜɴ ʜɪᴅᴅᴇɴ ᴄᴏᴅᴇ ᴠɪᴀ ᴅᴀᴛᴀ ꜰɪʟᴇꜱ (ᴘɪᴄᴋʟᴇ/ʏᴀᴍʟ ᴛʀɪᴄᴋ)",
            [r'pickle\.loads?\s*\(', r'cPickle', r'yaml\.load\s*\((?![^)]*Loader)', r'dill\.loads',
             r'eval\s*\(\s*input', r'new Function\s*\(']),
        ("root_escal", 38, "👑 ᴛʀɪᴇꜱ ᴛᴏ ɢᴇᴛ ᴀᴅᴍɪɴ/ʀᴏᴏᴛ ᴘᴏᴡᴇʀꜱ",
            [r'ctypes[^\n]{0,60}setuid', r'\bsudo\b', r'setuid\s*\(\s*0', r'uid=0', r'geteuid',
             r'/etc/sudoers', r'runas\b', r'start-process\s+-verb\s+runas']),
        ("browser_steal", 36, "🌐 ᴄᴀɴ ꜱᴛᴇᴀʟ ʙʀᴏᴡꜱᴇʀ ᴘᴀꜱꜱᴡᴏʀᴅꜱ/ᴄᴏᴏᴋɪᴇꜱ",
            [r'appdata[^\n]{0,50}google\\chrome', r'login[ _]?data', r'web data', r'cookies\.sqlite',
             r'local\sstate', r'%appdata%', r'ls/copy[^\n]{0,40}cookies', r'edge[/\\]user data']),
        ("discord_theft", 34, "🎮 ᴄᴀɴ ꜱᴛᴇᴀʟ ᴅɪꜱᴄᴏʀᴅ/ɢᴀᴍɪɴɢ ᴛᴏᴋᴇɴꜱ",
            [r'[MNOmno][A-Za-z0-9_-]{23}\.[A-Za-z0-9_-]{6}\.[A-Za-z0-9_-]{27}', r'discord[^\n]{0,30}(token|ldb)',
             r'leveldb[^\n]{0,20}\.ldb', r'token[_ ]?grab']),
        ("exfil_endpoints", 26, "📤 ꜱᴇɴᴅꜱ ᴅᴀᴛᴀ ᴛᴏ ᴘᴀꜱᴛᴇʙɪɴ-ʟɪᴋᴇ ᴇxꜰɪʟ ᴘᴏɪɴᴛꜱ",
            [r'pastebin\.com/raw', r'hastebin', r'requestbin', r'webhook\.site', r'ngrok\.io|ngrok-free\.app',
             r'pipedream\.net', r'interact\.sh', r'discord(app)?\.com/api/webhooks']),
        ("env_scrape", 24, "🗝 ꜱᴄᴀɴꜱ ᴇɴᴠɪʀᴏɴᴍᴇɴᴛ ꜰᴏʀ ꜱᴇᴄʀᴇᴛꜱ",
            [r'environ(ment)?\[[\'"][^\'"]*(key|secret|token|pass)', r'process\.env\.[A-Z_]*(TOKEN|KEY|SECRET)',
             r'os\.environ.{0,30}(items|values)\s*\(']),
        ("scrape_files", 38, "🗂 ᴄᴀɴ ꜱᴛᴇᴀʟ ᴏᴛʜᴇʀ ᴜꜱᴇʀꜱ' ꜰɪʟᴇꜱ & ᴛᴏᴋᴇɴꜱ ꜰʀᴏᴍ ᴛʜɪꜱ ʜᴏꜱᴛ",
            [r"os\.(listdir|walk|scandir)\s*\(\s*['\"](\.\.|/)", r"open\s*\(\s*['\"](\.\./|/etc/|/data/)",
             r"/sdcard|/storage/(emulated|self)", r"\bhbi\.py\b", r"shutil\.make_archive",
             r"shutil\.copytree", r"glob\.glob\s*\(\s*['\"][^'\"]*\.\.", r"sqlite3\.connect\s*\(\s*['\"]\.\."]),
        ("tunnel_expose", 44, "🌍 ᴏᴘᴇɴꜱ ᴘᴜʙʟɪᴄ ᴛᴜɴɴᴇʟ — ᴡʜᴏʟᴇ ɪɴᴛᴇʀɴᴇᴛ ʀᴇᴀᴄʜᴇꜱ ᴅᴇᴠɪᴄᴇ",
            [r"pyngrok|ngrok\.connect|ngrok\.com", r"localtunnel", r"serveo", r"localhost\.run",
             r"cloudflared|trycloudflare", r"telebit|bore\.pub|zrok\.io"])
    ]
    CMD_EXEC = ("cmd_exec", 22, "🖥 ᴄᴀɴ ʀᴜɴ ʜɪᴅᴅᴇɴ ꜱʏꜱᴛᴇᴍ ᴄᴏᴍᴍᴀɴᴅꜱ ᴏɴ ʏᴏᴜʀ ꜱᴇʀᴠᴇʀ")
    CMD_PATTERNS = [r'os\.system\s*\(', r'os\.popen\s*\(', r'subprocess\.(call|run|popen|check_output)',
                    r'child_process', r'os\.(execl|execv|spawnl|spawnv)', r'\bexec\s*\(', r'\beval\s*\(',
                    r'shell\s*=\s*true', r'commands?\.execute']
    SAFE_IMPORTS = {'flask','telebot','requests','math','random','datetime','time','json','os','sys','re',
                    'logging','sqlite3','threading','psutil','aiohttp','asyncio','collections','itertools',
                    'functools','typing','pathlib','io','os.path','uuid','hashlib','base64','urllib','socket',
                    'express','fs','http','https','path','dotenv'}
    VERDICTS = [(90,"⛔","ᴅᴀɴɢᴇʀᴏᴜꜱ — ʀᴜɴɴɪɴɢ ɴᴏᴛ ʀᴇᴄᴏᴍᴍᴇɴᴅᴇᴅ"),
                (70,"🔴","ʜɪɢʜ ʀɪꜱᴋ — ᴄʜᴇᴄᴋ ꜰɪɴᴅɪɴɢꜱ ᴄᴀʀᴇꜰᴜʟʟʏ"),
                (45,"🟠","ᴍᴇᴅɪᴜᴍ ʀɪꜱᴋ — ʀᴇᴠɪᴇᴡ ʙᴇꜰᴏʀᴇ ʀᴜɴ"),
                (20,"🟡","ꜱʟɪɢʜᴛ ʀɪꜱᴋ — ᴘʀᴏʙᴀʙʟʏ ᴏᴋᴀʏ"),
                (0,"🟢","ꜱᴀꜰᴇ — ʟᴏᴏᴋꜱ ᴄʟᴇᴀɴ")]

    def analyze_text(self, text):
        low = text.lower()
        findings, score, hits = [], 0, []
        cats = list(self.THREATS)
        cats.insert(0, self.CMD_EXEC + (self.CMD_PATTERNS,))
        obf_hits = 0
        for entry in cats:
            if len(entry) == 4:
                name, w, desc, pats = entry
                if name == "obfusc":
                    obf_hits = sum(1 for pat in pats if re.search(pat, low))
                    if obf_hits:
                        add = min(w + (obf_hits - 1) * 8, 32)
                        score += add; findings.append(desc)
                    continue
            else:
                name, w, desc, pats = entry
            for pat in pats:
                if re.search(pat, low):
                    score += w; findings.append(desc)
                    if name not in hits: hits.append(name)
                    break
        imports_clean = True
        for im in re.findall(r'(?:^|[\n])\s*(?:from\s+([\w.]+)|import\s+([\w., ]+))', low):
            mods = (im[0] or '').split(',') + (im[1] or '').replace('from','').split(',')
            for m in mods:
                m = m.strip().split('.')[0].strip()
                if m and m not in self.SAFE_IMPORTS and m not in ('as',): imports_clean = False
        if imports_clean and 0 < score <= 30: score -= 8
        score = max(3, min(score, 100))
        verdict = next(v for start, e, v in self.VERDICTS if score >= start)
        emoji = verdict and next((e for st, e, vv in self.VERDICTS if score >= st), "\U0001F7E2")
        return score, findings[:6], emoji, verdict, len(text.splitlines()), hits

    def build_report(self, file_path, ext, user_id, user_name, file_label=None):
        label = file_label or os.path.basename(file_path)
        texts, n_files = [], 1
        try:
            if ext == 'zip':
                import zipfile as _zf
                with _zf.ZipFile(file_path) as z:
                    members = [m for m in z.namelist()
                               if m.lower().endswith(('.py','.js','.json','.txt','.sh','.bat','.cmd','.ps1'))][:15]
                    n_files = len(members)
                    for m in members:
                        try: texts.append(z.read(m).decode('utf-8','ignore')[:4000])
                        except Exception: pass
                if not texts: texts.append('')
            else:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    texts = [f.read()[:60000]]
        except Exception as e:
            logger.error(f"AI analyzer read error: {e}")
            texts = ['']
        best_score, merged, emoji, verdict, lines, all_hits = 0, [], "🟢", "", 0, []
        for t in texts:
            sc_, fnd, em, vd, ln, hts = self.analyze_text(t)
            if sc_ > best_score:
                best_score, emoji, verdict = sc_, em, vd
            for x in fnd:
                if x not in merged: merged.append(x)
            for h in hts:
                if h not in all_hits: all_hits.append(h)
            lines += ln
        grok = None
        try:
            grok = _grok_scanner.scan(texts)
        except Exception as e:
            logger.error(f"Grok scan error: {e}")
        if grok:
            if grok['score'] > best_score:
                best_score = grok['score']
                emoji = next((e for st, e, vv in self.VERDICTS if best_score >= st), "🟢")
                verdict = next((vv for st, e, vv in self.VERDICTS if best_score >= st), "")
            for x in grok['findings']:
                tag = f"🤖 {x}"
                if tag not in merged and len(merged) < 10: merged.append(tag)
        kb = round(os.path.getsize(file_path)/1024, 1) if os.path.exists(file_path) else 0

        # ---- decision-friendly verdict ----
        HARM = {
            'cmd_exec':    "can run hidden system commands on host",
            'backdoor':    "attacker gets remote access to device",
            'token_theft': "saved passwords/tokens can be stolen",
            'spy':         "screen, keys or camera can be spied",
            'data_out':    "private data sent to attacker's server",
            'abuse':       "server lag & battery drain (mining/flood)",
            'file_damage': "your files and folders can be deleted",
            'persist':     "malware auto-restarts after every reboot",
            'obfusc':      "hidden code evades normal detection",
            'forkbomb':    "whole server can freeze/crash",
            'deser_exec':  "hidden code runs via data files",
            'root_escal':  "attacker gains root/admin powers",
            'browser_steal':"browser passwords & cookies stolen",
            'discord_theft':"discord/game tokens can be stolen",
            'exfil_endpoints':"stolen data uploaded to dump sites",
            'env_scrape':  "environment secrets harvested",
            'scrape_files':"other users' bot files & tokens stolen from this host",
            'tunnel_expose':"device becomes reachable by whole internet",
        }
        if best_score >= 90:   v_emoji, v_status, v_rec = "⛔", "MALWARE", "NO - never approve"
        elif best_score >= 70: v_emoji, v_status, v_rec = "🔴", "DANGEROUS", "NO"
        elif best_score >= 45: v_emoji, v_status, v_rec = "🟠", "RISKY", "check first"
        elif best_score >= 20: v_emoji, v_status, v_rec = "🟡", "MOSTLY SAFE", "yes - with care"
        else:                  v_emoji, v_status, v_rec = "🟢", "SAFE", "yes"

        harms = [HARM[h] for h in all_hits if h in HARM]
        if not harms:
            harms = ["none expected - clean script"]

        rep = ("🛡️ ᴅᴇᴇᴘ ꜱᴇᴄᴜʀɪᴛʏ ʀᴇᴘᴏʀᴛ\n\n"
               "╭━━━「 ⚖️ ꜰɪɴᴀʟ ꜱᴛᴀᴛᴜꜱ 」━━━╮\n"
               f"┃ {v_emoji} ꜱᴛᴀᴛᴜꜱ : {_t(v_status.lower())}\n"
               f"┃ 👍 ʀᴇᴄᴏᴍᴍᴇɴᴅᴇᴅ : {_t(v_rec)}\n"
               f"┃ 🎯 ʀɪꜱᴋ : {best_score}/100\n"
               "╰━━━━━━━━━━━━━━━━━━╯\n\n"
               f"📄 ꜰɪʟᴇ : {label}\n"
               f"👤 ᴜꜱᴇʀ : {_t(user_name)} · {user_id}\n"
               f"📏 {lines} ʟɪɴᴇꜱ · {kb} ᴋʙ"
               + (f" · 📦 {n_files} ꜰɪʟᴇꜱ\n" if ext == 'zip' else "\n")
               + ("🧠 ꜱᴄᴀɴ : ꜱᴇʀᴠᴇʀ 100+ ✅ · ɢʀᴏᴋ ᴀɪ ✅\n" if grok else "🧠 ꜱᴄᴀɴ : ꜱᴇʀᴠᴇʀ 100+ ᴄʜᴇᴄᴋꜱ\n")
               + "\n⚠️ ɪꜰ ᴀᴘᴘʀᴏᴠᴇᴅ, ʜᴀʀᴍ ꜱᴄᴇɴᴀʀɪᴏ:\n")
        rep += ("• " + "\n• ".join(_t(h) for h in harms[:6]))
        rep += "\n\n🔍 ꜰɪɴᴅɪɴɢꜱ:\n"
        rep += ("• " + "\n• ".join(merged)) if merged else "• nothing suspicious detected"
        if grok and grok.get('summary'):
            rep += f"\n\n🔬 ᴀɪ ꜱᴜᴍᴍᴀʀʏ: {_t(grok['summary'])}"
        rep += f"\n\n💡 ᴠᴇʀʙᴀʟ ᴠᴇʀᴅɪᴄᴛ: {verdict}"
        return rep

class GrokSecurityScanner:
    """xAI Grok deep-scan with 3-key failover. Returns dict or None."""
    SYSTEM_PROMPT = (
        "You are a hostile code security auditor for a public bot/web hosting platform. "
        "Analyze the given code for: backdoors/reverse shells, token-password-cookie theft, "
        "keyloggers/spyware, crypto miners, data exfiltration, destructive file operations, "
        "persistence tricks, and obfuscation hiding malicious intent. "
        "Be deeply suspicious of code that looks innocent but does something hidden. "
        "Scoring: 0-19 safe, 20-44 slight risk, 45-69 medium, 70-89 high, 90-100 dangerous. "
        'Respond ONLY with minified JSON, no markdown: {"score": int, "findings": ["short human-readable risk", ...], "summary": "one short line"}'
    )

    def scan(self, texts):
        keys = [k.strip() for k in GROK_KEYS if k and k.strip()]
        if not keys: return None
        blob = "\n\n===== FILE =====\n".join(t[:9000] for t in texts if t)[:45000]
        if not blob.strip(): return None
        body = {"model": GROK_MODEL,
                "messages": [{"role":"system","content":self.SYSTEM_PROMPT},
                             {"role":"user","content":"AUDIT THIS CODE:\n\n"+blob}],
                "temperature": 0.1, "max_tokens": 600}
        for i, key in enumerate(keys):
            try:
                r = requests.post(GROK_API, json=body,
                                  headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                                  timeout=22)
                if r.status_code != 200:
                    logger.warning(f"Grok key #{i+1} http {r.status_code}"); continue
                content = r.json()['choices'][0]['message']['content'].strip()
                m = re.search(r'\{.*\}', content, re.S)
                if not m: logger.warning(f"Grok key #{i+1}: no json"); continue
                d = json.loads(m.group(0))
                score = max(0, min(int(d.get('score', 0)), 100))
                findings = [str(x)[:120] for x in d.get('findings', [])][:6]
                return {"score": score, "findings": findings, "summary": str(d.get('summary',''))[:150]}
            except Exception as e:
                logger.warning(f"Grok key #{i+1} failed: {e}"); continue
        return None

_grok_scanner = GrokSecurityScanner()

_ai_engine = AISecurityAnalyzer()

ALERT_SUFFIX = "\n\n\U0001F6A8 " + _t("approval required") + " \u2014 " + _t("file will not start until you allow")
def build_ai_report(file_path, ext, user_id, user_name, file_label=None):
    try:
        return _ai_engine.build_report(file_path, ext, user_id, user_name, file_label)
    except Exception as e:
        logger.error(f"AI report error: {e}")
        return f"🤖 ᴀɪ ʀᴇᴘᴏʀᴛ ᴜɴᴀᴠᴀɪʟᴀʙʟᴇ ({e})"

def check_code_security(file_path, file_type):
    """Check code for dangerous commands (lightweight version)"""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Comprehensive dangerous patterns with regex
        dangerous_patterns = [
    # ======================
    # SYSTEM / OS COMMANDS
    # ======================
    r'\bos\b',
    r'\bos\.system\b',
    r'\bos\.(remove|unlink|walk|listdir|scandir|stat|popen|fork|exec|kill|spawn)\b',
    r'\bshutdown\b',
    r'\breboot\b',
    r'rm\s+-rf',
    r'format\s+c:',
    r'dd\s+if=',
    r'\bmkfs\b',
    r'\bfdisk\b',
    r'chmod\s+777',
    r'chmod\s+\+x',
    r'\bsys\.exit\b',
    r'\bsys\.argv\b',

    # ======================
    # BASIC SHELL COMMANDS
    # ======================
    r'\bls\b',
    r'\bcd\b',
    r'\bvps\b',
    r'\bkill\b',
    r'\bkillall\b',
    r'\bpkill\b',
    r'\bkill\s+-\d+',
    r'\bhalt\b',
    r'\bpoweroff\b',
    r'\binit\s+0',
    r'\binit\s+6',
    r'\btelinit\s+0',
    r'\btelinit\s+6',
    r'\bmv\b.*/dev/null',
    r'\bcat\s+>/dev/null',
    r'>\s*/dev/null',
    r'2>\s*&1',
    r'\b&\s*$',
    r'\bnohup\b',
    r'\bdisown\b',

    # ======================
    # FILE DELETION/DESTRUCTION
    # ======================
    r'rm\s+-rf\s+/',
    r'rm\s+-rf\s+~',
    r'rm\s+-rf\s+\.',
    r'rm\s+-rf\s+\*',
    r'rm\s+-rf\s+.*',
    r'\bdd\s+if=/dev/zero',
    r'\bdd\s+of=/dev/sda',
    r'\bmv\s+/dev/null',
    r'>\s+\.bash_history',
    r'>\s+\.zsh_history',
    r'echo\s+""\s+>',
    r'truncate\s+-s\s+0',
    r':>\s*',

    # ======================
    # REGULAR EXPRESSIONS (re) - Yeh add kiya
    # ======================
    r'\bre\b',
    r'\bre\.(compile|search|match|findall|finditer|sub|split|escape|fullmatch)\b',
    r'\bimport\s+re\b',
    r'\bfrom\s+re\s+import\b',
    r'\bregex\b',
    r'\bpattern\s*=\s*re\.compile',
    r're\.(I|IGNORECASE|M|MULTILINE|S|DOTALL|U|UNICODE|X|VERBOSE)',
    r'\.*\{.*,\}',
    r'\^.*\$',
    r'\[.*\]',
    r'\(.*\)',
    r'\?.*',
    r'\*.*',
    r'\+.*',

    # ======================
    # IMAGE/FILE MANIPULATION - Yeh add kiya
    # ======================
    r'image\.jpeg',
    r'image\.jpg',
    r'image\.png',
    r'image\.gif',
    r'image\.bmp',
    r'\.jpeg\b',
    r'\.jpg\b',
    r'\.png\b',
    r'\.gif\b',
    r'\.bmp\b',
    r'\.ico\b',
    r'\.svg\b',
    r'\.webp\b',
    r'\.tiff\b',
    r'\.tif\b',
    r'\.pdf\b',
    r'\.docx\b',
    r'\.doc\b',
    r'\.xlsx\b',
    r'\.xls\b',
    r'\.pptx\b',
    r'\.ppt\b',
    r'\.zip\b',
    r'\.tar\b',
    r'\.gz\b',
    r'\.7z\b',
    r'\.rar\b',
    r'\bPIL\b',
    r'\bImage\b',
    r'\bImage\.(open|save|new|fromarray|frombytes)\b',
    r'\bcv2\b',
    r'\bopencv\b',
    r'\bskimage\b',
    r'\bscikit-image\b',
    r'\bmatplotlib\.image\b',
    r'\bimread\b',
    r'\bimwrite\b',
    r'\bimshow\b',
    r'\bimsave\b',

    # ======================
    # CTYPES / DLL LOADING
    # ======================
    r'\bctypes\b',
    r'\bctypes\.(CDLL|WinDLL|PyDLL|cdll|windll|oledll|py_object|Structure|Union)\b',
    r'\bCDLL\b',
    r'\bWinDLL\b',
    r'\blibc\b',
    r'\bFILE_p\b',
    r'\blibc\.(system|exec|fork|kill|popen)\b',
    r'\bmemset\b',
    r'\bmemcpy\b',
    r'\bmprotect\b',
    r'\bmmap\b',
    r'\bVirtualAlloc\b',
    r'\bCreateProcess\b',
    r'\bLoadLibrary\b',
    r'\bGetProcAddress\b',

    # ======================
    # EXEC / SUBPROCESS
    # ======================
    r'\bsubprocess\b',
    r'\bsubprocess\.(Popen|call|run|check_output|getoutput|getstatusoutput)\b',
    r'\beval\b',
    r'\bexec\b',
    r'\bcompile\b',
    r'\b__import__\b',

    # ======================
    # FILE SYSTEM / DATA READ
    # ======================
    r'\bopen\s*\(',
    r'\bread\s*\(',
    r'\bpathlib\b',
    r'\bglob\b',
    r'\bshutil\b',
    r'\bshutil\.(rmtree|copytree|move|disk_usage)\b',
    r'\bzipfile\b',
    r'\btempfile\b',
    r'\bcPickle\b',
    r'\bshelve\b',
    r'\bsqlite3\b',
    r'\bpandas\.(read_csv|read_excel|read_json)\b',

    # ======================
    # ENV / SECRETS
    # ======================
    r'\bos\.environ\b',
    r'\bdotenv\b',
    r'\bload_dotenv\b',
    r'\bprintenv\b',
    r'\benv\b',
    r'\bgetpass\b',
    r'\bkeyring\b',
    r'\bconfigparser\b',
    r'\byaml\b',
    r'\bjson\.load\b',

    # ======================
    # NETWORK / DATA EXFIL
    # ======================
    r'\bsocket\b',
    r'\bsocket\.(socket|create_connection|gethostname|gethostbyname)\b',
    r'\brequests\b',
    r'\brequests\.(get|post|put|delete|head|request)\b',
    r'\burllib\b',
    r'\burllib2\b',
    r'\burllib3\b',
    r'\bhttp\.client\b',
    r'\bwebsocket\b',
    r'\basyncio\.open_connection\b',
    r'\bwget\b',
    r'\bcurl\b',
    r'\bdownload\b',
    r'\bftplib\b',
    r'\bsmtplib\b',
    r'\bpoplib\b',
    r'\bimaplib\b',
    r'\btelnetlib\b',

    # ======================
    # SSH / REMOTE ACCESS
    # ======================
    r'\bparamiko\b',
    r'\bscp\b',
    r'\bssh\b',
    r'\bsshlib\b',
    r'\bpexpect\b',
    r'\bfabric\b',

    # ======================
    # SYSTEM INFO LEAK
    # ======================
    r'\bpsutil\b',
    r'\bplatform\b',
    r'\bplatform\.(node|processor|machine|architecture|system|version)\b',
    r'\bcmdline\b',
    r'\bpid\b',
    r'/proc/',
    r'\bmem\b',
    r'\bcpu\b',
    r'\bhostname\b',
    r'\buname\b',
    r'\bwhoami\b',

    # ======================
    # PYTHON INTERNAL ABUSE
    # ======================
    r'\bglobals\b',
    r'\blocals\b',
    r'\bvars\b',
    r'\binspect\b',
    r'\bmarshal\b',
    r'\bpickle\b',
    r'\bimportlib\b',
    r'\b__builtins__\b',
    r'\b__import__\b',
    r'\b__loader__\b',
    r'\b__file__\b',
    r'\b__package__\b',
    r'\b__spec__\b',
    r'\b__code__\b',
    r'\b__dict__\b',
    r'\bgetattr\b',
    r'\bsetattr\b',
    r'\bdelattr\b',
    r'\bhasattr\b',
    r'\bcallable\b',

    # ======================
    # TELEGRAM / BOT CONTROL
    # ======================
    r'\btelebot\b',
    r'\btelebot\.types\b',
    r'\baiogram\b',
    r'\bpyrogram\b',
    r'\btelegram\.ext\b',
    r'\btelegram\.bot\b',

    # ======================
    # LINUX / SHELL / BACKDOOR
    # ======================
    r'/bin/sh',
    r'/bin/bash',
    r'/bin/zsh',
    r'/bin/dash',
    r'nc\s+-e',
    r'netcat',
    r'\bbase64\b',
    r'\becho\b.*\|',
    r'\bawk\b',
    r'\bsed\b',
    r'\bfind\b',
    r'\bxargs\b',
    r'\bcrontab\b',
    r'\bservice\b',
    r'\bsystemctl\b',
    r'\btop\b',
    r'\bps\b',
    r'\bhtop\b',
    r'\bifconfig\b',
    r'\bip\s+a',
    r'\bss\b',
    r'\blsof\b',
    r'\bnetstat\b',

    # ======================
    # SSH KEYS / USER DATA
    # ======================
    r'/etc/passwd',
    r'/etc/shadow',
    r'/etc/hosts',
    r'/etc/resolv.conf',
    r'\.ssh/',
    r'id_rsa',
    r'id_dsa',
    r'authorized_keys',
    r'known_hosts',
    r'\.bashrc',
    r'\.bash_profile',
    r'\.zshrc',
    r'\.profile',

    # ======================
    # DATABASE ACCESS
    # ======================
    r'\bsqlite3\b',
    r'\bmysql\b',
    r'\bmysql\.connector\b',
    r'\bpsycopg2\b',
    r'\bpymongo\b',
    r'\bredis\b',

    # ======================
    # CRYPTO / ENCRYPTION
    # ======================
    r'\bcrypt\b',
    r'\bhashlib\b',
    r'\bhmac\b',
    r'\bssl\b',
    r'\btls\b',
    r'\bCrypto\b',
    r'\bcryptography\b',

    # ======================
    # PROCESS CONTROL
    # ======================
    r'\bsignal\b',
    r'\bmultiprocessing\b',
    r'\bthreading\b',
    r'\bdaemon\b',
    r'\batexit\b',
    r'\bexit\b',
    r'\bquit\b',

    # ======================
    # GUI / SCREEN CAPTURE
    # ======================
    r'\bpyautogui\b',
    r'\bselenium\b',
    r'\bpyscreenshot\b',
    r'\bImageGrab\b',

    # ======================
    # KEYLOGGING / INPUT
    # ======================
    r'\bpynput\b',
    r'\bkeyboard\b',
    r'\bmouse\b',
    r'\bgetch\b',

    # ======================
    # MISC DANGEROUS
    # ======================
    r'\.name\b',
    r'\.__name__\b',
    r'\.__class__\b',
    r'\.__bases__\b',
    r'\.__subclasses__\b',
    r'\.__mro__\b',
    r'\.__dictitems__\b',
    r'\.__reduce__\b',
    r'\.__reduce_ex__\b',
    r'\.__getstate__\b',
    r'\.__setstate__\b',

    # ======================
    # WINDOWS SPECIFIC
    # ======================
    r'\bwin32api\b',
    r'\bwin32com\b',
    r'\bwin32con\b',
    r'\bwin32event\b',
    r'\bwin32file\b',
    r'\bwin32process\b',
    r'\bwin32security\b',
    r'\bwmi\b',
    r'\bregedit\b',
    r'\bregistry\b',
    r'\bGetAsyncKeyState\b',
    r'\bSetWindowsHookEx\b',
    r'\btaskkill\b',
    r'\btasklist\b',
    r'\bschtasks\b',

    # ======================
    # ANTI-DEBUG / ANTI-VM
    # ======================
    r'\bptrace\b',
    r'\bdebugger\b',
    r'\bisatty\b',
    r'\bwindbg\b',
    r'\bollydbg\b',

    # ======================
    # MEMORY MANIPULATION
    # ======================
    r'\bmmap\b',
    r'\bmprotect\b',
    r'\bbrk\b',
    r'\bsbrk\b',
    r'\bmalloc\b',
    r'\bfree\b',
    r'\brealloc\b',
    r'\bVirtualAlloc\b',
    r'\bVirtualProtect\b',
    r'\bVirtualFree\b',
    r'\bHeapAlloc\b',
    r'\bHeapFree\b',

    # ======================
    # CODE INJECTION
    # ======================
    r'\binject\b',
    r'\bpayload\b',
    r'\bshellcode\b',
    r'\bmetasploit\b',
    r'\bbackdoor\b',
    r'\brootkit\b',
    r'\btrojan\b',
    r'\bmalware\b',
    r'\bexploit\b',
    r'\bvirus\b',
    r'\bworm\b',

    # ======================
    # NETWORK SCANNING
    # ======================
    r'\bnmap\b',
    r'\bnping\b',
    r'\bscapy\b',
    r'\barp\b',
    r'\bping\b',
    r'\btraceroute\b',
    r'\broute\b',
    r'\bifconfig\b',
    r'\bipconfig\b',
    r'\bnetstat\b',
    r'\bss\b',

    # ======================
    # PRIVILEGE ESCALATION
    # ======================
    r'\bsudo\b',
    r'\bsu\b',
    r'\brunas\b',
    r'\bprivilege\b',
    r'\bescalation\b',
    r'\buac\b',
    r'\bbypassuac\b',

    # ======================
    # PERSISTENCE
    # ======================
    r'\bregistry\b',
    r'\bstartup\b',
    r'\bautostart\b',
    r'\bscheduled\s*task\b',
    r'\bcron\b',
    r'\bat\b',
    r'\binit\.d\b',
    r'\bsystemd\b',
    r'\blaunchd\b',
    r'\bplist\b',

    # ======================
    # MORE DESTRUCTIVE COMMANDS
    # ======================
    r'\bmv\s+.*\s+/dev/null',
    r'\b>+\s*.*\.log',
    r'\btar\s+.*--exclude',
    r'\bfuser\b',
    r'\bstrace\b',
    r'\bltrace\b',
    r'\bgdb\b',
    r'\bobjdump\b',
    r'\bstrings\b',
    r'\bhexdump\b',
    r'\bxxd\b',
    r'\bod\b',
    r'\bsize\b',
    r'\bnm\b',
    r'\breadelf\b',
    r'\bldd\b',
    r'\bfile\b',
    r'\bwhich\b',
    r'\bwhereis\b',
    r'\blocate\b',
    r'\bupdatedb\b',
    r'\bmake\b',
    r'\bgcc\b',
    r'\bg\+\+\b',
    r'\bclang\b',
    r'\bclang\+\+\b',
    r'\bpython\d*\s+-c',
    r'\bperl\s+-e',
    r'\bruby\s+-e',
    r'\bphp\s+-r',
    r'\blua\s+-e',
    r'\bnode\s+-e',
    r'\bwget\s+.*\|\s*sh',
    r'\bcurl\s+.*\|\s*sh',
    r'\bwget\s+.*\|\s*bash',
    r'\bcurl\s+.*\|\s*bash',
    r'\bchattr\s+\+i',
    r'\bchattr\s+-i',
    r'\bsetfacl\b',
    r'\bgetfacl\b',
    r'\bchown\s+.*:.*',
    r'\bchgrp\b',
    r'\busermod\b',
    r'\bgroupmod\b',
    r'\badduser\b',
    r'\baddgroup\b',
    r'\bdeluser\b',
    r'\bdelgroup\b',
    r'\bpasswd\b',
    r'\bvisudo\b',
    r'\bed\b',
    r'\bex\b',
    r'\bvi\b',
    r'\bvim\b',
    r'\bnano\b',
    r'\bemacs\b',
    r'\bpico\b',
    r'\bmicro\b',
    r'\bne\b',

    # ======================
    # ADDITIONAL SECURITY PATTERNS
    # ======================
    r'\b__import__\s*\(',
    r'\bgetattr\s*\(',
    r'\bsetattr\s*\(',
    r'\bdelattr\s*\(',
    r'\bhasattr\s*\(',
    r'\b__getattr__\b',
    r'\b__setattr__\b',
    r'\b__delattr__\b',
    r'\b__getattribute__\b',
    r'\b__call__\b',
    r'\b__enter__\b',
    r'\b__exit__\b',
    r'\b__new__\b',
    r'\b__init__\b',
    r'\b__del__\b',
    r'\b__repr__\b',
    r'\b__str__\b',
    r'\b__bytes__\b',
    r'\b__format__\b',
    r'\b__lt__\b',
    r'\b__le__\b',
    r'\b__eq__\b',
    r'\b__ne__\b',
    r'\b__gt__\b',
    r'\b__ge__\b',
    r'\b__hash__\b',
    r'\b__bool__\b',
    r'\b__getitem__\b',
    r'\b__setitem__\b',
    r'\b__delitem__\b',
    r'\b__iter__\b',
    r'\b__next__\b',
    r'\b__reversed__\b',
    r'\b__contains__\b',
    r'\b__len__\b',
    r'\b__length_hint__\b',
    r'\b__missing__\b',
    r'\b__copy__\b',
    r'\b__deepcopy__\b'
]
        
        found_patterns = []
        for pattern in dangerous_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                found_patterns.append(pattern)
        
        if found_patterns:
            logger.warning(f"🚨 Dangerous patterns detected in {file_path}: {found_patterns}")
            return False, f"Code contains dangerous commands: {', '.join(found_patterns[:5])}"  # Show first 5 only
        
        return True, "Code is safe"
    except Exception as e:
        logger.error(f"Error in security check: {e}")
        return False, f"Security check error: {str(e)}"

def scan_zip_security(zip_path):
    """Check ZIP contents for security (lightweight version)"""
    try:
        dangerous_patterns = [
    # ======================
    # SYSTEM / OS COMMANDS
    # ======================
    r'\bos\b',
    r'\bos\.system\b',
    r'\bos\.(remove|unlink|walk|listdir|scandir|stat|popen|fork|exec|kill|spawn)\b',
    r'\bshutdown\b',
    r'\breboot\b',
    r'rm\s+-rf',
    r'format\s+c:',
    r'dd\s+if=',
    r'\bmkfs\b',
    r'\bfdisk\b',
    r'chmod\s+777',
    r'chmod\s+\+x',
    r'\bsys\.exit\b',
    r'\bsys\.argv\b',

    # ======================
    # BASIC SHELL COMMANDS
    # ======================
    r'\bls\b',
    r'\bcd\b',
    r'\bvps\b',
    r'\bkill\b',
    r'\bkillall\b',
    r'\bpkill\b',
    r'\bkill\s+-\d+',
    r'\bhalt\b',
    r'\bpoweroff\b',
    r'\binit\s+0',
    r'\binit\s+6',
    r'\btelinit\s+0',
    r'\btelinit\s+6',
    r'\bmv\b.*/dev/null',
    r'\bcat\s+>/dev/null',
    r'>\s*/dev/null',
    r'2>\s*&1',
    r'\b&\s*$',
    r'\bnohup\b',
    r'\bdisown\b',

    # ======================
    # FILE DELETION/DESTRUCTION
    # ======================
    r'rm\s+-rf\s+/',
    r'rm\s+-rf\s+~',
    r'rm\s+-rf\s+\.',
    r'rm\s+-rf\s+\*',
    r'rm\s+-rf\s+.*',
    r'\bdd\s+if=/dev/zero',
    r'\bdd\s+of=/dev/sda',
    r'\bmv\s+/dev/null',
    r'>\s+\.bash_history',
    r'>\s+\.zsh_history',
    r'echo\s+""\s+>',
    r'truncate\s+-s\s+0',
    r':>\s*',

    # ======================
    # REGULAR EXPRESSIONS (re) - Yeh add kiya
    # ======================
    r'\bre\b',
    r'\bre\.(compile|search|match|findall|finditer|sub|split|escape|fullmatch)\b',
    r'\bimport\s+re\b',
    r'\bfrom\s+re\s+import\b',
    r'\bregex\b',
    r'\bpattern\s*=\s*re\.compile',
    r're\.(I|IGNORECASE|M|MULTILINE|S|DOTALL|U|UNICODE|X|VERBOSE)',
    r'\.*\{.*,\}',
    r'\^.*\$',
    r'\[.*\]',
    r'\(.*\)',
    r'\?.*',
    r'\*.*',
    r'\+.*',

    # ======================
    # IMAGE/FILE MANIPULATION - Yeh add kiya
    # ======================
    r'image\.jpeg',
    r'image\.jpg',
    r'image\.png',
    r'image\.gif',
    r'image\.bmp',
    r'\.jpeg\b',
    r'\.jpg\b',
    r'\.png\b',
    r'\.gif\b',
    r'\.bmp\b',
    r'\.ico\b',
    r'\.svg\b',
    r'\.webp\b',
    r'\.tiff\b',
    r'\.tif\b',
    r'\.pdf\b',
    r'\.docx\b',
    r'\.doc\b',
    r'\.xlsx\b',
    r'\.xls\b',
    r'\.pptx\b',
    r'\.ppt\b',
    r'\.zip\b',
    r'\.tar\b',
    r'\.gz\b',
    r'\.7z\b',
    r'\.rar\b',
    r'\bPIL\b',
    r'\bImage\b',
    r'\bImage\.(open|save|new|fromarray|frombytes)\b',
    r'\bcv2\b',
    r'\bopencv\b',
    r'\bskimage\b',
    r'\bscikit-image\b',
    r'\bmatplotlib\.image\b',
    r'\bimread\b',
    r'\bimwrite\b',
    r'\bimshow\b',
    r'\bimsave\b',

    # ======================
    # CTYPES / DLL LOADING
    # ======================
    r'\bctypes\b',
    r'\bctypes\.(CDLL|WinDLL|PyDLL|cdll|windll|oledll|py_object|Structure|Union)\b',
    r'\bCDLL\b',
    r'\bWinDLL\b',
    r'\blibc\b',
    r'\bFILE_p\b',
    r'\blibc\.(system|exec|fork|kill|popen)\b',
    r'\bmemset\b',
    r'\bmemcpy\b',
    r'\bmprotect\b',
    r'\bmmap\b',
    r'\bVirtualAlloc\b',
    r'\bCreateProcess\b',
    r'\bLoadLibrary\b',
    r'\bGetProcAddress\b',

    # ======================
    # EXEC / SUBPROCESS
    # ======================
    r'\bsubprocess\b',
    r'\bsubprocess\.(Popen|call|run|check_output|getoutput|getstatusoutput)\b',
    r'\beval\b',
    r'\bexec\b',
    r'\bcompile\b',
    r'\b__import__\b',

    # ======================
    # FILE SYSTEM / DATA READ
    # ======================
    r'\bopen\s*\(',
    r'\bread\s*\(',
    r'\bpathlib\b',
    r'\bglob\b',
    r'\bshutil\b',
    r'\bshutil\.(rmtree|copytree|move|disk_usage)\b',
    r'\bzipfile\b',
    r'\btempfile\b',
    r'\bcPickle\b',
    r'\bshelve\b',
    r'\bsqlite3\b',
    r'\bpandas\.(read_csv|read_excel|read_json)\b',

    # ======================
    # ENV / SECRETS
    # ======================
    r'\bos\.environ\b',
    r'\bdotenv\b',
    r'\bload_dotenv\b',
    r'\bprintenv\b',
    r'\benv\b',
    r'\bgetpass\b',
    r'\bkeyring\b',
    r'\bconfigparser\b',
    r'\byaml\b',
    r'\bjson\.load\b',

    # ======================
    # NETWORK / DATA EXFIL
    # ======================
    r'\bsocket\b',
    r'\bsocket\.(socket|create_connection|gethostname|gethostbyname)\b',
    r'\brequests\b',
    r'\brequests\.(get|post|put|delete|head|request)\b',
    r'\burllib\b',
    r'\burllib2\b',
    r'\burllib3\b',
    r'\bhttp\.client\b',
    r'\bwebsocket\b',
    r'\basyncio\.open_connection\b',
    r'\bwget\b',
    r'\bcurl\b',
    r'\bdownload\b',
    r'\bftplib\b',
    r'\bsmtplib\b',
    r'\bpoplib\b',
    r'\bimaplib\b',
    r'\btelnetlib\b',

    # ======================
    # SSH / REMOTE ACCESS
    # ======================
    r'\bparamiko\b',
    r'\bscp\b',
    r'\bssh\b',
    r'\bsshlib\b',
    r'\bpexpect\b',
    r'\bfabric\b',

    # ======================
    # SYSTEM INFO LEAK
    # ======================
    r'\bpsutil\b',
    r'\bplatform\b',
    r'\bplatform\.(node|processor|machine|architecture|system|version)\b',
    r'\bcmdline\b',
    r'\bpid\b',
    r'/proc/',
    r'\bmem\b',
    r'\bcpu\b',
    r'\bhostname\b',
    r'\buname\b',
    r'\bwhoami\b',

    # ======================
    # PYTHON INTERNAL ABUSE
    # ======================
    r'\bglobals\b',
    r'\blocals\b',
    r'\bvars\b',
    r'\binspect\b',
    r'\bmarshal\b',
    r'\bpickle\b',
    r'\bimportlib\b',
    r'\b__builtins__\b',
    r'\b__import__\b',
    r'\b__loader__\b',
    r'\b__file__\b',
    r'\b__package__\b',
    r'\b__spec__\b',
    r'\b__code__\b',
    r'\b__dict__\b',
    r'\bgetattr\b',
    r'\bsetattr\b',
    r'\bdelattr\b',
    r'\bhasattr\b',
    r'\bcallable\b',

    # ======================
    # TELEGRAM / BOT CONTROL
    # ======================
    r'\btelebot\b',
    r'\btelebot\.types\b',
    r'\baiogram\b',
    r'\bpyrogram\b',
    r'\btelegram\.ext\b',
    r'\btelegram\.bot\b',

    # ======================
    # LINUX / SHELL / BACKDOOR
    # ======================
    r'/bin/sh',
    r'/bin/bash',
    r'/bin/zsh',
    r'/bin/dash',
    r'nc\s+-e',
    r'netcat',
    r'\bbase64\b',
    r'\becho\b.*\|',
    r'\bawk\b',
    r'\bsed\b',
    r'\bfind\b',
    r'\bxargs\b',
    r'\bcrontab\b',
    r'\bservice\b',
    r'\bsystemctl\b',
    r'\btop\b',
    r'\bps\b',
    r'\bhtop\b',
    r'\bifconfig\b',
    r'\bip\s+a',
    r'\bss\b',
    r'\blsof\b',
    r'\bnetstat\b',

    # ======================
    # SSH KEYS / USER DATA
    # ======================
    r'/etc/passwd',
    r'/etc/shadow',
    r'/etc/hosts',
    r'/etc/resolv.conf',
    r'\.ssh/',
    r'id_rsa',
    r'id_dsa',
    r'authorized_keys',
    r'known_hosts',
    r'\.bashrc',
    r'\.bash_profile',
    r'\.zshrc',
    r'\.profile',

    # ======================
    # DATABASE ACCESS
    # ======================
    r'\bsqlite3\b',
    r'\bmysql\b',
    r'\bmysql\.connector\b',
    r'\bpsycopg2\b',
    r'\bpymongo\b',
    r'\bredis\b',

    # ======================
    # CRYPTO / ENCRYPTION
    # ======================
    r'\bcrypt\b',
    r'\bhashlib\b',
    r'\bhmac\b',
    r'\bssl\b',
    r'\btls\b',
    r'\bCrypto\b',
    r'\bcryptography\b',

    # ======================
    # PROCESS CONTROL
    # ======================
    r'\bsignal\b',
    r'\bmultiprocessing\b',
    r'\bthreading\b',
    r'\bdaemon\b',
    r'\batexit\b',
    r'\bexit\b',
    r'\bquit\b',

    # ======================
    # GUI / SCREEN CAPTURE
    # ======================
    r'\bpyautogui\b',
    r'\bselenium\b',
    r'\bpyscreenshot\b',
    r'\bImageGrab\b',

    # ======================
    # KEYLOGGING / INPUT
    # ======================
    r'\bpynput\b',
    r'\bkeyboard\b',
    r'\bmouse\b',
    r'\bgetch\b',

    # ======================
    # MISC DANGEROUS
    # ======================
    r'\.name\b',
    r'\.__name__\b',
    r'\.__class__\b',
    r'\.__bases__\b',
    r'\.__subclasses__\b',
    r'\.__mro__\b',
    r'\.__dictitems__\b',
    r'\.__reduce__\b',
    r'\.__reduce_ex__\b',
    r'\.__getstate__\b',
    r'\.__setstate__\b',

    # ======================
    # WINDOWS SPECIFIC
    # ======================
    r'\bwin32api\b',
    r'\bwin32com\b',
    r'\bwin32con\b',
    r'\bwin32event\b',
    r'\bwin32file\b',
    r'\bwin32process\b',
    r'\bwin32security\b',
    r'\bwmi\b',
    r'\bregedit\b',
    r'\bregistry\b',
    r'\bGetAsyncKeyState\b',
    r'\bSetWindowsHookEx\b',
    r'\btaskkill\b',
    r'\btasklist\b',
    r'\bschtasks\b',

    # ======================
    # ANTI-DEBUG / ANTI-VM
    # ======================
    r'\bptrace\b',
    r'\bdebugger\b',
    r'\bisatty\b',
    r'\bwindbg\b',
    r'\bollydbg\b',

    # ======================
    # MEMORY MANIPULATION
    # ======================
    r'\bmmap\b',
    r'\bmprotect\b',
    r'\bbrk\b',
    r'\bsbrk\b',
    r'\bmalloc\b',
    r'\bfree\b',
    r'\brealloc\b',
    r'\bVirtualAlloc\b',
    r'\bVirtualProtect\b',
    r'\bVirtualFree\b',
    r'\bHeapAlloc\b',
    r'\bHeapFree\b',

    # ======================
    # CODE INJECTION
    # ======================
    r'\binject\b',
    r'\bpayload\b',
    r'\bshellcode\b',
    r'\bmetasploit\b',
    r'\bbackdoor\b',
    r'\brootkit\b',
    r'\btrojan\b',
    r'\bmalware\b',
    r'\bexploit\b',
    r'\bvirus\b',
    r'\bworm\b',

    # ======================
    # NETWORK SCANNING
    # ======================
    r'\bnmap\b',
    r'\bnping\b',
    r'\bscapy\b',
    r'\barp\b',
    r'\bping\b',
    r'\btraceroute\b',
    r'\broute\b',
    r'\bifconfig\b',
    r'\bipconfig\b',
    r'\bnetstat\b',
    r'\bss\b',

    # ======================
    # PRIVILEGE ESCALATION
    # ======================
    r'\bsudo\b',
    r'\bsu\b',
    r'\brunas\b',
    r'\bprivilege\b',
    r'\bescalation\b',
    r'\buac\b',
    r'\bbypassuac\b',

    # ======================
    # PERSISTENCE
    # ======================
    r'\bregistry\b',
    r'\bstartup\b',
    r'\bautostart\b',
    r'\bscheduled\s*task\b',
    r'\bcron\b',
    r'\bat\b',
    r'\binit\.d\b',
    r'\bsystemd\b',
    r'\blaunchd\b',
    r'\bplist\b',

    # ======================
    # MORE DESTRUCTIVE COMMANDS
    # ======================
    r'\bmv\s+.*\s+/dev/null',
    r'\b>+\s*.*\.log',
    r'\btar\s+.*--exclude',
    r'\bfuser\b',
    r'\bstrace\b',
    r'\bltrace\b',
    r'\bgdb\b',
    r'\bobjdump\b',
    r'\bstrings\b',
    r'\bhexdump\b',
    r'\bxxd\b',
    r'\bod\b',
    r'\bsize\b',
    r'\bnm\b',
    r'\breadelf\b',
    r'\bldd\b',
    r'\bfile\b',
    r'\bwhich\b',
    r'\bwhereis\b',
    r'\blocate\b',
    r'\bupdatedb\b',
    r'\bmake\b',
    r'\bgcc\b',
    r'\bg\+\+\b',
    r'\bclang\b',
    r'\bclang\+\+\b',
    r'\bpython\d*\s+-c',
    r'\bperl\s+-e',
    r'\bruby\s+-e',
    r'\bphp\s+-r',
    r'\blua\s+-e',
    r'\bnode\s+-e',
    r'\bwget\s+.*\|\s*sh',
    r'\bcurl\s+.*\|\s*sh',
    r'\bwget\s+.*\|\s*bash',
    r'\bcurl\s+.*\|\s*bash',
    r'\bchattr\s+\+i',
    r'\bchattr\s+-i',
    r'\bsetfacl\b',
    r'\bgetfacl\b',
    r'\bchown\s+.*:.*',
    r'\bchgrp\b',
    r'\busermod\b',
    r'\bgroupmod\b',
    r'\badduser\b',
    r'\baddgroup\b',
    r'\bdeluser\b',
    r'\bdelgroup\b',
    r'\bpasswd\b',
    r'\bvisudo\b',
    r'\bed\b',
    r'\bex\b',
    r'\bvi\b',
    r'\bvim\b',
    r'\bnano\b',
    r'\bemacs\b',
    r'\bpico\b',
    r'\bmicro\b',
    r'\bne\b',

    # ======================
    # ADDITIONAL SECURITY PATTERNS
    # ======================
    r'\b__import__\s*\(',
    r'\bgetattr\s*\(',
    r'\bsetattr\s*\(',
    r'\bdelattr\s*\(',
    r'\bhasattr\s*\(',
    r'\b__getattr__\b',
    r'\b__setattr__\b',
    r'\b__delattr__\b',
    r'\b__getattribute__\b',
    r'\b__call__\b',
    r'\b__enter__\b',
    r'\b__exit__\b',
    r'\b__new__\b',
    r'\b__init__\b',
    r'\b__del__\b',
    r'\b__repr__\b',
    r'\b__str__\b',
    r'\b__bytes__\b',
    r'\b__format__\b',
    r'\b__lt__\b',
    r'\b__le__\b',
    r'\b__eq__\b',
    r'\b__ne__\b',
    r'\b__gt__\b',
    r'\b__ge__\b',
    r'\b__hash__\b',
    r'\b__bool__\b',
    r'\b__getitem__\b',
    r'\b__setitem__\b',
    r'\b__delitem__\b',
    r'\b__iter__\b',
    r'\b__next__\b',
    r'\b__reversed__\b',
    r'\b__contains__\b',
    r'\b__len__\b',
    r'\b__length_hint__\b',
    r'\b__missing__\b',
    r'\b__copy__\b',
    r'\b__deepcopy__\b'
]
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            for file_info in zip_ref.infolist():
                if file_info.filename.endswith(('.py', '.js', '.zip', '.txt', '.sh', '.bat', '.cmd')):
                    with zip_ref.open(file_info.filename) as f:
                        try:
                            content = f.read().decode('utf-8', errors='ignore')
                        except:
                            continue
                        
                        for pattern in dangerous_patterns:
                            if re.search(pattern, content, re.IGNORECASE):
                                return False, f"File {file_info.filename} contains dangerous command: {pattern}"
        return True, "Archive is safe"
    except Exception as e:
        return False, f"Error scanning archive: {str(e)}"

# --- Mandatory Channels Functions ---
def is_user_member(user_id, channel_id):
    """Check if user is member of a channel"""
    try:
        chat_member = bot.get_chat_member(channel_id, user_id)
        return chat_member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        logger.error(f"Error checking channel membership for {user_id} in {channel_id}: {e}")
        return False

def check_mandatory_subscription(user_id):
    """Check if user is subscribed to all mandatory channels"""
    if not mandatory_channels:
        return True, []  # No mandatory channels exist
    
    not_joined = []
    for channel_id, channel_info in mandatory_channels.items():
        if not is_user_member(user_id, channel_id):
            not_joined.append((channel_id, channel_info))
    
    if not_joined:
        return False, not_joined
    return True, []

def save_mandatory_channel(channel_id, channel_username, channel_name, added_by):
    """Save mandatory channel to database"""
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            added_date = datetime.now().isoformat()
            c.execute('INSERT OR REPLACE INTO mandatory_channels (channel_id, channel_username, channel_name, added_by, added_date) VALUES (?, ?, ?, ?, ?)',
                      (channel_id, channel_username, channel_name, added_by, added_date))
            conn.commit()
            mandatory_channels[channel_id] = {
                'username': channel_username,
                'name': channel_name
            }
            logger.info(f"Saved mandatory channel: {channel_name} ({channel_id})")
            return True
        except sqlite3.Error as e:
            logger.error(f"❌ SQLite error saving channel: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error saving channel: {e}", exc_info=True)
            return False
        finally:
            conn.close()

def remove_mandatory_channel_db(channel_id):
    """Remove mandatory channel from database"""
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            c.execute('DELETE FROM mandatory_channels WHERE channel_id = ?', (channel_id,))
            conn.commit()
            if channel_id in mandatory_channels:
                del mandatory_channels[channel_id]
            logger.info(f"Removed mandatory channel: {channel_id}")
            return True
        except sqlite3.Error as e:
            logger.error(f"❌ SQLite error removing channel: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error removing channel: {e}", exc_info=True)
            return False
        finally:
            conn.close()

def create_mandatory_channels_menu():
    """Create mandatory channels management menu"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.row(
        types.InlineKeyboardButton('➕ Add Channel', callback_data='add_mandatory_channel'),
        types.InlineKeyboardButton('➖ Remove Channel', callback_data='remove_mandatory_channel')
    )
    markup.row(types.InlineKeyboardButton('📋 List Channels', callback_data='list_mandatory_channels'))
    markup.row(types.InlineKeyboardButton('🔙 Back to Main', callback_data='back_to_main'))
    return markup

def create_subscription_check_message(not_joined_channels):
    """Create subscription verification message"""
    message = "\U0001F4E1 one step left \u2014 join these channels:\n\n"
    
    markup = types.InlineKeyboardMarkup()
    
    for channel_id, channel_info in not_joined_channels:
        channel_username = channel_info.get('username', '')
        channel_name = channel_info.get('name', 'Channel')
        
        if channel_username:
            channel_link = f"https://t.me/{channel_username.replace('@', '')}"
        else:
            channel_link = f"https://t.me/c/{channel_id.replace('-100', '')}"
        
        message += f"• {channel_name}\n"
        markup.add(types.InlineKeyboardButton(f"{channel_name}", url=channel_link))
    
    markup.add(types.InlineKeyboardButton("\u2705 i joined \u2014 verify", callback_data='check_subscription_status'))
    
    return message, markup

# --- Database Lock ---
DB_LOCK = threading.Lock()

# --- User Management Functions ---
def is_user_banned(user_id):
    """Check if user is banned"""
    return user_id in banned_users

def ban_user_db(user_id, reason, banned_by):
    """Ban a user"""
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            ban_date = datetime.now().isoformat()
            c.execute('INSERT OR REPLACE INTO banned_users (user_id, reason, banned_by, ban_date) VALUES (?, ?, ?, ?)',
                      (user_id, reason, banned_by, ban_date))
            conn.commit()
            banned_users.add(user_id)
            logger.warning(f"User {user_id} banned by {banned_by}. Reason: {reason}")
            return True
        except sqlite3.Error as e:
            logger.error(f"❌ SQLite error banning user {user_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error banning user {user_id}: {e}", exc_info=True)
            return False
        finally:
            conn.close()

def unban_user_db(user_id):
    """Unban a user"""
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            c.execute('DELETE FROM banned_users WHERE user_id = ?', (user_id,))
            conn.commit()
            banned_users.discard(user_id)
            logger.info(f"User {user_id} unbanned")
            return True
        except sqlite3.Error as e:
            logger.error(f"❌ SQLite error unbanning user {user_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error unbanning user {user_id}: {e}", exc_info=True)
            return False
        finally:
            conn.close()

def set_user_limit_db(user_id, limit, set_by):
    """Set custom file limit for a user"""
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            set_date = datetime.now().isoformat()
            c.execute('INSERT OR REPLACE INTO user_limits (user_id, file_limit, set_by, set_date) VALUES (?, ?, ?, ?)',
                      (user_id, limit, set_by, set_date))
            conn.commit()
            user_limits[user_id] = limit
            logger.info(f"Set file limit {limit} for user {user_id} by {set_by}")
            return True
        except sqlite3.Error as e:
            logger.error(f"❌ SQLite error setting limit for user {user_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error setting limit for user {user_id}: {e}", exc_info=True)
            return False
        finally:
            conn.close()

def remove_user_limit_db(user_id):
    """Remove custom file limit for a user"""
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            c.execute('DELETE FROM user_limits WHERE user_id = ?', (user_id,))
            conn.commit()
            if user_id in user_limits:
                del user_limits[user_id]
            logger.info(f"Removed custom limit for user {user_id}")
            return True
        except sqlite3.Error as e:
            logger.error(f"❌ SQLite error removing limit for user {user_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error removing limit for user {user_id}: {e}", exc_info=True)
            return False
        finally:
            conn.close()

# --- Modified Helper Functions ---
def get_user_folder(user_id):
    """Get or create user's folder for storing files"""
    user_folder = os.path.join(UPLOAD_BOTS_DIR, str(user_id))
    os.makedirs(user_folder, exist_ok=True)
    return user_folder

def get_user_file_limit(user_id):
    """Get the file upload limit for a user"""
    if user_id == OWNER_ID: return OWNER_LIMIT
    if user_id in admin_ids: return ADMIN_LIMIT
    if user_id in user_limits: return user_limits[user_id]
    if user_id in user_subscriptions and user_subscriptions[user_id]['expiry'] > datetime.now():
        return SUBSCRIBED_USER_LIMIT
    return FREE_USER_LIMIT

def get_user_file_count(user_id):
    """Get the number of files uploaded by a user"""
    return len(user_files.get(user_id, []))

def is_bot_running(script_owner_id, file_name):
    """Check if a bot script is currently running for a specific user"""
    script_key = f"{script_owner_id}_{file_name}"
    script_info = bot_scripts.get(script_key)
    if script_info and script_info.get('process'):
        try:
            proc = psutil.Process(script_info['process'].pid)
            is_running = proc.is_running() and proc.status() != psutil.STATUS_ZOMBIE
            if not is_running:
                logger.warning(f"Process {script_info['process'].pid} for {script_key} found in memory but not running/zombie. Cleaning up.")
                if 'log_file' in script_info and hasattr(script_info['log_file'], 'close') and not script_info['log_file'].closed:
                    try:
                        script_info['log_file'].close()
                    except Exception as log_e:
                        logger.error(f"Error closing log file during zombie cleanup {script_key}: {log_e}")
                if script_key in bot_scripts:
                    del bot_scripts[script_key]
            return is_running
        except psutil.NoSuchProcess:
            logger.warning(f"Process for {script_key} not found (NoSuchProcess). Cleaning up.")
            if 'log_file' in script_info and hasattr(script_info['log_file'], 'close') and not script_info['log_file'].closed:
                try:
                     script_info['log_file'].close()
                except Exception as log_e:
                     logger.error(f"Error closing log file during cleanup of non-existent process {script_key}: {log_e}")
            if script_key in bot_scripts:
                 del bot_scripts[script_key]
            return False
        except Exception as e:
            logger.error(f"Error checking process status for {script_key}: {e}", exc_info=True)
            return False
    return False

def kill_process_tree(process_info):
    """Kill a process and all its children, ensuring log file is closed."""
    pid = None
    log_file_closed = False
    script_key = process_info.get('script_key', 'N/A') 

    try:
        if 'log_file' in process_info and hasattr(process_info['log_file'], 'close') and not process_info['log_file'].closed:
            try:
                process_info['log_file'].close()
                log_file_closed = True
                logger.info(f"Closed log file for {script_key} (PID: {process_info.get('process', {}).get('pid', 'N/A')})")
            except Exception as log_e:
                logger.error(f"Error closing log file during kill for {script_key}: {log_e}")

        process = process_info.get('process')
        if process and hasattr(process, 'pid'):
           pid = process.pid
           if pid: 
                try:
                    parent = psutil.Process(pid)
                    children = parent.children(recursive=True)
                    logger.info(f"Attempting to kill process tree for {script_key} (PID: {pid}, Children: {[c.pid for c in children]})")

                    for child in children:
                        try:
                            child.terminate()
                            logger.info(f"Terminated child process {child.pid} for {script_key}")
                        except psutil.NoSuchProcess:
                            logger.warning(f"Child process {child.pid} for {script_key} already gone.")
                        except Exception as e:
                            logger.error(f"Error terminating child {child.pid} for {script_key}: {e}. Trying kill...")
                            try: child.kill(); logger.info(f"Killed child process {child.pid} for {script_key}")
                            except Exception as e2: logger.error(f"Failed to kill child {child.pid} for {script_key}: {e2}")

                    gone, alive = psutil.wait_procs(children, timeout=1)
                    for p in alive:
                        logger.warning(f"Child process {p.pid} for {script_key} still alive. Killing.")
                        try: p.kill()
                        except Exception as e: logger.error(f"Failed to kill child {p.pid} for {script_key} after wait: {e}")

                    try:
                        parent.terminate()
                        logger.info(f"Terminated parent process {pid} for {script_key}")
                        try: parent.wait(timeout=1)
                        except psutil.TimeoutExpired:
                            logger.warning(f"Parent process {pid} for {script_key} did not terminate. Killing.")
                            parent.kill()
                            logger.info(f"Killed parent process {pid} for {script_key}")
                    except psutil.NoSuchProcess:
                        logger.warning(f"Parent process {pid} for {script_key} already gone.")
                    except Exception as e:
                        logger.error(f"Error terminating parent {pid} for {script_key}: {e}. Trying kill...")
                        try: parent.kill(); logger.info(f"Killed parent process {pid} for {script_key}")
                        except Exception as e2: logger.error(f"Failed to kill parent {pid} for {script_key}: {e2}")

                except psutil.NoSuchProcess:
                    logger.warning(f"Process {pid or 'N/A'} for {script_key} not found during kill. Already terminated?")
           else: logger.error(f"Process PID is None for {script_key}.")
        elif log_file_closed: logger.warning(f"Process object missing for {script_key}, but log file closed.")
        else: logger.error(f"Process object missing for {script_key}, and no log file. Cannot kill.")
    except Exception as e:
        logger.error(f"❌ Unexpected error killing process tree for PID {pid or 'N/A'} ({script_key}): {e}", exc_info=True)

# --- Map Telegram import names to actual PyPI package names ---
TELEGRAM_MODULES = {
    # Main Bot Frameworks
    'telebot': 'pyTelegramBotAPI',
    'telegram': 'python-telegram-bot',
    'python_telegram_bot': 'python-telegram-bot',
    'aiogram': 'aiogram',
    'pyrogram': 'pyrogram',
    'telethon': 'telethon',
    'telethon.sync': 'telethon', # Handle specific imports
    'from telethon.sync import telegramclient': 'telethon', # Example

    # Additional Libraries (add more specific mappings if import name differs)
    'telepot': 'telepot',
    'pytg': 'pytg',
    'tgcrypto': 'tgcrypto',
    'telegram_upload': 'telegram-upload',
    'telegram_send': 'telegram-send',
    'telegram_text': 'telegram-text',

    # MTProto & Low-Level
    'mtproto': 'telegram-mtproto', # Example, check actual package name
    'tl': 'telethon',  # Part of Telethon, install 'telethon'

    # Utilities & Helpers (examples, verify package names)
    'telegram_utils': 'telegram-utils',
    'telegram_logger': 'telegram-logger',
    'telegram_handlers': 'python-telegram-handlers',

    # Database Integrations (examples)
    'telegram_redis': 'telegram-redis',
    'telegram_sqlalchemy': 'telegram-sqlalchemy',

    # Payment & E-commerce (examples)
    'telegram_payment': 'telegram-payment',
    'telegram_shop': 'telegram-shop-sdk',

    # Testing & Debugging (examples)
    'pytest_telegram': 'pytest-telegram',
    'telegram_debug': 'telegram-debug',

    # Scraping & Analytics (examples)
    'telegram_scraper': 'telegram-scraper',
    'telegram_analytics': 'telegram-analytics',

    # NLP & AI (examples)
    'telegram_nlp': 'telegram-nlp-toogit',
    'telegram_ai': 'telegram-ai', # Assuming this exists

    # Web & API Integration (examples)
    'telegram_api': 'telegram-api-client',
    'telegram_web': 'telegram-web-integration',

    # Gaming & Interactive (examples)
    'telegram_games': 'telegram-games',
    'telegram_quiz': 'telegram-quiz-bot',

    # File & Media Handling (examples)
    'telegram_ffmpeg': 'telegram-ffmpeg',
    'telegram_media': 'telegram-media-utils',

    # Security & Encryption (examples)
    'telegram_2fa': 'telegram-twofa',
    'telegram_crypto': 'telegram-crypto-bot',

    # Localization & i18n (examples)
    'telegram_i18n': 'telegram-i18n',
    'telegram_translate': 'telegram-translate',

    # Common non-telegram examples
    'bs4': 'beautifulsoup4',
    'requests': 'requests',
    'pillow': 'Pillow', # Note the capitalization difference
    'cv2': 'opencv-python', # Common import name for OpenCV
    'yaml': 'PyYAML',
    'dotenv': 'python-dotenv',
    'dateutil': 'python-dateutil',
    'pandas': 'pandas',
    'numpy': 'numpy',
    'flask': 'Flask',
    'django': 'Django',
    'sqlalchemy': 'SQLAlchemy',
    'asyncio': None, # Core module, should not be installed
    'json': None,    # Core module
    'datetime': None,# Core module
    'os': None,      # Core module
    'sys': None,     # Core module
    're': None,      # Core module
    'time': None,    # Core module
    'math': None,    # Core module
    'random': None,  # Core module
    'logging': None, # Core module
    'threading': None,# Core module
    'subprocess':None,# Core module
    'zipfile':None,  # Core module
    'tempfile':None, # Core module
    'shutil':None,   # Core module
    'sqlite3':None,  # Core module
    'psutil': 'psutil',
    'atexit': None   # Core module
}

# --- Manual Modules Installation System ---
def save_install_log(user_id, module_name, package_name, status, log):
    """Save installation log to database"""
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            install_date = datetime.now().isoformat()
            c.execute('INSERT INTO install_logs (user_id, module_name, package_name, status, log, install_date) VALUES (?, ?, ?, ?, ?, ?)',
                      (user_id, module_name, package_name, status, log, install_date))
            conn.commit()
            logger.info(f"Saved install log for user {user_id}: {module_name} - {status}")
        except sqlite3.Error as e:
            logger.error(f"❌ SQLite error saving install log: {e}")
        except Exception as e:
            logger.error(f"❌ Unexpected error saving install log: {e}", exc_info=True)
        finally:
            conn.close()

def attempt_install_pip(module_name, message, manual_request=False):
    """Install Python package via pip"""
    package_name = TELEGRAM_MODULES.get(module_name.lower(), module_name) 
    if package_name is None: 
        logger.info(f"Module '{module_name}' is core. Skipping pip install.")
        return False, "Core module - no installation needed"
    
    try:
        if manual_request:
            bot.reply_to(message, f"\U0001F9E9 admin asked for `{module_name}` \u2014 queued.", parse_mode='Markdown')
        else:
            bot.reply_to(message, f"\U0001F40D missing `{module_name}` \u2014 fetching `{package_name}`...", parse_mode='Markdown')
        
        command = [sys.executable, '-m', 'pip', 'install', package_name]
        logger.info(f"Running install: {' '.join(command)}")
        result = subprocess.run(command, capture_output=True, text=True, check=False, encoding='utf-8', errors='ignore')
        
        if result.returncode == 0:
            log_msg = f"Installed {package_name}. Output:\n{result.stdout}"
            logger.info(log_msg)
            success_msg = f"✅ Package `{package_name}` (for `{module_name}`) installed successfully."
            bot.reply_to(message, success_msg, parse_mode='Markdown')
            save_install_log(message.from_user.id, module_name, package_name, "success", log_msg)
            return True, log_msg
        else:
            error_msg = f"❌ Failed to install `{package_name}` for `{module_name}`.\nLog:\n```\n{result.stderr or result.stdout}\n```"
            logger.error(error_msg)
            if len(error_msg) > 4000: error_msg = error_msg[:4000] + "\n... (Log truncated)"
            bot.reply_to(message, error_msg, parse_mode='Markdown')
            save_install_log(message.from_user.id, module_name, package_name, "failed", error_msg)
            return False, error_msg
    except Exception as e:
        error_msg = f"❌ Error installing `{package_name}`: {str(e)}"
        logger.error(error_msg, exc_info=True)
        bot.reply_to(message, error_msg)
        save_install_log(message.from_user.id, module_name, package_name, "error", error_msg)
        return False, error_msg

def attempt_install_npm(module_name, user_folder, message, manual_request=False):
    """Install Node package via npm"""
    try:
        if manual_request:
            bot.reply_to(message, f"\U0001F9E9 admin asked for node pkg `{module_name}` \u2014 queued.", parse_mode='Markdown')
        else:
            bot.reply_to(message, f"\U0001F7E0 missing `{module_name}` \u2014 installing locally...", parse_mode='Markdown')
        
        command = ['npm', 'install', module_name]
        logger.info(f"Running npm install: {' '.join(command)} in {user_folder}")
        result = subprocess.run(command, capture_output=True, text=True, check=False, cwd=user_folder, encoding='utf-8', errors='ignore')
        
        if result.returncode == 0:
            log_msg = f"Installed {module_name}. Output:\n{result.stdout}"
            logger.info(log_msg)
            success_msg = f"✅ Node package `{module_name}` installed locally."
            bot.reply_to(message, success_msg, parse_mode='Markdown')
            save_install_log(message.from_user.id, module_name, module_name, "success", log_msg)
            return True, log_msg
        else:
            error_msg = f"❌ Failed to install Node package `{module_name}`.\nLog:\n```\n{result.stderr or result.stdout}\n```"
            logger.error(error_msg)
            if len(error_msg) > 4000: error_msg = error_msg[:4000] + "\n... (Log truncated)"
            bot.reply_to(message, error_msg, parse_mode='Markdown')
            save_install_log(message.from_user.id, module_name, module_name, "failed", error_msg)
            return False, error_msg
    except FileNotFoundError:
         error_msg = "❌ Error: 'npm' not found. Ensure Node.js/npm are installed and in PATH."
         logger.error(error_msg)
         bot.reply_to(message, error_msg)
         save_install_log(message.from_user.id, module_name, module_name, "error", error_msg)
         return False, error_msg
    except Exception as e:
        error_msg = f"❌ Error installing Node package `{module_name}`: {str(e)}"
        logger.error(error_msg, exc_info=True)
        bot.reply_to(message, error_msg)
        save_install_log(message.from_user.id, module_name, module_name, "error", error_msg)
        return False, error_msg

def manual_install_module_init(message):
    """Initialize manual module installation"""
    user_id = message.from_user.id
    
    if is_user_banned(user_id):
        bot.reply_to(message, "\u26D4 your account is restricted from this bot.")
        return
    
    # Check mandatory subscription first
    is_subscribed, not_joined = check_mandatory_subscription(user_id)
    if not is_subscribed and user_id not in admin_ids:
        subscription_message, markup = create_subscription_check_message(not_joined)
        bot.reply_to(message, subscription_message, reply_markup=markup, parse_mode='Markdown')
        return
    
    if bot_locked and user_id not in admin_ids:
        bot.reply_to(message, "⚠️ Bot locked by admin. Try later.")
        return
    
    msg = bot.reply_to(message, "\U0001F9E9 send module name to install\n(e.g. `requests` \u00b7 `pillow` \u00b7 node: `npm:name`)\n/cancel to quit")
    bot.register_next_step_handler(msg, process_manual_install_module)

def process_manual_install_module(message):
    """Process manual module installation"""
    user_id = message.from_user.id
    
    if is_user_banned(user_id):
        bot.reply_to(message, "\u26D4 your account is restricted from this bot.")
        return
    
    if message.text.lower() == '/cancel':
        bot.reply_to(message, "\u2716\uFE0F install cancelled.")
        return
    
    module_name = message.text.strip()
    
    # Check if it's a Node.js module
    if module_name.lower().startswith('npm:'):
        module_name = module_name[4:].strip()
        user_folder = get_user_folder(user_id)
        success, log = attempt_install_npm(module_name, user_folder, message, manual_request=True)
    else:
        # Python module
        success, log = attempt_install_pip(module_name, message, manual_request=True)
    
    if success:
        logger.info(f"User {user_id} manually installed module: {module_name}")

# --- Database Operations ---
def save_user_file(user_id, file_name, file_type='py'):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            c.execute('INSERT OR REPLACE INTO user_files (user_id, file_name, file_type) VALUES (?, ?, ?)',
                      (user_id, file_name, file_type))
            conn.commit()
            if user_id not in user_files: user_files[user_id] = []
            user_files[user_id] = [(fn, ft) for fn, ft in user_files[user_id] if fn != file_name]
            user_files[user_id].append((file_name, file_type))
            logger.info(f"Saved file '{file_name}' ({file_type}) for user {user_id}")
        except sqlite3.Error as e: logger.error(f"❌ SQLite error saving file for user {user_id}, {file_name}: {e}")
        except Exception as e: logger.error(f"❌ Unexpected error saving file for {user_id}, {file_name}: {e}", exc_info=True)
        finally: conn.close()

def remove_user_file_db(user_id, file_name):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            c.execute('DELETE FROM user_files WHERE user_id = ? AND file_name = ?', (user_id, file_name))
            conn.commit()
            if user_id in user_files:
                user_files[user_id] = [f for f in user_files[user_id] if f[0] != file_name]
                if not user_files[user_id]: del user_files[user_id]
            logger.info(f"Removed file '{file_name}' for user {user_id} from DB")
        except sqlite3.Error as e: logger.error(f"❌ SQLite error removing file for {user_id}, {file_name}: {e}")
        except Exception as e: logger.error(f"❌ Unexpected error removing file for {user_id}, {file_name}: {e}", exc_info=True)
        finally: conn.close()

def add_active_user(user_id):
    is_new = user_id not in active_users
    active_users.add(user_id)
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            now = datetime.now().isoformat()
            if is_new:
                c.execute('INSERT OR IGNORE INTO active_users (user_id, join_date, last_seen) VALUES (?, ?, ?)',
                          (user_id, now, now))
            else:
                c.execute('UPDATE active_users SET last_seen = ? WHERE user_id = ?', (now, user_id))
            conn.commit()
            if is_new: logger.info(f"New member registered: {user_id}")
        except sqlite3.Error as e: logger.error(f"❌ SQLite error adding active user {user_id}: {e}")
        except Exception as e: logger.error(f"❌ Unexpected error adding active user {user_id}: {e}", exc_info=True)
        finally: conn.close()

def _sandbox_preexec(user_folder=None):
    """Child-process jail: RAM/CPU/proc/filesize limits. Best-effort on every OS."""
    def _apply():
        try:
            import resource as _res
            lim = {'as': 512*1024*1024, 'cpu': 3600, 'nproc': 24, 'fsize': 200*1024*1024}
            _res.setrlimit(_res.RLIMIT_AS,   (lim['as'],   lim['as']))
            _res.setrlimit(_res.RLIMIT_CPU,  (lim['cpu'],  lim['cpu']))
            _res.setrlimit(_res.RLIMIT_NPROC,(lim['nproc'],lim['nproc']))
            _res.setrlimit(_res.RLIMIT_FSIZE,(lim['fsize'],lim['fsize']))
        except Exception: pass
        try:
            os.setsid()
        except Exception: pass
        if user_folder:
            try: os.chdir(user_folder)
            except Exception: pass
    return _apply

_SANDBOX_ENV = {
    'PATH': '/usr/bin:/bin:/data/data/com.termux/files/usr/bin:/usr/local/bin',
    'HOME': None, 'LANG': 'en_US.UTF-8', 'PYTHONUNBUFFERED': '1',
    'TMPDIR': None,
}
def _clean_env_for(user_folder):
    env = dict(_SANDBOX_ENV)
    env['PATH'] = os.environ.get('PATH', env['PATH'])
    env['HOME'] = user_folder or os.environ.get('HOME','/tmp')
    env['TMPDIR'] = os.path.join(env['HOME'], 'tmp')
    try: os.makedirs(env['TMPDIR'], exist_ok=True)
    except Exception: pass
    keep = ('ANDROID_DATA','ANDROID_ROOT','EXTERNAL_STORAGE','PREFIX','LD_PRELOAD')
    for k in keep:
        if k in os.environ: env[k] = os.environ[k]
    return env

_upload_times = {}
UPLOAD_RATE_LIMIT = (6, 600)

def _rate_ok(user_id):
    """Max UPLOAD_RATE_LIMIT[0] uploads per UPLOAD_RATE_LIMIT[1] sec."""
    import time as _t
    now = _t.time()
    win = _upload_times.get(user_id, [])
    win = [t for t in win if now - t < UPLOAD_RATE_LIMIT[1]]
    if len(win) >= UPLOAD_RATE_LIMIT[0]:
        return False
    win.append(now)
    _upload_times[user_id] = win
    return True

def _touch_user(user_id):
    """Register any interacting user instantly (fixes stale member count)."""
    if user_id not in active_users:
        try: add_active_user(user_id)
        except Exception as e: logger.error(f"touch_user err {user_id}: {e}")

def save_subscription(user_id, expiry):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            expiry_str = expiry.isoformat()
            c.execute('INSERT OR REPLACE INTO subscriptions (user_id, expiry) VALUES (?, ?)', (user_id, expiry_str))
            conn.commit()
            user_subscriptions[user_id] = {'expiry': expiry}
            logger.info(f"Saved subscription for {user_id}, expiry {expiry_str}")
        except sqlite3.Error as e: logger.error(f"❌ SQLite error saving subscription for {user_id}: {e}")
        except Exception as e: logger.error(f"❌ Unexpected error saving subscription for {user_id}: {e}", exc_info=True)
        finally: conn.close()

def remove_subscription_db(user_id):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            c.execute('DELETE FROM subscriptions WHERE user_id = ?', (user_id,))
            conn.commit()
            if user_id in user_subscriptions: del user_subscriptions[user_id]
            logger.info(f"Removed subscription for {user_id} from DB")
        except sqlite3.Error as e: logger.error(f"❌ SQLite error removing subscription for {user_id}: {e}")
        except Exception as e: logger.error(f"❌ Unexpected error removing subscription for {user_id}: {e}", exc_info=True)
        finally: conn.close()

def add_admin_db(admin_id, added_by):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            added_date = datetime.now().isoformat()
            c.execute('INSERT OR IGNORE INTO admins (user_id, added_by, added_date) VALUES (?, ?, ?)', 
                      (admin_id, added_by, added_date))
            conn.commit()
            admin_ids.add(admin_id) 
            logger.info(f"Added admin {admin_id} to DB by {added_by}")
        except sqlite3.Error as e: logger.error(f"❌ SQLite error adding admin {admin_id}: {e}")
        except Exception as e: logger.error(f"❌ Unexpected error adding admin {admin_id}: {e}", exc_info=True)
        finally: conn.close()

def remove_admin_db(admin_id):
    if admin_id == OWNER_ID:
        logger.warning("Attempted to remove OWNER_ID from admins.")
        return False 
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        removed = False
        try:
            c.execute('SELECT 1 FROM admins WHERE user_id = ?', (admin_id,))
            if c.fetchone():
                c.execute('DELETE FROM admins WHERE user_id = ?', (admin_id,))
                conn.commit()
                removed = c.rowcount > 0 
                if removed: admin_ids.discard(admin_id); logger.info(f"Removed admin {admin_id} from DB")
                else: logger.warning(f"Admin {admin_id} found but delete affected 0 rows.")
            else:
                logger.warning(f"Admin {admin_id} not found in DB.")
                admin_ids.discard(admin_id)
            return removed
        except sqlite3.Error as e: logger.error(f"❌ SQLite error removing admin {admin_id}: {e}"); return False
        except Exception as e: logger.error(f"❌ Unexpected error removing admin {admin_id}: {e}", exc_info=True); return False
        finally: conn.close()

# --- Menu creation (Inline and ReplyKeyboards) ---
def create_main_menu_inline(user_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = [
        types.InlineKeyboardButton('📡 ᴜᴘᴅᴀᴛᴇꜱ', url=f'https://t.me/{UPDATE_CHANNEL.replace("@", "")}'),
        types.InlineKeyboardButton('⬆️ ᴅᴇᴘʟᴏʏ ʙᴏᴛ', callback_data='upload'),
        types.InlineKeyboardButton('🗂️ ᴍʏ ʙᴏᴛꜱ', callback_data='check_files'),
        types.InlineKeyboardButton('🌀 ꜱᴘᴇᴇᴅ', callback_data='speed'),
        types.InlineKeyboardButton('🧩 ɪɴꜱᴛᴀʟʟ', callback_data='manual_install'),
        types.InlineKeyboardButton('💬 ᴅᴇᴠᴇʟᴏᴘᴇʀ', url=f'https://t.me/{YOUR_USERNAME.replace("@", "")}')
    ]
    if user_id in admin_ids:
        admin_buttons = [
            types.InlineKeyboardButton('💳 ꜱᴜʙꜱ', callback_data='subscription'),
            types.InlineKeyboardButton('📊 ꜱᴛᴀᴛꜱ', callback_data='stats'),
            types.InlineKeyboardButton('⛔ ʟᴏᴄᴋ ʙᴏᴛ' if not bot_locked else '\U0001F513 ᴜɴʟᴏᴄᴋ ʙᴏᴛ',
                                     callback_data='lock_bot' if not bot_locked else 'unlock_bot'),
            types.InlineKeyboardButton('📮 ʙʀᴏᴀᴅᴄᴀꜱᴛ', callback_data='broadcast'),
            types.InlineKeyboardButton('🛡️ ᴀᴅᴍɪɴ ᴢᴏɴᴇ', callback_data='admin_panel'),
            types.InlineKeyboardButton('♻️ ʀᴜɴ ᴀʟʟ', callback_data='run_all_scripts'),
            types.InlineKeyboardButton('📡 ᴄʜᴀɴɴᴇʟ', callback_data='manage_mandatory_channels'),
            types.InlineKeyboardButton('👥 ᴜꜱᴇʀꜱ', callback_data='user_management'),
            types.InlineKeyboardButton('🧩+ ꜰᴏʀ ᴜꜱᴇʀꜱ', callback_data='admin_install'),
            types.InlineKeyboardButton('🔧 ꜱᴇᴛᴛɪɴɢ', callback_data='admin_settings')
        ]
        markup.add(buttons[1], buttons[2])
        markup.add(buttons[4], buttons[3])
        markup.add(types.InlineKeyboardButton('🌐 ᴡᴇʙ ʜᴏꜱᴛ', callback_data='web_host'),
                   types.InlineKeyboardButton('🌐 ᴍʏ ᴡᴇʙ', callback_data='my_websites'))
        markup.add(admin_buttons[1], admin_buttons[0])
        markup.add(admin_buttons[3], admin_buttons[5])
        markup.add(admin_buttons[2], admin_buttons[7])
        markup.add(admin_buttons[9], admin_buttons[6])
        markup.add(admin_buttons[4])
        markup.add(buttons[0])
        markup.add(buttons[5])
    else:
        markup.add(buttons[1], buttons[2])
        markup.add(buttons[4], buttons[3])
        markup.add(types.InlineKeyboardButton('🌐 ᴡᴇʙ ʜᴏꜱᴛ', callback_data='web_host'),
                   types.InlineKeyboardButton('🌐 ᴍʏ ᴡᴇʙ', callback_data='my_websites'))
        markup.add(types.InlineKeyboardButton('📊 ꜱᴛᴀᴛꜱ', callback_data='stats'))
        markup.add(buttons[0])
        markup.add(buttons[5])
    return markup

def create_reply_keyboard_main_menu(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    layout_to_use = ADMIN_COMMAND_BUTTONS_LAYOUT_USER_SPEC if user_id in admin_ids else COMMAND_BUTTONS_LAYOUT_USER_SPEC
    for row_buttons_text in layout_to_use:
        markup.add(*[types.KeyboardButton(text) for text in row_buttons_text])
    return markup

def create_control_buttons(script_owner_id, file_name, is_running=True):
    markup = types.InlineKeyboardMarkup(row_width=2)
    if is_running:
        markup.row(
            types.InlineKeyboardButton("⏹ ꜱᴛᴏᴘ", callback_data=f'stop_{script_owner_id}_{file_name}'),
            types.InlineKeyboardButton("♻️ ʀᴇꜱᴛᴀʀᴛ", callback_data=f'restart_{script_owner_id}_{file_name}')
        )
        markup.row(
            types.InlineKeyboardButton("🗑 ᴅᴇʟᴇᴛᴇ", callback_data=f'delete_{script_owner_id}_{file_name}'),
            types.InlineKeyboardButton("📝 ʟᴏɢꜱ", callback_data=f'logs_{script_owner_id}_{file_name}')
        )
    else:
        markup.row(
            types.InlineKeyboardButton("▶️ ꜱᴛᴀʀᴛ", callback_data=f'start_{script_owner_id}_{file_name}'),
            types.InlineKeyboardButton("🗑 ᴅᴇʟᴇᴛᴇ", callback_data=f'delete_{script_owner_id}_{file_name}')
        )
        markup.row(
            types.InlineKeyboardButton("📝 ᴠɪᴇᴡ ʟᴏɢꜱ", callback_data=f'logs_{script_owner_id}_{file_name}')
        )
    markup.add(types.InlineKeyboardButton("↩️ ʙᴀᴄᴋ ᴛᴏ ꜰɪʟᴇꜱ", callback_data='check_files'))
    return markup

def create_admin_panel():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.row(
        types.InlineKeyboardButton('➕ ᴀᴅᴅ ᴀᴅᴍɪɴ', callback_data='add_admin'),
        types.InlineKeyboardButton('➖ ʀᴇᴍᴏᴠᴇ ᴀᴅᴍɪɴ', callback_data='remove_admin')
    )
    markup.row(types.InlineKeyboardButton('📋 ᴀᴅᴍɪɴ ʟɪꜱᴛ', callback_data='list_admins'))
    markup.row(types.InlineKeyboardButton('↩️ ʙᴀᴄᴋ', callback_data='back_to_main'))
    return markup

def create_user_management_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.row(
        types.InlineKeyboardButton('⛔ ʙᴀɴ ᴜꜱᴇʀ', callback_data='ban_user'),
        types.InlineKeyboardButton('✅ ᴜɴʙᴀɴ ᴜꜱᴇʀ', callback_data='unban_user')
    )
    markup.row(
        types.InlineKeyboardButton('🔎 ᴜꜱᴇʀ ɪɴꜰᴏ', callback_data='user_info'),
        types.InlineKeyboardButton('👥 ᴀʟʟ ᴜꜱᴇʀꜱ', callback_data='all_users')
    )
    markup.row(
        types.InlineKeyboardButton('🔧 ꜱᴇᴛ ʟɪᴍɪᴛ', callback_data='set_user_limit'),
        types.InlineKeyboardButton('🗑 ʀᴇᴍᴏᴠᴇ ʟɪᴍɪᴛ', callback_data='remove_user_limit')
    )
    markup.row(types.InlineKeyboardButton('↩️ ʙᴀᴄᴋ', callback_data='back_to_main'))
    return markup

def create_subscription_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.row(
        types.InlineKeyboardButton('➕ ᴀᴅᴅ ꜱᴜʙ', callback_data='add_subscription'),
        types.InlineKeyboardButton('➖ ʀᴇᴍᴏᴠᴇ ꜱᴜʙ', callback_data='remove_subscription')
    )
    markup.row(types.InlineKeyboardButton('🔍 ᴄʜᴇᴄᴋ ꜱᴜʙ', callback_data='check_subscription'))
    markup.row(types.InlineKeyboardButton('↩️ ʙᴀᴄᴋ', callback_data='back_to_main'))
    return markup

def create_admin_settings_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.row(
        types.InlineKeyboardButton('🖥 ꜱʏꜱᴛᴇᴍ', callback_data='system_info'),
        types.InlineKeyboardButton('📈 ᴘᴇʀꜰᴏʀᴍᴀɴᴄᴇ', callback_data='bot_performance')
    )
    markup.row(
        types.InlineKeyboardButton('🧹 ᴄʟᴇᴀɴᴜᴘ', callback_data='cleanup_files'),
        types.InlineKeyboardButton('📋 ɪɴꜱᴛᴀʟʟ ʟᴏɢꜱ', callback_data='install_logs')
    )
    markup.row(
        types.InlineKeyboardButton('⏹ ꜱᴛᴏᴘ ᴀʟʟ', callback_data='stop_all_scripts'),
        types.InlineKeyboardButton('♻️ ʀᴜɴ ᴀʟʟ', callback_data='run_all_scripts')
    )
    markup.row(
        types.InlineKeyboardButton('💾 ꜱᴛᴏʀᴀɢᴇ', callback_data='storage_info'),
        types.InlineKeyboardButton('🔄 ʀᴇʙᴏᴏᴛ', callback_data='reboot_bot')
    )
    markup.row(types.InlineKeyboardButton('↩️ ʙᴀᴄᴋ', callback_data='back_to_main'))
    return markup

# --- File Handling ---
def handle_zip_file(downloaded_file_content, file_name_zip, message):
    user_id = message.from_user.id
    user_folder = get_user_folder(user_id)
    temp_dir = None 
    try:
        temp_dir = tempfile.mkdtemp(prefix=f"user_{user_id}_zip_")
        logger.info(f"Temp dir for zip: {temp_dir}")
        zip_path = os.path.join(temp_dir, file_name_zip)
        with open(zip_path, 'wb') as new_file: new_file.write(downloaded_file_content)
        
        # AI security analysis — every zip goes to admin for approval
        ai_report = build_ai_report(zip_path, 'zip', user_id, message.from_user.first_name, file_label=file_name_zip)
        markup = types.InlineKeyboardMarkup()
        markup.row(
            types.InlineKeyboardButton("\u2705 "+_t("approve"), callback_data=f"approve_zip_{user_id}_{file_name_zip}"),
            types.InlineKeyboardButton("\u2716\uFE0F "+_t("reject"), callback_data=f"reject_zip_{user_id}_{file_name_zip}")
        )
        admin_alert = "\U0001F916 \U0001F1E9\u1D1B\u1D1B\u1D1B \u1D20\u1D40\u1D1B\n\n" + ai_report + ALERT_SUFFIX  # 🤖 BOT FILE
        for admin_id in admin_ids:
            head = ("\U0001F916 \U0001F1E9\u1D1B\u1D1B\u1D1B \u1D20\u1D40\u1D1B\n\n"
                    "\U0001F4C1 "+_t("file")+": "+file_name_zip+"\n"
                    "\U0001F464 "+_t("user id")+": "+str(user_id))
            try:
                bot.send_message(admin_id, admin_alert[:2048], reply_markup=markup)
            except Exception as e:
                logger.error(f"Failed to send AI report to admin {admin_id}: {e}")
            try:
                bot.send_document(admin_id, downloaded_file_content,
                                  caption=head[:900],
                                  visible_file_name=file_name_zip)
            except Exception as e:
                logger.error(f"Failed to send file to admin {admin_id}: {e}")

        # Store the file content for later approval
        if user_id not in pending_zip_files:
            pending_zip_files[user_id] = {}
        pending_zip_files[user_id][file_name_zip] = downloaded_file_content

        shutil.rmtree(temp_dir, ignore_errors=True)
        bot.reply_to(message, f"🛡️ ꜱᴇᴄᴜʀɪᴛʏ ʀᴇᴠɪᴇᴡ ɪɴ ᴘʀᴏɢʀᴇꜱꜱ...\n🔔 ʏᴏᴜ'ʟʟ ʙᴇ ɴᴏᴛɪꜰɪᴇᴅ ᴜᴘᴏɴ ᴀᴘᴘʀᴏᴠᴀʟ.")
        return
        
    except zipfile.BadZipFile as e:
        logger.error(f"Bad zip file from {user_id}: {e}")
        bot.reply_to(message, f"\U0001F4A5 broken/corrupt zip. {e}")
    except Exception as e:
        logger.error(f"❌ Error processing zip for {user_id}: {e}", exc_info=True)
        bot.reply_to(message, f"\U0001F4A5 zip problem: {e}")
    finally:
        if temp_dir and os.path.exists(temp_dir):
            try: shutil.rmtree(temp_dir); logger.info(f"Cleaned temp dir: {temp_dir}")
            except Exception as e: logger.error(f"Failed to clean temp dir {temp_dir}: {e}", exc_info=True)

def process_zip_file(zip_path, user_id, user_folder, file_name_zip, message, temp_dir=None):
    """Process ZIP file extraction and setup"""
    cleanup_temp = False
    if temp_dir is None:
        temp_dir = tempfile.mkdtemp(prefix=f"user_{user_id}_zip_")
        cleanup_temp = True
        
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # Check for safe paths
            for member in zip_ref.infolist():
                member_path = os.path.abspath(os.path.join(temp_dir, member.filename))
                if not member_path.startswith(os.path.abspath(temp_dir)):
                    raise zipfile.BadZipFile(f"Zip has unsafe path: {member.filename}")
            zip_ref.extractall(temp_dir)
            logger.info(f"Extracted zip to {temp_dir}")

        extracted_items = os.listdir(temp_dir)
        py_files = [f for f in extracted_items if f.endswith('.py')]
        js_files = [f for f in extracted_items if f.endswith('.js')]
        req_file = 'requirements.txt' if 'requirements.txt' in extracted_items else None
        pkg_json = 'package.json' if 'package.json' in extracted_items else None

        if req_file:
            req_path = os.path.join(temp_dir, req_file)
            logger.info(f"requirements.txt found, installing: {req_path}")
            bot.reply_to(message, f"\U0001F9E9 adding python packages from `{req_file}`...")
            try:
                command = [sys.executable, '-m', 'pip', 'install', '-r', req_path]
                result = subprocess.run(command, capture_output=True, text=True, check=True, encoding='utf-8', errors='ignore')
                logger.info(f"pip install from requirements.txt OK. Output:\n{result.stdout}")
                bot.reply_to(message, f"\u2705 python packages ready.")
            except subprocess.CalledProcessError as e:
                error_msg = f"❌ Failed to install Python deps from `{req_file}`.\nLog:\n```\n{e.stderr or e.stdout}\n```"
                logger.error(error_msg)
                if len(error_msg) > 4000: error_msg = error_msg[:4000] + "\n... (Log truncated)"
                bot.reply_to(message, error_msg, parse_mode='Markdown'); return
            except Exception as e:
                 error_msg = f"❌ Unexpected error installing Python deps: {e}"
                 logger.error(error_msg, exc_info=True); bot.reply_to(message, error_msg); return

        if pkg_json:
            logger.info(f"package.json found, npm install in: {temp_dir}")
            bot.reply_to(message, f"\U0001F9E9 adding node packages from `{pkg_json}`...")
            try:
                command = ['npm', 'install']
                result = subprocess.run(command, capture_output=True, text=True, check=True, cwd=temp_dir, encoding='utf-8', errors='ignore')
                logger.info(f"npm install OK. Output:\n{result.stdout}")
                bot.reply_to(message, f"\u2705 node packages ready.")
            except FileNotFoundError:
                bot.reply_to(message, "\U0001F40B npm missing on host."); return 
            except subprocess.CalledProcessError as e:
                error_msg = f"❌ Failed to install Node deps from `{pkg_json}`.\nLog:\n```\n{e.stderr or e.stdout}\n```"
                logger.error(error_msg)
                if len(error_msg) > 4000: error_msg = error_msg[:4000] + "\n... (Log truncated)"
                bot.reply_to(message, error_msg, parse_mode='Markdown'); return
            except Exception as e:
                 error_msg = f"❌ Unexpected error installing Node deps: {e}"
                 logger.error(error_msg, exc_info=True); bot.reply_to(message, error_msg); return

        main_script_name = None; file_type = None
        preferred_py = ['main.py', 'bot.py', 'app.py']; preferred_js = ['index.js', 'main.js', 'bot.js', 'app.js']
        for p in preferred_py:
            if p in py_files: main_script_name = p; file_type = 'py'; break
        if not main_script_name:
             for p in preferred_js:
                 if p in js_files: main_script_name = p; file_type = 'js'; break
        if not main_script_name:
            if py_files: main_script_name = py_files[0]; file_type = 'py'
            elif js_files: main_script_name = js_files[0]; file_type = 'js'
        if not main_script_name:
            bot.reply_to(message, "\U0001F50D no .py/.js entry found inside the zip!"); return

        logger.info(f"Moving extracted files from {temp_dir} to {user_folder}")
        moved_count = 0
        for item_name in os.listdir(temp_dir):
            src_path = os.path.join(temp_dir, item_name)
            dest_path = os.path.join(user_folder, item_name)
            if os.path.isdir(dest_path): shutil.rmtree(dest_path)
            elif os.path.exists(dest_path): os.remove(dest_path)
            shutil.move(src_path, dest_path); moved_count +=1
        logger.info(f"Moved {moved_count} items to {user_folder}")

        save_user_file(user_id, main_script_name, file_type)
        logger.info(f"Saved main script '{main_script_name}' ({file_type}) for {user_id} from zip.")
        main_script_path = os.path.join(user_folder, main_script_name)
        bot.reply_to(message, f"\U0001F5C2\uFE0F unpacked! launching `{main_script_name}`...", parse_mode='Markdown')

        # Use user_id as script_owner_id for script key context
        if file_type == 'py':
             threading.Thread(target=run_script, args=(main_script_path, user_id, user_folder, main_script_name, message)).start()
        elif file_type == 'js':
             threading.Thread(target=run_js_script, args=(main_script_path, user_id, user_folder, main_script_name, message)).start()
             
    except Exception as e:
        logger.error(f"Error processing zip file: {e}", exc_info=True)
        bot.reply_to(message, f"\U0001F4A5 zip problem: {e}")
    finally:
        if cleanup_temp and temp_dir and os.path.exists(temp_dir):
            try: shutil.rmtree(temp_dir); logger.info(f"Cleaned temp dir: {temp_dir}")
            except Exception as e: logger.error(f"Failed to clean temp dir {temp_dir}: {e}", exc_info=True)

def handle_js_file(file_path, script_owner_id, user_folder, file_name, message):
    try:
        save_user_file(script_owner_id, file_name, 'js')
        threading.Thread(target=run_js_script, args=(file_path, script_owner_id, user_folder, file_name, message)).start()
    except Exception as e:
        logger.error(f"❌ Error processing JS file {file_name} for {script_owner_id}: {e}", exc_info=True)
        bot.reply_to(message, f"\U0001F4A5 js file problem: {e}")

def handle_py_file(file_path, script_owner_id, user_folder, file_name, message):
    try:
        save_user_file(script_owner_id, file_name, 'py')
        threading.Thread(target=run_script, args=(file_path, script_owner_id, user_folder, file_name, message)).start()
    except Exception as e:
        logger.error(f"❌ Error processing Python file {file_name} for {script_owner_id}: {e}", exc_info=True)
        bot.reply_to(message, f"\U0001F4A5 python file problem: {e}")

# --- Automatic Package Installation & Script Running ---
def run_script(script_path, script_owner_id, user_folder, file_name, message_obj_for_reply, attempt=1):
    """Run Python script. script_owner_id is used for the script_key. message_obj_for_reply is for sending feedback."""
    max_attempts = 2 
    if attempt > max_attempts:
        bot.reply_to(message_obj_for_reply, f"\U0001F4A5 couldn't start '{file_name}'. check logs.")
        return

    script_key = f"{script_owner_id}_{file_name}"
    logger.info(f"Attempt {attempt} to run Python script: {script_path} (Key: {script_key}) for user {script_owner_id}")

    try:
        if not os.path.exists(script_path):
             bot.reply_to(message_obj_for_reply, f"\u2754 '{file_name}' is gone \u2014 file not found!")
             logger.error(f"Script not found: {script_path} for user {script_owner_id}")
             if script_owner_id in user_files:
                 user_files[script_owner_id] = [f for f in user_files.get(script_owner_id, []) if f[0] != file_name]
             remove_user_file_db(script_owner_id, file_name)
             return

        if attempt == 1:
            check_command = [sys.executable, script_path]
            logger.info(f"Running Python pre-check: {' '.join(check_command)}")
            check_proc = None
            try:
                check_proc = subprocess.Popen(check_command, cwd=user_folder, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='ignore')
                stdout, stderr = check_proc.communicate(timeout=5)
                return_code = check_proc.returncode
                logger.info(f"Python Pre-check early. RC: {return_code}. Stderr: {stderr[:200]}...")
                if return_code != 0 and stderr:
                    match_py = re.search(r"ModuleNotFoundError: No module named '(.+?)'", stderr)
                    if match_py:
                        module_name = match_py.group(1).strip().strip("'\"")
                        logger.info(f"Detected missing Python module: {module_name}")
                        success, _ = attempt_install_pip(module_name, message_obj_for_reply)
                        if success:
                            logger.info(f"Install OK for {module_name}. Retrying run_script...")
                            bot.reply_to(message_obj_for_reply, f"\U0001F9E9 module added \u2014 starting again...")
                            time.sleep(2)
                            threading.Thread(target=run_script, args=(script_path, script_owner_id, user_folder, file_name, message_obj_for_reply, attempt + 1)).start()
                            return
                        else:
                            bot.reply_to(message_obj_for_reply, f"\U0001F4A5 couldn't add that module. stopped.")
                            return
                    else:
                         error_summary = stderr[:500]
                         bot.reply_to(message_obj_for_reply, f"⚠️ script error in '{file_name}':\n```\n{error_summary}\n```\nfix it & resend.", parse_mode='Markdown')
                         return
            except subprocess.TimeoutExpired:
                logger.info("Python Pre-check timed out (>5s), imports likely OK. Killing check process.")
                if check_proc and check_proc.poll() is None: check_proc.kill(); check_proc.communicate()
                logger.info("Python Check process killed. Proceeding to long run.")
            except FileNotFoundError:
                 logger.error(f"Python interpreter not found: {sys.executable}")
                 bot.reply_to(message_obj_for_reply, f"🐍 python missing on host ({sys.executable})!")
                 return
            except Exception as e:
                 logger.error(f"Error in Python pre-check for {script_key}: {e}", exc_info=True)
                 bot.reply_to(message_obj_for_reply, f"💥 pre-check crashed ({e})")
                 return
            finally:
                 if check_proc and check_proc.poll() is None:
                     logger.warning(f"Python Check process {check_proc.pid} still running. Killing.")
                     check_proc.kill(); check_proc.communicate()

        logger.info(f"Starting long-running Python process for {script_key}")
        log_file_path = os.path.join(user_folder, f"{os.path.splitext(file_name)[0]}.log")
        log_file = None; process = None
        try: log_file = open(log_file_path, 'w', encoding='utf-8', errors='ignore')
        except Exception as e:
             logger.error(f"Failed to open log file '{log_file_path}' for {script_key}: {e}", exc_info=True)
             bot.reply_to(message_obj_for_reply, f"\U0001F4DD couldn't write logs: {e}")
             return
        try:
            startupinfo = None; creationflags = 0
            if os.name == 'nt':
                 startupinfo = subprocess.STARTUPINFO(); startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                 startupinfo.wShowWindow = subprocess.SW_HIDE
            process = subprocess.Popen(
                [sys.executable, script_path], cwd=user_folder, stdout=log_file, stderr=log_file,
                stdin=subprocess.PIPE, startupinfo=startupinfo, creationflags=creationflags,
                encoding='utf-8', errors='ignore', env=_clean_env_for(user_folder),
                preexec_fn=_sandbox_preexec(user_folder) if os.name != 'nt' else None
            )
            logger.info(f"Started Python process {process.pid} for {script_key}")
            bot_scripts[script_key] = {
                'process': process, 'log_file': log_file, 'file_name': file_name,
                'chat_id': message_obj_for_reply.chat.id, # Chat ID for potential future direct replies from script, defaults to admin/triggering user
                'script_owner_id': script_owner_id, # Actual owner of the script
                'start_time': datetime.now(), 'user_folder': user_folder, 'type': 'py', 'script_key': script_key
            }
            bot.reply_to(message_obj_for_reply, f"\u2705 live! '{file_name}' \u00b7 pid {process.pid}")
        except FileNotFoundError:
             logger.error(f"Python interpreter {sys.executable} not found for long run {script_key}")
             bot.reply_to(message_obj_for_reply, f"🐍 python missing on host ({sys.executable})!")
             if log_file and not log_file.closed: log_file.close()
             if script_key in bot_scripts: del bot_scripts[script_key]
        except Exception as e:
            if log_file and not log_file.closed: log_file.close()
            error_msg = f"\U0001F4A5 start failed '{file_name}': {e}"
            logger.error(error_msg, exc_info=True)
            bot.reply_to(message_obj_for_reply, error_msg)
            if process and process.poll() is None:
                 logger.warning(f"Killing potentially started Python process {process.pid} for {script_key}")
                 kill_process_tree({'process': process, 'log_file': log_file, 'script_key': script_key})
            if script_key in bot_scripts: del bot_scripts[script_key]
    except Exception as e:
        error_msg = f"\U0001F4A5 unexpected error on '{file_name}': {e}"
        logger.error(error_msg, exc_info=True)
        bot.reply_to(message_obj_for_reply, error_msg)
        if script_key in bot_scripts:
             logger.warning(f"Cleaning up {script_key} due to error in run_script.")
             kill_process_tree(bot_scripts[script_key])
             del bot_scripts[script_key]

def run_js_script(script_path, script_owner_id, user_folder, file_name, message_obj_for_reply, attempt=1):
    """Run JS script. script_owner_id is used for the script_key. message_obj_for_reply is for sending feedback."""
    max_attempts = 2
    if attempt > max_attempts:
        bot.reply_to(message_obj_for_reply, f"\U0001F4A5 couldn't start '{file_name}'. check logs.")
        return

    script_key = f"{script_owner_id}_{file_name}"
    logger.info(f"Attempt {attempt} to run JS script: {script_path} (Key: {script_key}) for user {script_owner_id}")

    try:
        if not os.path.exists(script_path):
             bot.reply_to(message_obj_for_reply, f"\u2754 '{file_name}' is gone \u2014 file not found!")
             logger.error(f"JS Script not found: {script_path} for user {script_owner_id}")
             if script_owner_id in user_files:
                 user_files[script_owner_id] = [f for f in user_files.get(script_owner_id, []) if f[0] != file_name]
             remove_user_file_db(script_owner_id, file_name)
             return

        if attempt == 1:
            check_command = ['node', script_path]
            logger.info(f"Running JS pre-check: {' '.join(check_command)}")
            check_proc = None
            try:
                check_proc = subprocess.Popen(check_command, cwd=user_folder, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='ignore')
                stdout, stderr = check_proc.communicate(timeout=5)
                return_code = check_proc.returncode
                logger.info(f"JS Pre-check early. RC: {return_code}. Stderr: {stderr[:200]}...")
                if return_code != 0 and stderr:
                    match_js = re.search(r"Cannot find module '(.+?)'", stderr)
                    if match_js:
                        module_name = match_js.group(1).strip().strip("'\"")
                        if not module_name.startswith('.') and not module_name.startswith('/'):
                             logger.info(f"Detected missing Node module: {module_name}")
                             success, _ = attempt_install_npm(module_name, user_folder, message_obj_for_reply)
                             if success:
                                 logger.info(f"NPM Install OK for {module_name}. Retrying run_js_script...")
                                 bot.reply_to(message_obj_for_reply, f"\U0001F9E9 package added \u2014 starting again...")
                                 time.sleep(2)
                                 threading.Thread(target=run_js_script, args=(script_path, script_owner_id, user_folder, file_name, message_obj_for_reply, attempt + 1)).start()
                                 return
                             else:
                                 bot.reply_to(message_obj_for_reply, f"\U0001F4A5 couldn't add that package. stopped.")
                                 return
                        else: logger.info(f"Skipping npm install for relative/core: {module_name}")
                    error_summary = stderr[:500]
                    bot.reply_to(message_obj_for_reply, f"❌ Error in JS script pre-check for '{file_name}':\n```\n{error_summary}\n```\nfix it or ask staff to add it.", parse_mode='Markdown')
                    return
            except subprocess.TimeoutExpired:
                logger.info("JS Pre-check timed out (>5s), imports likely OK. Killing check process.")
                if check_proc and check_proc.poll() is None: check_proc.kill(); check_proc.communicate()
                logger.info("JS Check process killed. Proceeding to long run.")
            except FileNotFoundError:
                 error_msg = "\U0001F40B node missing on host!"
                 logger.error(error_msg)
                 bot.reply_to(message_obj_for_reply, error_msg)
                 return
            except Exception as e:
                 logger.error(f"Error in JS pre-check for {script_key}: {e}", exc_info=True)
                 bot.reply_to(message_obj_for_reply, f"\U0001F4A5 pre-check crashed ({e})")
                 return
            finally:
                 if check_proc and check_proc.poll() is None:
                     logger.warning(f"JS Check process {check_proc.pid} still running. Killing.")
                     check_proc.kill(); check_proc.communicate()

        logger.info(f"Starting long-running JS process for {script_key}")
        log_file_path = os.path.join(user_folder, f"{os.path.splitext(file_name)[0]}.log")
        log_file = None; process = None
        try: log_file = open(log_file_path, 'w', encoding='utf-8', errors='ignore')
        except Exception as e:
            logger.error(f"Failed to open log file '{log_file_path}' for JS script {script_key}: {e}", exc_info=True)
            bot.reply_to(message_obj_for_reply, f"\U0001F4DD couldn't write logs: {e}")
            return
        try:
            startupinfo = None; creationflags = 0
            if os.name == 'nt':
                 startupinfo = subprocess.STARTUPINFO(); startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                 startupinfo.wShowWindow = subprocess.SW_HIDE
            process = subprocess.Popen(
                ['node', script_path], cwd=user_folder, stdout=log_file, stderr=log_file,
                stdin=subprocess.PIPE, startupinfo=startupinfo, creationflags=creationflags,
                encoding='utf-8', errors='ignore', env=_clean_env_for(user_folder),
                preexec_fn=_sandbox_preexec(user_folder) if os.name != 'nt' else None
            )
            logger.info(f"Started JS process {process.pid} for {script_key}")
            bot_scripts[script_key] = {
                'process': process, 'log_file': log_file, 'file_name': file_name,
                'chat_id': message_obj_for_reply.chat.id, # Chat ID for potential future direct replies
                'script_owner_id': script_owner_id, # Actual owner of the script
                'start_time': datetime.now(), 'user_folder': user_folder, 'type': 'js', 'script_key': script_key
            }
            bot.reply_to(message_obj_for_reply, f"\u2705 live! '{file_name}' \u00b7 pid {process.pid}")
        except FileNotFoundError:
             error_msg = "❌ Error: 'node' not found for long run. Ensure Node.js is installed."
             logger.error(error_msg)
             if log_file and not log_file.closed: log_file.close()
             bot.reply_to(message_obj_for_reply, error_msg)
             if script_key in bot_scripts: del bot_scripts[script_key]
        except Exception as e:
            if log_file and not log_file.closed: log_file.close()
            error_msg = f"❌ Error starting JS script '{file_name}': {str(e)}"
            logger.error(error_msg, exc_info=True)
            bot.reply_to(message_obj_for_reply, error_msg)
            if process and process.poll() is None:
                 logger.warning(f"Killing potentially started JS process {process.pid} for {script_key}")
                 kill_process_tree({'process': process, 'log_file': log_file, 'script_key': script_key})
            if script_key in bot_scripts: del bot_scripts[script_key]
    except Exception as e:
        error_msg = f"❌ Unexpected error running JS script '{file_name}': {str(e)}"
        logger.error(error_msg, exc_info=True)
        bot.reply_to(message_obj_for_reply, error_msg)
        if script_key in bot_scripts:
             logger.warning(f"Cleaning up {script_key} due to error in run_js_script.")
             kill_process_tree(bot_scripts[script_key])
             del bot_scripts[script_key]

# --- Logic Functions (called by commands and text handlers) ---
def _logic_send_welcome(message):
    deploy_sessions.pop(message.from_user.id, None)
    web_sessions.pop(message.from_user.id, None)
    user_id = message.from_user.id
    chat_id = message.chat.id
    user_name = message.from_user.first_name

    logger.info(f"Welcome request from user_id: {user_id}")

    # Check if user is banned
    if is_user_banned(user_id):
        bot.send_message(chat_id, "\u26D4 your account is restricted from this bot.")
        return

    # Check mandatory subscription FIRST - before anything else
    is_subscribed, not_joined = check_mandatory_subscription(user_id)
    if not is_subscribed and user_id not in admin_ids:
        subscription_message, markup = create_subscription_check_message(not_joined)
        bot.send_message(chat_id, subscription_message, reply_markup=markup, parse_mode='Markdown')
        return

    if bot_locked and user_id not in admin_ids:
        bot.send_message(chat_id, "⚠️ Bot locked by admin. Try later.")
        return

    if user_id not in active_users:
        add_active_user(user_id)
        try:
            uname = message.from_user.username
            username_str = f"@{uname}" if uname else "no username"
            mention_link = f"[{user_name}](tg://user?id={user_id})"
            total_users = len(active_users)
            join_time = datetime.now().strftime("%d %b, %I:%M %p")
            owner_notification = (
                "╭━━「 🔔 ᴛʜᴇʀᴇ's ᴀ ɴᴇᴡ ᴜꜱᴇʀ 」━━╮\n"
                f"┃ 👤 {mention_link}\n"
                f"┃ 🆔 `{user_id}`\n"
                f"┃ 📛 {username_str}\n"
                f"┃ 🕐 {join_time}\n"
                f"┃ 👥 ᴛᴏᴛᴀʟ: {total_users}\n"
                "╰━━━━━━━━━━━━━━━━━━━━━╯")
            bot.send_message(OWNER_ID, owner_notification, parse_mode='Markdown')
        except Exception as e: 
            logger.error(f"⚠️ Failed to notify owner about new user {user_id}: {e}")

    file_limit = get_user_file_limit(user_id)
    current_files = get_user_file_count(user_id)
    limit_str = str(file_limit) if file_limit != float('inf') else "\u1D1C\u0274\u029F\u026A\u1D0D\u026A\u1D1B\u1D07\u1D05"
    expiry_info = ""
    
    if user_id == OWNER_ID: 
        status_word = "ᴅᴇᴠᴇʟᴏᴘᴇʀ"
    elif user_id in admin_ids: 
        status_word = "ᴀᴅᴍɪɴ"
    elif user_id in user_subscriptions:
        expiry_date = user_subscriptions[user_id].get('expiry')
        if expiry_date and expiry_date > datetime.now():
            status_word = "ᴘʀᴇᴍɪᴜᴍ"
            days_left = (expiry_date - datetime.now()).days
            expiry_info = f"\n┃ ⏳ {_t('expires in')} : {days_left} {_t('days')}"
        else: 
            status_word = "ꜰʀᴇᴇ (ᴇxᴘɪʀᴇᴅ)"
            remove_subscription_db(user_id)
    else: 
        status_word = "ꜰʀᴇᴇ ᴜꜱᴇʀ"

    welcome_msg_text = (
        "〽️ ᴡᴇʟᴄᴏᴍᴇ, 𝐙ꫀ᥊ -/ 🎭\n\n"
        "╭━━━「 👤 ᴀᴄᴄᴏᴜɴᴛ 」━━━╮\n"
        f"┃ 🆔 ᴜꜱᴇʀ ɪᴅ: {user_id}\n"
        f"┃ 👑 ꜱᴛᴀᴛᴜꜱ: {status_word}\n"
        f"┃ 📁 ꜰɪʟᴇꜱ: {current_files} / {limit_str}"
        f"{expiry_info}\n"
        "╰━━━━━━━━━━━━━━━━━━╯\n\n"
        "╭━━━「 🚀 ʜᴏꜱᴛɪɴɢ 」━━━╮\n"
        "┃ 🤖 ᴘʏᴛʜᴏɴ (.ᴘʏ)\n"
        "┃ 🟨 ᴊᴀᴠᴀꜱᴄʀɪᴘᴛ (.ᴊꜱ)\n"
        "┃ 📦 .ᴢɪᴘ ᴀʀᴄʜɪᴠᴇ ꜱᴜᴘᴘᴏʀᴛ\n"
        "┃ ⚙️ ᴍᴀɴᴜᴀʟ ᴍᴏᴅᴜʟᴇ ɪɴꜱᴛᴀʟʟ\n"
        "╰━━━━━━━━━━━━━━━━━━╯\n\n"
        "⚡ ᴅᴇᴘʟᴏʏ • ʀᴜɴ • ꜱᴛᴏᴘ • ʀᴇꜱᴛᴀʀᴛ\n"
        "📊 ᴍᴏɴɪᴛᴏʀ ʏᴏᴜʀ ᴘʀᴏᴊᴇᴄᴛꜱ ɪɴ ʀᴇᴀʟ-ᴛɪᴍᴇ\n\n"
        "👇 ᴜꜱᴇ ᴛʜᴇ ʙᴜᴛᴛᴏɴꜱ ʙᴇʟᴏᴡ\n"
        "ᴏʀ ᴛʏᴘᴇ ᴀ ᴄᴏᴍᴍᴀɴᴅ ᴛᴏ ɢᴇᴛ ꜱᴛᴀʀᴛᴇᴅ.")
    
    main_reply_markup = create_reply_keyboard_main_menu(user_id)
    try:
        bot.send_message(chat_id, welcome_msg_text, reply_markup=main_reply_markup, parse_mode='HTML')
    except Exception as e:
        logger.error(f"Error sending welcome to {user_id}: {e}", exc_info=True)

def _logic_updates_channel(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton('\U0001F4E1 '+_t('join channel'), url=f'https://t.me/{UPDATE_CHANNEL.replace("@", "")}'))
    bot.reply_to(message, "\U0001F4E1 stay updated \u2014 join the channel:", reply_markup=markup)

def _logic_upload_file(message):
    user_id = message.from_user.id
    
    # Check if user is banned
    if is_user_banned(user_id):
        bot.reply_to(message, "\u26D4 your account is restricted from this bot.")
        return
    
    # Check mandatory subscription first
    is_subscribed, not_joined = check_mandatory_subscription(user_id)
    if not is_subscribed and user_id not in admin_ids:
        subscription_message, markup = create_subscription_check_message(not_joined)
        bot.reply_to(message, subscription_message, reply_markup=markup, parse_mode='Markdown')
        return
        
    if bot_locked and user_id not in admin_ids:
        bot.reply_to(message, "\U0001F527 under maintenance — uploads paused.")
        return

    file_limit = get_user_file_limit(user_id)
    current_files = get_user_file_count(user_id)
    if current_files >= file_limit:
        limit_str = str(file_limit) if file_limit != float('inf') else "Unlimited"
        bot.reply_to(message, f"\U0001F9BA {_t('slots full')} [{current_files}/{limit_str}] \u2014 {_t('remove one or buy subscription')} \u2192 {_t('contact')} {YOUR_USERNAME}")
        return
    deploy_sessions[user_id] = True
    bot.reply_to(message, f"\U0001F3AF {_t('drop your script here')} \u2014 `.py` \u00B7 `.js` · `.zip`")

def _logic_check_files(message):
    user_id = message.from_user.id
    
    # Check if user is banned
    if is_user_banned(user_id):
        bot.reply_to(message, "\u26D4 your account is restricted from this bot.")
        return
    
    # Check mandatory subscription first
    is_subscribed, not_joined = check_mandatory_subscription(user_id)
    if not is_subscribed and user_id not in admin_ids:
        subscription_message, markup = create_subscription_check_message(not_joined)
        bot.reply_to(message, subscription_message, reply_markup=markup, parse_mode='Markdown')
        return
        
    user_files_list = user_files.get(user_id, [])
    if not user_files_list:
        bot.reply_to(message, f"\U0001F5C2\uFE0F {_t('no files yet')}\n{_t('send your first script to get started')} \U0001F680")
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    for file_name, file_type in sorted(user_files_list):
        is_running = is_bot_running(user_id, file_name) # Use user_id for checking status
        status_icon = "\U0001F7E9 running" if is_running else "\u2B1C stopped"
        btn_text = f"{file_name} ({file_type}) - {status_icon}"
        # Callback data includes user_id as script_owner_id
        markup.add(types.InlineKeyboardButton(btn_text, callback_data=f'file_{user_id}_{file_name}'))
    bot.reply_to(message, f"\U0001F5C2\uFE0F {_t('my files')}\n{_t('tap a file to manage')} \U0001F447", reply_markup=markup, parse_mode='Markdown')

def _logic_bot_speed(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    # Check if user is banned
    if is_user_banned(user_id):
        bot.reply_to(message, "\u26D4 your account is restricted from this bot.")
        return
    
    # Check mandatory subscription first
    is_subscribed, not_joined = check_mandatory_subscription(user_id)
    if not is_subscribed and user_id not in admin_ids:
        subscription_message, markup = create_subscription_check_message(not_joined)
        bot.reply_to(message, subscription_message, reply_markup=markup, parse_mode='Markdown')
        return
        
    start_time_ping = time.time()
    wait_msg = bot.reply_to(message, "\U0001F4E1 pinging the server...")
    try:
        bot.send_chat_action(chat_id, 'typing')
        response_time = round((time.time() - start_time_ping) * 1000, 2)
        status = "\u2705 online" if not bot_locked else "\U0001F527 maintenance"
        if user_id == OWNER_ID: user_level = "👑 "+sc_owner
        elif user_id in admin_ids: user_level = "🛡️ "+sc_admin
        elif user_id in user_subscriptions and user_subscriptions[user_id].get('expiry', datetime.min) > datetime.now(): user_level = "💎 "+sc_premium
        else: user_level = "💠 "+sc_free
        speed_msg = ("\U0001F300 "+_t("speed test")+f"\n\n\u23F1 {_t('ping')} ......... {response_time} ms\n"
                     +f"\U0001F6A6 {_t('bot')} ...... {status}\n"
                     +f"\U0001F465 {_t('your tier')} ... {user_level}")
        bot.edit_message_text(speed_msg, chat_id, wait_msg.message_id)
    except Exception as e:
        logger.error(f"Error during speed test (cmd): {e}", exc_info=True)
        bot.edit_message_text("\U0001F4A5 speed test failed.", chat_id, wait_msg.message_id)

def _logic_contact_owner(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton('\U0001F4AC '+_t('contact developer'), url=f'https://t.me/{YOUR_USERNAME.replace("@", "")}'))
    bot.reply_to(message, "\U0001F4AC need help? tap below \u2014 owner is one tap away.", reply_markup=markup)

def _logic_manual_install(message):
    """Handle manual installation request from user"""
    manual_install_module_init(message)

def _logic_help(message):
    help_text = (
        "❔ 𝐙ꫀ𝐗 ɢᴜɪᴅᴇ -/ 📖\n\n"
        "╭━━━「 🤖 ʙᴏᴛ ʜᴏꜱᴛɪɴɢ 」━━━╮\n"
        "┃ 1️⃣ ᴛᴀᴘ ⬆️ ᴅᴇᴘʟᴏʏ ʙᴏᴛ\n"
        "┃ 2️⃣ ꜱᴇɴᴅ .ᴘʏ · .ᴊꜱ · .ᴢɪᴘ (ᴍᴀx 20ᴍʙ)\n"
        "┃ 3️⃣ 🛡️ ᴀɪ ꜱᴄᴀɴ → ᴀᴅᴍɪɴ ✅\n"
        "┃ 4️⃣ ʙᴏᴛ ᴀᴜᴛᴏ-ꜱᴛᴀʀᴛ ⚡\n"
        "┃ ▶️ ꜱᴛᴀʀᴛ · ⏹ ꜱᴛᴏᴘ · 🔄 ʀᴇꜱᴛᴀʀᴛ · 📜 ʟᴏɢꜱ\n"
        "┃ 🗂️ ᴍᴀɴᴀɢᴇ → ᴍʏ ʙᴏᴛꜱ\n"
        "╰━━━━━━━━━━━━━━━━━━╯\n\n"
        "╭━━━「 🌐 ᴡᴇʙ ʜᴏꜱᴛɪɴɢ 」━━━╮\n"
        "┃ 1️⃣ ᴛᴀᴘ 🌐 ᴡᴇʙ ʜᴏꜱᴛ\n"
        "┃ 2️⃣ ꜱᴇɴᴅ .ʜᴛᴍʟ ᴏʀ .ᴢɪᴘ (ᴍᴀx 50ᴍʙ)\n"
        "┃ 3️⃣ ᴄʜᴏᴏꜱᴇ ᴀ ɴᴀᴍᴇ → ꜱᴄᴀɴ → ✅\n"
        "┃ 4️⃣ ɢᴇᴛ ʏᴏᴜʀ ʟɪᴠᴇ ʟɪɴᴋ 🎉\n"
        "┃ 🗂️ ᴍᴀɴᴀɢᴇ → ᴍʏ ᴡᴇʙ\n"
        "╰━━━━━━━━━━━━━━━━━━╯\n\n"
        "╭━━━「 💎 ꜱʟᴏᴛꜱ & ʟɪᴍɪᴛꜱ 」━━━╮\n"
        "┃ ꜰʀᴇᴇ : 2 ʙᴏᴛ · 1 ᴡᴇʙ\n"
        "┃ ᴘʀᴇᴍɪᴜᴍ : ♾️ ᴜɴʟɪᴍɪᴛᴇᴅ\n"
        "┃ 🧹 ꜰʀᴇᴇ ᴀ ꜱʟᴏᴛ = ᴅᴇʟᴇᴛᴇ ᴏʟᴅ ᴏɴᴇ\n"
        "╰━━━━━━━━━━━━━━━━━━╯\n\n"
        "🛡️ ᴇᴠᴇʀʏ ꜰɪʟᴇ ɢᴇᴛꜱ ꜱᴄᴀɴɴᴇᴅ\n"
        "⚠️ ᴍᴀʟᴡᴀʀᴇ = ɪɴꜱᴛᴀɴᴛ ʀᴇᴊᴇᴄᴛ\n\n"
        "📡 ɴᴇᴡꜱ : @MIKKU_ERA\n"
        "💬 ꜱᴜᴘᴘᴏʀᴛ : @duifioookn2"
    )
    bot.reply_to(message, help_text)

# --- Admin Logic Functions ---
def _logic_subscriptions_panel(message):
    if message.from_user.id not in admin_ids:
        bot.reply_to(message, "\U0001F512 staff only area.")
        return
    bot.reply_to(message, "\U0001F4B3 subscription zone\npick an action below \U0001F447", reply_markup=create_subscription_menu())

def _logic_statistics(message, uid=None):
    user_id = uid if uid is not None else getattr(message, 'from_user', None).id
    
    if is_user_banned(user_id):
        bot.reply_to(message, "\u26D4 your account is restricted from this bot.")
        return
    
    is_subscribed, not_joined = check_mandatory_subscription(user_id)
    if not is_subscribed and user_id not in admin_ids:
        subscription_message, markup = create_subscription_check_message(not_joined)
        bot.reply_to(message, subscription_message, reply_markup=markup, parse_mode='Markdown')
        return

    my_files = user_files.get(user_id, [])
    my_file_count = len(my_files)
    my_running = 0
    my_stopped = 0
    for script_key_iter, script_info_iter in list(bot_scripts.items()):
        s_owner_id, _ = script_key_iter.split('_', 1)
        if int(s_owner_id) == user_id:
            if is_bot_running(int(s_owner_id), script_info_iter['file_name']):
                my_running += 1
            else:
                my_stopped += 1

    my_web_count = sum(1 for v in web_manifest.values() if v.get('uid') == user_id)

    my_storage_bytes = 0
    upload_dir = os.path.join(BASE_DIR, 'upload_bots', str(user_id))
    if os.path.isdir(upload_dir):
        for root, _, files in os.walk(upload_dir):
            for fn in files:
                try: my_storage_bytes += os.path.getsize(os.path.join(root, fn))
                except Exception: pass
    if my_storage_bytes >= 1024 * 1024:
        storage_str = f"{my_storage_bytes / (1024*1024):.1f} MB"
    elif my_storage_bytes >= 1024:
        storage_str = f"{my_storage_bytes / 1024:.1f} KB"
    else:
        storage_str = f"{my_storage_bytes} B"

    tier = "👑 " + _t("developer") if user_id == OWNER_ID else \
           "🛡️ " + _t("admin") if user_id in admin_ids else \
           "💎 " + _t("premium") if user_id in user_subscriptions and user_subscriptions[user_id].get('expiry', datetime.min) > datetime.now() else \
           "💠 " + _t("free user")

    stats_msg = (f"📊 {_t('your stats')} -/ 🎭\n\n"
                 f"╭━━━「 👤 {_t('account')} 」━━━╮\n"
                 f"┃ 🆔 {_t('user id')} : {user_id}\n"
                 f"┃ 👑 {_t('tier')} : {tier}\n"
                 f"╰━━━━━━━━━━━━━━━━━━╯\n\n"
                 f"╭━━━「 📁 {_t('my files')} 」━━━╮\n"
                 f"┃ 📁 {_t('files')} : {my_file_count}\n"
                 f"┃ 🟩 {_t('running')} : {my_running}\n"
                 f"┃ ⬜ {_t('stopped')} : {my_stopped}\n"
                 f"╰━━━━━━━━━━━━━━━━━━╯\n\n"
                 f"╭━━━「 💾 {_t('storage')} 」━━━╮\n"
                 f"┃ 💾 {_t('disk used')} : {storage_str}\n"
                 f"╰━━━━━━━━━━━━━━━━━━╯\n\n"
                 f"╭━━━「 🌐 {_t('websites')} 」━━━╮\n"
                 f"┃ 🌐 {_t('sites')} : {my_web_count}\n"
                 f"╰━━━━━━━━━━━━━━━━━━╯")

    if user_id in admin_ids:
        total_users = len(active_users)
        total_files_records = sum(len(files) for files in user_files.values())
        today_str = datetime.now().strftime('%Y-%m-%d')
        new_today = active_today = premium_count = 0
        try:
            with DB_LOCK:
                conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
                c = conn.cursor()
                c.execute("SELECT COUNT(*) FROM active_users WHERE join_date LIKE ?", (today_str+'%',))
                new_today = c.fetchone()[0]
                c.execute("SELECT COUNT(*) FROM active_users WHERE last_seen LIKE ?", (today_str+'%',))
                active_today = c.fetchone()[0]
                conn.close()
        except Exception as e:
            logger.error(f"stats db err: {e}")
        for uid_s, sub in user_subscriptions.items():
            try:
                if sub.get('expiry') and sub['expiry'] > datetime.now(): premium_count += 1
            except Exception: pass
        running_bots_count = sum(1 for sk, si in bot_scripts.items()
                                if is_bot_running(int(sk.split('_')[0]), si['file_name']))
        web_total = len(web_manifest)
        lock_icon = "\U0001F512" if bot_locked else "\U0001F513"
        stats_msg += (f"\n\n{'━'*20}\n"
                      f"🛡️ {_t('admin panel')}\n"
                      f"{'━'*20}\n"
                      f"╭━━━「 👥 {_t('members')} 」━━━╮\n"
                      f"┃ 👥 {_t('total members')} : {total_users}\n"
                      f"┃ 🆕 {_t('new today')} : {new_today}\n"
                      f"┃ 🟢 {_t('online today')} : {active_today}\n"
                      f"┃ 💎 premium : {premium_count}\n"
                      f"┃ 🚫 {_t('banned')} : {len(banned_users)}\n"
                      f"╰━━━━━━━━━━━━━━━━━━╯\n"
                      f"╭━━━「 🚀 {_t('hosting')} 」━━━╮\n"
                      f"┃ 📁 {_t('files')} : {total_files_records}\n"
                      f"┃ 🟩 {_t('running bots')} : {running_bots_count}\n"
                      f"┃ 🌐 websites : {web_total}\n"
                      f"╰━━━━━━━━━━━━━━━━━━╯\n"
                      f"╭━━━「 ⚙️ {_t('system')} 」━━━╮\n"
                      f"┃ 🔒 {_t('lock')} : {lock_icon}\n"
                      f"┃ 📡 {_t('channels')} : {len(mandatory_channels)}\n"
                      f"┃ 📋 {_t('limits')} : {len(user_limits)}\n"
                      f"╰━━━━━━━━━━━━━━━━━━╯")

    bot.reply_to(message, stats_msg)

def _logic_broadcast_init(message):
    if message.from_user.id not in admin_ids:
        bot.reply_to(message, "\U0001F512 staff only area.")
        return
    msg = bot.reply_to(message, "\U0001F4EE type your announcement now.\n/cancel to quit.")
    bot.register_next_step_handler(msg, process_broadcast_message)

def _logic_toggle_lock_bot(message):
    if message.from_user.id not in admin_ids:
        bot.reply_to(message, "\U0001F512 staff only area.")
        return
    global bot_locked
    bot_locked = not bot_locked
    status = "locked" if bot_locked else "unlocked"
    logger.warning(f"Bot {status} by Admin {message.from_user.id} via command/button.")
    bot.reply_to(message, "\u26D4 gates closed." if bot_locked else "\U0001F513 gates open.")

def _logic_admin_panel(message):
    if message.from_user.id not in admin_ids:
        bot.reply_to(message, "\U0001F512 staff only area.")
        return
    bot.reply_to(message, "\U0001F451 admin zone\nmanage admins below \U0001F447", 
                 reply_markup=create_admin_panel())

def _logic_user_management(message):
    if message.from_user.id not in admin_ids:
        bot.reply_to(message, "\U0001F512 staff only area.")
        return
    bot.reply_to(message, "\U0001F465 user control\nban/unban \u00b7 limits \u00b7 info \u2014 pick one", 
                 reply_markup=create_user_management_menu())

def _logic_admin_settings(message):
    if message.from_user.id not in admin_ids:
        bot.reply_to(message, "\U0001F512 staff only area.")
        return
    bot.reply_to(message, "\U0001F527 system tools\ninfo \u00b7 cleanup \u00b7 logs", 
                 reply_markup=create_admin_settings_menu())

def _logic_run_all_scripts(message_or_call):
    if isinstance(message_or_call, telebot.types.Message):
        admin_user_id = message_or_call.from_user.id
        admin_chat_id = message_or_call.chat.id
        reply_func = lambda text, **kwargs: bot.reply_to(message_or_call, text, **kwargs)
        admin_message_obj_for_script_runner = message_or_call
    elif isinstance(message_or_call, telebot.types.CallbackQuery):
        admin_user_id = message_or_call.from_user.id
        admin_chat_id = message_or_call.message.chat.id
        bot.answer_callback_query(message_or_call.id)
        reply_func = lambda text, **kwargs: bot.send_message(admin_chat_id, text, **kwargs)
        admin_message_obj_for_script_runner = message_or_call.message 
    else:
        logger.error("Invalid argument for _logic_run_all_scripts")
        return

    if admin_user_id not in admin_ids:
        reply_func("\U0001F512 staff only area.")
        return

    reply_func("⏳ Starting process to run all user scripts. This may take a while...")
    logger.info(f"Admin {admin_user_id} initiated 'run all scripts' from chat {admin_chat_id}.")

    started_count = 0; attempted_users = 0; skipped_files = 0; error_files_details = []

    # Use a copy of user_files keys and values to avoid modification issues during iteration
    all_user_files_snapshot = dict(user_files)

    for target_user_id, files_for_user in all_user_files_snapshot.items():
        if not files_for_user: continue
        attempted_users += 1
        logger.info(f"Processing scripts for user {target_user_id}...")
        user_folder = get_user_folder(target_user_id)

        for file_name, file_type in files_for_user:
            # script_owner_id for key context is target_user_id
            if not is_bot_running(target_user_id, file_name):
                file_path = os.path.join(user_folder, file_name)
                if os.path.exists(file_path):
                    logger.info(f"Admin {admin_user_id} attempting to start '{file_name}' ({file_type}) for user {target_user_id}.")
                    try:
                        if file_type == 'py':
                            threading.Thread(target=run_script, args=(file_path, target_user_id, user_folder, file_name, admin_message_obj_for_script_runner)).start()
                            started_count += 1
                        elif file_type == 'js':
                            threading.Thread(target=run_js_script, args=(file_path, target_user_id, user_folder, file_name, admin_message_obj_for_script_runner)).start()
                            started_count += 1
                        else:
                            logger.warning(f"Unknown file type '{file_type}' for {file_name} (user {target_user_id}). Skipping.")
                            error_files_details.append(f"`{file_name}` (User {target_user_id}) - Unknown type")
                            skipped_files += 1
                        time.sleep(0.7) # Increased delay slightly
                    except Exception as e:
                        logger.error(f"Error queueing start for '{file_name}' (user {target_user_id}): {e}")
                        error_files_details.append(f"`{file_name}` (User {target_user_id}) - Start error")
                        skipped_files += 1
                else:
                    logger.warning(f"File '{file_name}' for user {target_user_id} not found at '{file_path}'. Skipping.")
                    error_files_details.append(f"`{file_name}` (User {target_user_id}) - File not found")
                    skipped_files += 1
            # else: logger.info(f"Script '{file_name}' for user {target_user_id} already running.")

    summary_msg = (f"✅ All Users' Scripts - Processing Complete:\n\n"
                   f"▶️ Attempted to start: {started_count} scripts.\n"
                   f"👥 Users processed: {attempted_users}.\n")
    if skipped_files > 0:
        summary_msg += f"⚠️ Skipped/Error files: {skipped_files}\n"
        if error_files_details:
             summary_msg += "Details (first 5):\n" + "\n".join([f"  - {err}" for err in error_files_details[:5]])
             if len(error_files_details) > 5: summary_msg += "\n  ... and more (check logs)."

    reply_func(summary_msg, parse_mode='Markdown')
    logger.info(f"Run all scripts finished. Admin: {admin_user_id}. Started: {started_count}. Skipped/Errors: {skipped_files}")

# --- Stop all running hosted scripts (OWNER/ADMIN) ---
def _logic_stop_all(message):
    if not _require_owner(message):
        bot.reply_to(message, "\U0001F512 staff only area.")
        return
    stopped = _stop_all_scripts()
    bot.reply_to(message, f"\u23F9\ufe0F stopped **{stopped}** hosted process(es).\n"
                          f"use ♻️ **run all** to bring them back when needed.",
                  parse_mode='Markdown')

# --- New Admin Functions for Channel Management ---
def _logic_manage_mandatory_channels(message):
    """Manage mandatory channels - for admin only"""
    if message.from_user.id not in admin_ids:
        bot.reply_to(message, "\U0001F512 staff only area.")
        return
    bot.reply_to(message, "\U0001F4E1 required channels\nadd or remove below", reply_markup=create_mandatory_channels_menu())

def _logic_admin_install(message):
    """Admin manual installation for users"""
    if message.from_user.id not in admin_ids:
        bot.reply_to(message, "\U0001F512 staff only area.")
        return
    msg = bot.reply_to(message, "\U0001F9E9 install for a user\nsend: `user_id module_name`\n/cancel to quit")
    bot.register_next_step_handler(msg, process_admin_install)

def process_admin_install(message):
    """Process admin installation request"""
    admin_id = message.from_user.id
    if admin_id not in admin_ids:
        bot.reply_to(message, "\U0001F512 not allowed.")
        return
        
    if message.text.lower() == '/cancel':
        bot.reply_to(message, "\u2716\uFE0F install cancelled.")
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "❔ send it like: `user_id module_name`")
            return
            
        user_id = int(parts[0])
        module_name = ' '.join(parts[1:])
        
        # Check if it's a Node.js module
        if module_name.lower().startswith('npm:'):
            module_name = module_name[4:].strip()
            user_folder = get_user_folder(user_id)
            success, log = attempt_install_npm(module_name, user_folder, message, manual_request=True)
        else:
            # Python module
            success, log = attempt_install_pip(module_name, message, manual_request=True)
        
        if success:
            logger.info(f"Admin {admin_id} installed module {module_name} for user {user_id}")
            # Notify user
            try:
                bot.send_message(user_id, f"📦 Admin installed module `{module_name}` for you.")
            except Exception as e:
                logger.error(f"Failed to notify user {user_id}: {e}")
    except ValueError:
        bot.reply_to(message, "❔ invalid id — numbers only.")
    except Exception as e:
        logger.error(f"Error in admin install: {e}", exc_info=True)
        bot.reply_to(message, f"💥 error: {e}")

# --- Owner / User Hosting Management Commands (integrated into existing architecture) ---
REBOOT_STATE_PATH = os.path.join(IROTECH_DIR, '.reboot_state.json')

def _is_owner(user_id):
    return user_id == OWNER_ID

def _require_owner(message):
    if not _is_owner(message.from_user.id):
        bot.reply_to(message, "\U0001F451 owner only area.")
        return False
    return True

def _count_running_processes():
    running = 0
    for key, info in list(bot_scripts.items()):
        try:
            proc = psutil.Process(info['process'].pid)
            if proc.is_running() and proc.status() != psutil.STATUS_ZOMBIE:
                running += 1
        except psutil.NoSuchProcess:
            pass
        except Exception as e:
            logger.error(f"Health: error checking {key}: {e}")
    return running

# --- /health (OWNER ONLY) ---
def _logic_owner_health(message):
    if not _require_owner(message): return

    parts = ["🤖 **Hosting Health Report**\n"]
    running = _count_running_processes()
    parts.append(f"• Hosted processes: {len(bot_scripts)} tracked / {running} alive")

    try:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        c.execute('SELECT 1')
        db_ok = c.fetchone()[0] == 1
        integrity = c.execute('PRAGMA integrity_check').fetchone()[0]
        conn.close()
        parts.append(f"• Database: {'✅ connected' if db_ok else '❌ failed'} · integrity: {integrity}")
    except Exception as e:
        parts.append(f"• Database: ❌ error ({e})")

    total_files = sum(len(files) for files in user_files.values())
    parts.append(f"• Projects registered: {total_files} across {len(user_files)} user(s)")

    for label, d in (("Uploads", UPLOAD_BOTS_DIR), ("Data", IROTECH_DIR)):
        parts.append(f"• {label} dir: {'✅ exists' if os.path.isdir(d) else '❌ missing'}")

    deps_ok = []
    for mod_name in ('telebot', 'psutil', 'flask', 'requests'):
        try:
            __import__(mod_name); deps_ok.append(f"{mod_name} ✅")
        except Exception:
            deps_ok.append(f"{mod_name} ❌")
    parts.append("• Dependencies: " + ", ".join(deps_ok))

    env_flags = []
    if TOKEN: env_flags.append("token ✅")
    else: env_flags.append("token ❌")
    if OWNER_ID: env_flags.append("owner ✅")
    else: env_flags.append("owner ❌")
    parts.append("• Config: " + " · ".join(env_flags))
    parts.append(f"• System uptime: {time.strftime('%H:%M:%S', time.gmtime(time.time() - psutil.boot_time()))}")

    bot.reply_to(message, "\n".join(parts), parse_mode='Markdown')

# --- /status (OWNER ONLY) global hosting status ---
def _logic_owner_status(message):
    if not _require_owner(message): return

    running, stopped, failed = [], [], []
    for owner_id, files in sorted(user_files.items()):
        for fname, ftype in sorted(files):
            if is_bot_running(owner_id, fname):
                running.append((owner_id, fname, ftype))
                continue
            log_path = os.path.join(get_user_folder(owner_id), f"{os.path.splitext(fname)[0]}.log")
            crashed = False
            try:
                if os.path.exists(log_path) and os.path.getsize(log_path) > 0:
                    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                        tail = f.read()[-2000:]
                    if 'Traceback' in tail or '\nError' in tail:
                        crashed = True
            except Exception as e:
                logger.error(f"Status: log read error for {owner_id}/{fname}: {e}")
            if crashed: failed.append((owner_id, fname, ftype))
            else: stopped.append((owner_id, fname, ftype))

    lines = ["📊 **Global Hosting Status**\n"]
    lines.append(f"🟢 Running: {len(running)} | 🔴 Stopped: {len(stopped)} | 💥 Failed/Crashed: {len(failed)}")
    lines.append(f"👥 Users with projects: {len(user_files)}")
    lines.append("")

    def fmt(items, limit=15):
        out = []
        for o, f, t in items[:limit]:
            out.append(f"• `{o}` / `{f}` ({t})")
        if len(items) > limit:
            out.append(f"  … and {len(items) - limit} more")
        return "\n".join(out)

    if running:
        lines.append("**Running:**\n" + fmt(running))
    if failed:
        lines.append("**Failed/Crashed:**\n" + fmt(failed))
    if stopped:
        lines.append("**Stopped:**\n" + fmt(stopped))

    msg = "\n".join(lines)
    if len(msg) > 4000:
        msg = msg[:4000] + "\n…(truncated)"
    bot.reply_to(message, msg, parse_mode='Markdown')

# --- /cleanup (OWNER ONLY) ---
def _perform_hosting_cleanup():
    cleaned_dirs = 0
    cleaned_files = 0
    cleaned_temp = 0
    cleaned_web = 0
    killed_zombies = 0

    running_basenames = set()
    for key, info in list(bot_scripts.items()):
        try:
            proc = psutil.Process(info['process'].pid)
            if proc.is_running() and proc.status() != psutil.STATUS_ZOMBIE:
                running_basenames.add(os.path.splitext(info.get('file_name', ''))[0])
        except Exception:
            pass

    # zombie / dead scripts still registered in bot_scripts -> drop them
    for key, info in list(bot_scripts.items()):
        try:
            proc = psutil.Process(info['process'].pid)
            if not proc.is_running() or proc.status() == psutil.STATUS_ZOMBIE:
                bot_scripts.pop(key, None)
                try: proc.kill()
                except Exception: pass
                killed_zombies += 1
        except Exception:
            bot_scripts.pop(key, None)
            killed_zombies += 1

    for user_dir in os.listdir(UPLOAD_BOTS_DIR):
        user_path = os.path.join(UPLOAD_BOTS_DIR, user_dir)
        if not os.path.isdir(user_path):
            continue
        try:
            if not os.listdir(user_path):
                os.rmdir(user_path)
                cleaned_dirs += 1
            else:
                for file_name in os.listdir(user_path):
                    if not file_name.endswith('.log'):
                        continue
                    base = os.path.splitext(file_name)[0]
                    if base in running_basenames:
                        continue
                    file_path = os.path.join(user_path, file_name)
                    try:
                        if time.time() - os.path.getmtime(file_path) > 7 * 24 * 3600:
                            os.remove(file_path)
                            cleaned_files += 1
                    except Exception as e:
                        logger.error(f"Error cleaning log file {file_path}: {e}")
        except Exception as e:
            logger.error(f"Error cleaning user dir {user_path}: {e}")

    # web_files/ dirs with no matching manifest entry -> stale
    try:
        for name in list(os.listdir(WEB_FILES_DIR)):
            folder = os.path.join(WEB_FILES_DIR, name)
            if not os.path.isdir(folder):
                continue
            if name not in web_manifest:
                shutil.rmtree(folder, ignore_errors=True)
                cleaned_web += 1
    except Exception as e:
        logger.error(f"Error cleaning web files: {e}")

    try:
        temp_root = tempfile.gettempdir()
        for name in os.listdir(temp_root):
            if name.startswith('user_') and '_zip_' in name:
                p = os.path.join(temp_root, name)
                try:
                    if os.path.isdir(p) and (time.time() - os.path.getmtime(p)) > 24 * 3600:
                        shutil.rmtree(p, ignore_errors=True)
                        cleaned_temp += 1
                except Exception as e:
                    logger.error(f"Error cleaning temp dir {p}: {e}")
    except Exception as e:
        logger.error(f"Error scanning temp dir: {e}")

    return cleaned_dirs, cleaned_files, cleaned_temp, cleaned_web, killed_zombies

def _logic_owner_cleanup(message):
    if not _require_owner(message): return
    try:
        cleaned_dirs, cleaned_files, cleaned_temp, cleaned_web, killed_zombies = _perform_hosting_cleanup()
        bot.reply_to(message,
                     f"🧹 **Cleanup Complete:**\n"
                     f"• Removed empty directories: {cleaned_dirs}\n"
                     f"• Cleared old log files: {cleaned_files}\n"
                     f"• Removed stale temp dirs: {cleaned_temp}\n"
                     f"• Removed stale web dirs: {cleaned_web}\n"
                     f"• Killed dead/zombie sessions: {killed_zombies}",
                     parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error in /cleanup: {e}", exc_info=True)
        bot.reply_to(message, f"🧹 cleanup problem: {e}")

# --- /reboot (OWNER ONLY) ---
class _RebootChatId:
    def __init__(self, chat_id): self.id = chat_id

class _RebootUserId:
    def __init__(self, user_id): self.id = user_id

class _RebootReplyMsg:
    """Minimal message stand-in so hosted scripts can be re-run after reboot."""
    def __init__(self, chat_id):
        self.chat = _RebootChatId(chat_id)
        self.message_id = None
        self.from_user = _RebootUserId(OWNER_ID)
    def reply_to(self, text, **kwargs):
        try:
            return bot.send_message(self.chat.id, text, **kwargs)
        except Exception as e:
            logger.error(f"Reboot restore reply error: {e}")
            return None

def _snapshot_running_scripts():
    snapshot = []
    for key, info in list(bot_scripts.items()):
        try:
            proc = psutil.Process(info['process'].pid)
            if proc.is_running() and proc.status() != psutil.STATUS_ZOMBIE:
                snapshot.append({
                    'script_owner_id': info.get('script_owner_id'),
                    'file_name': info.get('file_name'),
                    'user_folder': info.get('user_folder'),
                    'type': info.get('type'),
                    'chat_id': info.get('chat_id'),
                })
        except Exception as e:
            logger.error(f"Reboot snapshot error for {key}: {e}")
    try:
        with open(REBOOT_STATE_PATH, 'w', encoding='utf-8') as f:
            json.dump(snapshot, f)
        logger.info(f"Reboot snapshot saved: {len(snapshot)} scripts")
    except Exception as e:
        logger.error(f"Failed to save reboot snapshot: {e}")

def _stop_all_scripts():
    stopped = 0
    for key in list(bot_scripts.keys()):
        info = bot_scripts.get(key)
        if info:
            try:
                kill_process_tree(info)
                stopped += 1
            except Exception as e:
                logger.error(f"Reboot: error stopping {key}: {e}")
            bot_scripts.pop(key, None)
    return stopped

def _restore_after_reboot():
    """Restore previously running hosted scripts after an owner /reboot."""
    if not os.path.exists(REBOOT_STATE_PATH):
        return
    try:
        with open(REBOOT_STATE_PATH, 'r', encoding='utf-8') as f:
            snapshot = json.load(f)
        os.remove(REBOOT_STATE_PATH)
    except Exception as e:
        logger.error(f"Reboot state read error: {e}")
        return
    logger.info(f"Restoring {len(snapshot)} hosted scripts after reboot...")
    for item in snapshot:
        try:
            owner_id = int(item.get('script_owner_id', 0))
            file_name = item.get('file_name')
            user_folder = item.get('user_folder') or get_user_folder(owner_id)
            file_type = item.get('type', 'py')
            file_path = os.path.join(user_folder, file_name) if file_name else None
            if not file_name or not os.path.exists(file_path):
                logger.warning(f"Reboot restore: skipping missing '{file_name}'")
                continue
            if is_bot_running(owner_id, file_name):
                continue
            reply_obj = _RebootReplyMsg(item.get('chat_id') or OWNER_ID)
            if file_type == 'js':
                threading.Thread(target=run_js_script, args=(file_path, owner_id, user_folder, file_name, reply_obj)).start()
            else:
                threading.Thread(target=run_script, args=(file_path, owner_id, user_folder, file_name, reply_obj)).start()
            time.sleep(0.5)
        except Exception as e:
            logger.error(f"Reboot restore error for {item}: {e}")

def _logic_owner_reboot(message):
    if not _require_owner(message): return
    try:
        _snapshot_running_scripts()
        stopped = _stop_all_scripts()
        bot.send_message(message.chat.id,
                         f"🔄 Rebooting hosting environment...\n"
                         f"• Stopped {stopped} hosted process(es).\n"
                         f"• Project files and user data are preserved.")
        time.sleep(1.5)
        logger.warning("Reboot initiated by owner. Re-executing bot process.")
        os.execv(sys.executable, [sys.executable, os.path.abspath(__file__)])
    except Exception as e:
        logger.error(f"Reboot failed: {e}", exc_info=True)
        try:
            bot.send_message(message.chat.id, f"❌ Reboot failed: {e}")
        except Exception:
            pass

# --- /restart (ALL USERS, strictly user-scoped) ---
def _logic_user_restart(message):
    user_id = message.from_user.id

    if is_user_banned(user_id):
        bot.reply_to(message, "\u26D4 your account is restricted from this bot.")
        return

    if bot_locked and user_id not in admin_ids:
        bot.reply_to(message, "⚠️ Bot locked by admin. Try later.")
        return

    is_subscribed, not_joined = check_mandatory_subscription(user_id)
    if not is_subscribed and user_id not in admin_ids:
        subscription_message, markup = create_subscription_check_message(not_joined)
        bot.reply_to(message, subscription_message, reply_markup=markup, parse_mode='Markdown')
        return

    user_projects = list(user_files.get(user_id, []))
    if not user_projects:
        bot.reply_to(message, "📭 You have no hosted projects to restart.")
        return

    bot.reply_to(message, f"🔄 Restarting your projects ({len(user_projects)})...")

    for file_name, file_type in user_projects:
        script_key = f"{user_id}_{file_name}"
        user_folder = get_user_folder(user_id)
        file_path = os.path.join(user_folder, file_name)

        if not os.path.exists(file_path):
            logger.warning(f"/restart: file missing for {user_id}: {file_name}")
            remove_user_file_db(user_id, file_name)
            continue

        if is_bot_running(user_id, file_name):
            info = bot_scripts.get(script_key)
            if info:
                try:
                    kill_process_tree(info)
                except Exception as e:
                    logger.error(f"/restart: error stopping {script_key}: {e}")
                bot_scripts.pop(script_key, None)
            time.sleep(1.0)

        if file_type == 'py':
            threading.Thread(target=run_script, args=(file_path, user_id, user_folder, file_name, message)).start()
        elif file_type == 'js':
            threading.Thread(target=run_js_script, args=(file_path, user_id, user_folder, file_name, message)).start()
        else:
            logger.warning(f"/restart: unknown type for {user_id}: {file_name}")
        time.sleep(0.5)

    bot.send_message(message.chat.id,
                     f"✅ `/restart` finished. {len(user_projects)} project(s) processed.",
                     parse_mode='Markdown')

# --- /storage (OWNER ONLY) ---
def _tidb_storage_lines():
    """Query TiDB table sizes (rows + stored bytes) via the shim."""
    rows_out = []
    try:
        sys.path.insert(0, BASE_DIR)
        import tidb_shim
        c = tidb_shim.connect()
        cur = c.cursor()
        cur.execute("SELECT COUNT(*), COALESCE(SUM(LENGTH(content)),0) FROM h2_files")
        h2 = cur.fetchone()
        cur.execute("SELECT COUNT(*), COALESCE(SUM(LENGTH(content)),0) FROM web_files_data")
        web = cur.fetchone()
        cur.execute("SELECT COUNT(*) FROM active_users")
        au = cur.fetchone()
        cur.execute("SELECT COUNT(*) FROM user_files")
        uf = cur.fetchone()
        c.close()
        rows_out.append(f"• h2_files (bot files): {h2[0]} rows · {h2[1] / 1024**2:.2f} MB stored")
        rows_out.append(f"• web_files_data (sites): {web[0]} rows · {web[1] / 1024**2:.2f} MB stored")
        rows_out.append(f"• active_users: {au[0]} · user_files: {uf[0]} rows")
    except Exception as e:
        rows_out.append(f"• TiDB query: ❌ error ({e})")
    return rows_out


def _logic_owner_storage(message):
    if not _require_owner(message): return

    parts = ["💾 **Storage Report**\n"]
    try:
        du = psutil.disk_usage(BASE_DIR)
        parts.append("**Host disk:**")
        parts.append(f"• Total: {du.total / 1024**3:.2f} GB · Free: {du.free / 1024**3:.2f} GB")
        parts.append(f"• Used: {du.used / 1024**3:.2f} GB ({du.percent}%)")
    except Exception as e:
        parts.append(f"• Host disk: ❌ error ({e})")

    try:
        parts.append("")
        parts.append("**Health:**")
        cpu = psutil.cpu_percent(interval=0.5)
        parts.append(f"• CPU: {cpu:.0f}% · Load: {psutil.getloadavg()[0]:.2f}")
        vm = psutil.virtual_memory()
        parts.append(f"• RAM: {vm.used / 1024**3:.2f} / {vm.total / 1024**3:.2f} GB ({vm.percent}%)")
        boot = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(psutil.boot_time()))
        parts.append(f"• System up since: {boot}")
    except Exception as e:
        parts.append(f"• Health: ❌ error ({e})")

    parts.append("")
    parts.append("**Project storage (upload_bots):**")
    total_proj = 0
    user_rows = []
    try:
        for user_id_str in os.listdir(UPLOAD_BOTS_DIR):
            user_path = os.path.join(UPLOAD_BOTS_DIR, user_id_str)
            if not os.path.isdir(user_path):
                continue
            size = sum(os.path.getsize(os.path.join(dp, f))
                       for dp, _, fns in os.walk(user_path) for f in fns)
            total_proj += size
            user_rows.append((user_id_str, size))
        user_rows.sort(key=lambda x: x[1], reverse=True)
        parts.append(f"• Total on disk: {total_proj / 1024**2:.2f} MB")
        for uid, sz in user_rows[:10]:
            parts.append(f"  • `{uid}`: {sz / 1024**2:.2f} MB")
        if len(user_rows) > 10:
            parts.append(f"  … and {len(user_rows) - 10} more user(s)")
    except Exception as e:
        parts.append(f"• Project scan: ❌ error ({e})")

    parts.append("**TiDB storage (cloud):**")
    parts.extend(_tidb_storage_lines())

    bot.reply_to(message, "\n".join(parts), parse_mode='Markdown')

# --- /version (OWNER ONLY) ---
def _logic_owner_version(message):
    if not _require_owner(message): return
    parts = ["ℹ️ **Hosting Bot Version**"]
    parts.append(f"• Bot version: `{BOT_VERSION}`")
    parts.append(f"• Python: `{sys.version.split()[0]}`")
    try:
        parts.append(f"• pyTelegramBotAPI: `{telebot.__version__}`")
    except Exception:
        pass
    parts.append(f"• Bot uptime: {time.strftime('%H:%M:%S', time.gmtime(time.time() - BOT_START_TIME))}")
    parts.append(f"• Base dir: `{BASE_DIR}`")
    bot.reply_to(message, "\n".join(parts), parse_mode='Markdown')


# ================= WEB HOSTING SYSTEM (Titan-style path links + ZEX approval) =================
BASE_DIR_W = os.path.dirname(os.path.abspath(__file__))
WEB_FILES_DIR = os.path.join(BASE_DIR_W, 'web_files')
WEB_MANIFEST_PATH = os.path.join(BASE_DIR_W, 'web_sites.json')
os.makedirs(WEB_FILES_DIR, exist_ok=True)

def _load_web_manifest():
    try:
        import web_sync
        return web_sync.restore_manifest()
    except Exception:
        pass
    try:
        with open(WEB_MANIFEST_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}
def _save_web_manifest():
    try:
        with open(WEB_MANIFEST_PATH, 'w', encoding='utf-8') as f:
            json.dump(web_manifest, f)
    except Exception as e:
        logger.error(f"manifest save err: {e}")
    try:
        import web_sync
        web_sync.save_manifest(web_manifest)
    except Exception as e:
        logger.error(f"manifest TiDB save err: {e}")

web_manifest = _load_web_manifest()   # {name: {'uid':..,'created':'YYYY-MM-DD','ftype':'html'|'zip'}}
_main_site_id = [None]

def _netlify_ready():
    return bool(RENDER_WEB_URL) or bool(NETLIFY_TOKEN)

def _nh():
    return {'Authorization': 'Bearer '+NETLIFY_TOKEN}

def _sanitize_webname(name):
    n = re.sub(r'[^a-z0-9-]', '', str(name).lower().replace(' ', '-'))
    n = re.sub(r'-+', '-', n).strip('-')
    return (n or 'site')[:20]

def _web_prefix(uid):
    return 'u'+str(uid)+'-'   # kept for compat

def _web_url(name):
    if RENDER_WEB_URL:
        return f"{RENDER_WEB_URL}/web/{name}/"
    return f"https://{NETLIFY_MAIN_SITE}.netlify.app/{name}/"

def _web_count(uid):
    return sum(1 for d in web_manifest.values() if d.get('uid') == uid)

def _web_limit(uid):
    if uid == OWNER_ID or uid in admin_ids: return float('inf')
    sub = user_subscriptions.get(uid)
    if sub and sub.get('expiry') and sub['expiry'] > datetime.now(): return float('inf')
    return WEB_FREE_LIMIT

def _ensure_main_site():
    """returns main netlify site id (cached)"""
    if _main_site_id[0]: return _main_site_id[0]
    r = requests.get(NETLIFY_API+'/sites', headers=_nh(), params={'filter':'all','per_page':100}, timeout=20)
    if r.status_code == 200:
        for x in r.json():
            if x.get('name') == NETLIFY_MAIN_SITE:
                _main_site_id[0] = x['id']; return _main_site_id[0]
    c = requests.post(NETLIFY_API+'/sites', headers=_nh(), json={'name': NETLIFY_MAIN_SITE}, timeout=25)
    if c.status_code not in (200, 201): raise RuntimeError('main site create failed: '+c.text[:120])
    _main_site_id[0] = c.json()['id']; return _main_site_id[0]

def _root_landing():
    rows = ''.join(f'<li><a href="{n}/">{n}</a></li>' for n in sorted(web_manifest))
    return ('<!DOCTYPE html><html><head><meta charset="utf-8"><title>ZEX WEB HOST</title>'
            '<style>body{background:#0b0f1a;color:#7df9ff;font-family:monospace;text-align:center;padding-top:60px}'
            'a{color:#ffd166}ul{list-style:none;padding:0}</style></head>'
            '<body><h1>🌐 ZEX WEB HOST</h1><p>live sites:</p><ul>'+rows+'</ul>'
            '<p style="color:#666">powered by zex hosting bot</p></body></html>')

def _deploy_bundle():
    """deploys ALL sites (web_files/<name>/) to the one main netlify site.
    On Render the Flask app serves web_files/ directly, so just verify files exist."""
    if RENDER_WEB_URL:
        if not os.listdir(WEB_FILES_DIR):
            raise RuntimeError('no web files yet')
        return True
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('index.html', _root_landing())
        for name in os.listdir(WEB_FILES_DIR):
            folder = os.path.join(WEB_FILES_DIR, name)
            if not os.path.isdir(folder): continue
            for root, _, files in os.walk(folder):
                for fn in files:
                    fp = os.path.join(root, fn)
                    arc = name+'/'+os.path.relpath(fp, folder).replace(os.sep, '/')
                    z.write(fp, arc)
    sid = _ensure_main_site()
    d = requests.post(NETLIFY_API+f'/sites/{sid}/deploys',
                      headers={**_nh(), 'Content-Type': 'application/zip'},
                      data=buf.getvalue(), timeout=90)
    if d.status_code not in (200, 201):
        raise RuntimeError('deploy failed: '+d.text[:150])
    dep = d.json(); did = dep['id']
    for _ in range(15):
        time.sleep(3)
        c = requests.get(NETLIFY_API+f'/sites/{sid}/deploys/{did}', headers=_nh(), timeout=15)
        st = c.json().get('state', '') if c.status_code == 200 else ''
        if st == 'ready': return True
        if st in ('error', 'expired'): raise RuntimeError('build error')
    return True   # slow build - treat as accepted

def _web_extra_scan(content_bytes, ftype):
    out = []
    try:
        txt = content_bytes.decode('utf-8', 'ignore').lower()
        if '<form' in txt and 'password' in txt:
            out.append("\U0001F3A3 "+_t("can collect passwords - fake login page possible"))
        if 'http-equiv="refresh"' in txt or "http-equiv='refresh'" in txt:
            out.append("🔀 "+_t("auto-redirects visitor to another page"))
        if re.search(r'<script[^>]+src=[\"\']http://', txt):
            out.append("\U0001F539 loads remote script over insecure http")
        if 'document.cookie' in txt and ('fetch(' in txt or 'new Image' in txt or '.src =' in txt):
            out.append("\U0001F36A can steal visitor cookies to another server")
        if '<iframe' in txt and ('width="0"' in txt or 'display:none' in txt.replace(' ','')):
            out.append("\U0001F40D hidden invisible iframe - clickjacking trick")
        if re.search(r'(eval|atob)\s*\(\s*(atob|unescape|decodeURI)', txt):
            out.append("\U0001F47E encoded javascript - hiding what it does")
        if 'keylog' in txt or "addEventListener('keydown'" in txt or 'addEventListener("keydown"' in txt:
            out.append("\U0001F5B3 records visitor keystrokes")
        if 'location.replace' in txt or 'window.location =' in txt:
            out.append("🔀 "+_t("javascript auto-redirect found"))
        if any(k in txt for k in ('coinhive', 'cryptonight', 'minero')):
            out.append("👾 "+_t("hidden crypto miner in page"))
        if ftype == 'html' and len(txt) < 40 and '<' not in txt:
            out.append("🚩 "+_t("not a valid webpage content"))
    except Exception:
        pass
    return out

def _logic_web_host(message):
    uid = message.from_user.id
    if is_user_banned(uid):
        bot.reply_to(message, "⛔ "+_t("your account is restricted from this bot"))
        return
    is_subscribed, not_joined = check_mandatory_subscription(uid)
    if not is_subscribed and uid not in admin_ids:
        sub_msg, sub_mk = create_subscription_check_message(not_joined)
        bot.reply_to(message, sub_msg, reply_markup=sub_mk)
        return
    if not _netlify_ready():
        bot.reply_to(message, "🔧 "+_t("web hosting setup pending - contact developer"))
        return
    cnt = _web_count(uid); lim = _web_limit(uid)
    if cnt >= lim:
        lim_s = 'unlimited' if lim == float('inf') else str(lim)
        bot.reply_to(message, f"🚧 "+_t("web slot full")+" ["+str(cnt)+"/"+lim_s+"] \u2014 "+_t("delete a site or buy subscription")+" \u2192 "+_t("contact")+" "+YOUR_USERNAME)
        return
    web_sessions[uid] = {'stage': 'file'}
    bot.reply_to(message,
        "\U0001F4E4 "+_t("send your website file now")+":\n"
        "• \u026A\u0274\u1D0Ex.\u029C\u1D1B\u1D0D\uA731 (single page)\n"
        "• .\u1D22\u026AP ("+_t("full site")+")\n\n"
        "\U0001F4CC "+_t("main page must be named")+" index.html")

@bot.message_handler(content_types=['document'])
def _web_doc_catcher(message):
    uid = message.from_user.id
    sess = web_sessions.get(uid)
    _touch_user(uid)
    if not sess or sess.get('stage') != 'file':
        handle_file_upload_doc(message); return
    if is_user_banned(uid):
        web_sessions.pop(uid, None)
        bot.reply_to(message, "⛔ "+_t("your account is restricted from this bot"))
        return
    if not _rate_ok(uid):
        bot.reply_to(message, "\U0001F4C9 "+_t("too many uploads - slow down"))
        return
    doc = message.document
    fname = doc.file_name or 'site.html'
    ext = os.path.splitext(fname)[1].lower()
    if ext not in ('.html', '.htm', '.zip'):
        web_sessions.pop(uid, None)
        handle_file_upload_doc(message); return
    if (doc.file_size or 0) > 50*1024*1024:
        bot.reply_to(message, "🐋 "+_t("too big - max 50 mb")); return
    try:
        info = bot.get_file(doc.file_id)
        content = bot.download_file(info.file_path)
    except Exception as e:
        bot.reply_to(message, f"💥 {e}"); return
    ftype = 'zip' if ext == '.zip' else 'html'
    web_sessions[uid] = {'stage': 'name', 'content': content, 'fname': fname, 'ftype': ftype}
    bot.reply_to(message,
        "✍️ "+_t("now send a name for your site")+"\n"
        "("+_t("letters & numbers only")+")\n\n"
        "⏳ "+_t("link will be shown after admin approval"))

@bot.message_handler(func=lambda m: m.from_user.id in web_sessions and web_sessions[m.from_user.id].get('stage') == 'name')
def _web_name_catcher(message):
    uid = message.from_user.id
    _touch_user(uid)
    if (message.text or "").startswith("/"):
        web_sessions.pop(uid, None)
        return
    sess = web_sessions.get(uid)
    if not sess: return
    if is_user_banned(uid):
        web_sessions.pop(uid, None)
        bot.reply_to(message, "⛔ "+_t("your account is restricted from this bot"))
        return
    safe = _sanitize_webname(message.text)
    if safe in web_manifest:
        bot.reply_to(message, "⛔ "+_t("name already taken")+" — "+_t("try another")); return
    web_sessions.pop(uid, None)
    full = safe
    content, ftype = sess['content'], sess['ftype']
    tmpdir = tempfile.mkdtemp(prefix='webscan_')
    try:
        tmppath = os.path.join(tmpdir, ('site.zip' if ftype == 'zip' else 'index.html'))
        with open(tmppath, 'wb') as f: f.write(content)
        ai_report = build_ai_report(tmppath, ftype, uid, message.from_user.first_name)
        extra = _web_extra_scan(content, ftype)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
    _web_counter[0] += 1
    key = f"{uid}_{_web_counter[0]}"
    web_pending[key] = {'uid': uid, 'name': full, 'content': content, 'fname': sess['fname'], 'ftype': ftype}
    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton("\u2705 "+_t("approve"), callback_data=f"wapprove_{key}"),
        types.InlineKeyboardButton("\u2716\uFE0F "+_t("reject"), callback_data=f"wreject_{key}"))
    alert = "\U0001F310 WE\u1D1B H\u1D0F\u02E2\u1D1BING APPROVAL\n\n" + ai_report + "\n\n📄 "+_t("site")+": "+sess['fname']+" · 🏷 "+full
    if extra: alert += "\n"+"\n".join(extra)
    alert += "\n\n" + _t("approval required")
    for aid in admin_ids:
        head = ("\U0001F310 WE\u1D1B H\u1D0F\u02E2\u1D1BING APPROVAL\n\n"
                "\U0001F4C1 "+_t("site")+": "+sess['fname']+" · 🏷 "+full+"\n"
                "\U0001F464 "+_t("user id")+": "+str(uid))
        try:
            bot.send_message(aid, alert[:2048], reply_markup=markup)
        except Exception as e: logger.error(f"web report -> admin {aid}: {e}")
        try:
            bot.send_document(aid, content, caption=head[:900],
                              visible_file_name=sess['fname'])
        except Exception as e: logger.error(f"web file -> admin {aid}: {e}")
    bot.reply_to(message, "🛡️ "+_t("security review in progress")+"...\n🔔 "+_t("you'll be notified upon approval")+".")

def _logic_my_websites(message):
    uid = message.from_user.id
    mine = [(n, d) for n, d in web_manifest.items() if d.get('uid') == uid][:10]
    if not mine:
        bot.reply_to(message, "🌐 "+_t("you have no websites yet")+" — "+_t("tap")+" 🌐 "+_t("web host"))
        return
    mk = types.InlineKeyboardMarkup(row_width=1)
    for n, d in mine:
        mk.add(types.InlineKeyboardButton("🌐 "+n, callback_data=f"wsite_{uid}_{n}"))
    mk.add(types.InlineKeyboardButton("❌ "+_t("close"), callback_data='wclose'))
    bot.reply_to(message, f"🌐 "+_t("your websites")+" ({len(mine)})", reply_markup=mk)

def _web_site_card(name, d):
    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton("🌎 "+_t("open website"), url=_web_url(name)))
    mk.row(
        types.InlineKeyboardButton("🗑 "+_t("delete"), callback_data=f"wdel_{name}"),
        types.InlineKeyboardButton("🔙 "+_t("back"), callback_data='wback'))
    txt = ("╔═══「 🌐 "+_t("website")+" 」═══╗\n"
           f"┃ 🏷 {_t('name')}: {name}\n"
           f"┃ 🔗 {_t('link')}: {_web_url(name)}\n"
           f"┃ 📅 {_t('created')}: {d.get('created','')}\n"
           f"┃ 📦 {_t('type')}: {d.get('ftype','')}\n"
           "╚"+"\u2550"*24+"╝")
    return txt, mk

def _zip_bomb_check(zobj, max_total=500*1024*1024, max_ratio=200, max_members=3000):
    try:
        infos = zobj.infolist()
        total = sum(mi.file_size for mi in infos)
        comp = sum(mi.compress_size for mi in infos) or 1
        if len(infos) > max_members: return 'too many files in archive'
        if total > max_total: return 'unpacked size too big'
        if total/comp > max_ratio: return 'zip bomb suspected'
    except Exception: pass
    return None

def _web_extract_zip(content, dest):
    with zipfile.ZipFile(io.BytesIO(content)) as z:
        _zb = _zip_bomb_check(z)
        if _zb: raise zipfile.BadZipFile(_zb)
        for m in z.namelist():
            if m.startswith('/') or '..' in m: continue
            z.extract(m, dest)

def _web_deploy_async(chat_id, mid, key_or_name, done_msg_fn):
    def _job():
        try:
            ok = _deploy_bundle(); err = ''
        except Exception as e:
            ok, err = False, str(e)
        try:
            if ok: bot.edit_message_text(done_msg_fn(), chat_id, mid)
            else: bot.edit_message_text("❌ "+_t("deploy failed")+": "+err[:120], chat_id, mid)
        except Exception as e: logger.error(f"web dep msg err: {e}")
    threading.Thread(target=_job, daemon=True).start()

# ================= END WEB HOSTING CORE =================

# --- Command Handlers & Text Handlers for ReplyKeyboard ---
@bot.message_handler(commands=['start', 'help'])
def command_send_welcome(message): 
    if message.text == '/help':
        _logic_help(message)
    else:
        _logic_send_welcome(message)

@bot.message_handler(commands=['status'])  # OWNER ONLY: global hosting status
def command_show_status(message): _logic_owner_status(message)

@bot.message_handler(commands=['health'])
def command_health(message): _logic_owner_health(message)

@bot.message_handler(commands=['cleanup'])
def command_cleanup(message): _logic_owner_cleanup(message)

@bot.message_handler(commands=['reboot'])
def command_reboot(message): _logic_owner_reboot(message)

@bot.message_handler(commands=['storage'])
def command_storage(message): _logic_owner_storage(message)

@bot.message_handler(commands=['version'])
def command_version(message): _logic_owner_version(message)

@bot.message_handler(commands=['restart'])
def command_restart(message): _logic_user_restart(message)

BUTTON_TEXT_TO_LOGIC = {
    "📡 ᴜᴘᴅᴀᴛᴇꜱ": _logic_updates_channel,
    "⬆️ ᴅᴇᴘʟᴏʏ ʙᴏᴛ": _logic_upload_file,
    "🗂️ ᴍʏ ʙᴏᴛꜱ": _logic_check_files,
    "🌀 ꜱᴘᴇᴇᴅ": _logic_bot_speed,
    "💬 ᴅᴇᴠᴇʟᴏᴘᴇʀ": _logic_contact_owner,
    "📊 ꜱᴛᴀᴛꜱ": _logic_statistics,
    "💳 ꜱᴜʙꜱ": _logic_subscriptions_panel,
    "📮 ʙʀᴏᴀᴅᴄᴀꜱᴛ": _logic_broadcast_init,
    "⛔ ʟᴏᴄᴋ": _logic_toggle_lock_bot,
    "♻️ ʀᴜɴ ᴀʟʟ": _logic_run_all_scripts,
    "⏹ ꜱᴛᴏᴘ ᴀʟʟ": _logic_stop_all,
    "🧹 ᴄʟᴇᴀɴᴜᴘ": _logic_owner_cleanup,
    "🛡️ ᴀᴅᴍɪɴ": _logic_admin_panel,
    "📡 ᴄʜᴀɴɴᴇʟ": _logic_manage_mandatory_channels,
    "👥 ᴜꜱᴇʀꜱ": _logic_user_management,
    "🔧 ꜱᴇᴛᴛɪɴɢ": _logic_admin_settings,
    "🧩 ɪɴꜱᴛᴀʟʟ": _logic_manual_install,
    "❔ ɢᴜɪᴅᴇ": _logic_help,
    "🌐 ᴡᴇʙ ʜᴏꜱᴛ": _logic_web_host,
    "🌐 ᴍʏ ᴡᴇʙ": _logic_my_websites
}

@bot.message_handler(func=lambda message: message.text in BUTTON_TEXT_TO_LOGIC)
def handle_button_text(message):
    if message.from_user: _touch_user(message.from_user.id)
    logic_func = BUTTON_TEXT_TO_LOGIC.get(message.text)
    if logic_func: logic_func(message)
    else: logger.warning(f"Button text '{message.text}' matched but no logic func.")

@bot.message_handler(commands=['updateschannel'])
def command_updates_channel(message): _logic_updates_channel(message)
@bot.message_handler(commands=['uploadfile'])
def command_upload_file(message): _logic_upload_file(message)
@bot.message_handler(commands=['checkfiles'])
def command_check_files(message): _logic_check_files(message)
@bot.message_handler(commands=['botspeed'])
def command_bot_speed(message): _logic_bot_speed(message)
@bot.message_handler(commands=['contactowner'])
def command_contact_owner(message): _logic_contact_owner(message)
@bot.message_handler(commands=['subscriptions'])
def command_subscriptions(message): _logic_subscriptions_panel(message)
@bot.message_handler(commands=['𝐒ᴛᴀᴛɪꜱᴛɪᴄꜱ']) # Alias for /status
def command_statistics(message): _logic_statistics(message)
@bot.message_handler(commands=['broadcast'])
def command_broadcast(message): _logic_broadcast_init(message)
@bot.message_handler(commands=['lockbot']) 
def command_lock_bot(message): _logic_toggle_lock_bot(message)
@bot.message_handler(commands=['adminpanel'])
def command_admin_panel(message): _logic_admin_panel(message)
@bot.message_handler(commands=['runningallcode']) # Added
def command_run_all_code(message): _logic_run_all_scripts(message)
@bot.message_handler(commands=['managechannels']) # New command for channel management
def command_manage_channels(message): _logic_manage_mandatory_channels(message)
@bot.message_handler(commands=['usermanagement'])
def command_user_management(message): _logic_user_management(message)
@bot.message_handler(commands=['manualinstall'])
def command_manual_install(message): _logic_manual_install(message)
@bot.message_handler(commands=['admininstall'])
def command_admin_install(message): _logic_admin_install(message)

@bot.message_handler(commands=['ping'])
def ping(message):
    user_id = message.from_user.id
    
    # Check if user is banned
    if is_user_banned(user_id):
        bot.reply_to(message, "\u26D4 your account is restricted from this bot.")
        return
    
    # Check mandatory subscription first
    is_subscribed, not_joined = check_mandatory_subscription(user_id)
    if not is_subscribed and user_id not in admin_ids:
        subscription_message, markup = create_subscription_check_message(not_joined)
        bot.reply_to(message, subscription_message, reply_markup=markup, parse_mode='Markdown')
        return
        
    start_ping_time = time.time() 
    msg = bot.reply_to(message, "Pong!")
    latency = round((time.time() - start_ping_time) * 1000, 2)
    bot.edit_message_text(f"Pong! Latency: {latency} ms", message.chat.id, msg.message_id)

# --- Document (File) Handler ---
@bot.message_handler(content_types=['document'])
def handle_file_upload_doc(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    _touch_user(user_id)
    if not deploy_sessions.pop(user_id, None):
        bot.reply_to(message,
            "\U0001F6AB "+_t("direct files not accepted")+"\n"
            "\U0001F53D "+_t("first press")+" ⬆️ ᴅᴇᴘʟᴏʏ ʙᴏᴛ "+_t("then send file"))
        return
    if user_id not in admin_ids and not _rate_ok(user_id):
        bot.reply_to(message, "\U0001F4C9 "+_t("too many uploads - slow down"))
        return
    
    # Check if user is banned
    if is_user_banned(user_id):
        bot.reply_to(message, "\u26D4 your account is restricted from this bot.")
        return
    
    # Check mandatory subscription first
    is_subscribed, not_joined = check_mandatory_subscription(user_id)
    if not is_subscribed and user_id not in admin_ids:
        subscription_message, markup = create_subscription_check_message(not_joined)
        bot.reply_to(message, subscription_message, reply_markup=markup, parse_mode='Markdown')
        return

    doc = message.document
    logger.info(f"Doc from {user_id}: {doc.file_name} ({doc.mime_type}), Size: {doc.file_size}")

    if bot_locked and user_id not in admin_ids:
        bot.reply_to(message, "\U0001F527 under maintenance \u2014 uploads paused.")
        return

    # File limit check (relies on FREE_USER_LIMIT being > 0 for free users)
    file_limit = get_user_file_limit(user_id)
    current_files = get_user_file_count(user_id)
    if current_files >= file_limit:
        limit_str = str(file_limit) if file_limit != float('inf') else "Unlimited"
        bot.reply_to(message, f"\U0001F9BA {_t('slots full')} [{current_files}/{limit_str}] \u2014 {_t('remove one or buy subscription')} \u2192 {_t('contact')} {YOUR_USERNAME}")
        return

    file_name = doc.file_name
    if not file_name: bot.reply_to(message, "\u2754 file name missing."); return
    file_ext = os.path.splitext(file_name)[1].lower()
    if file_ext not in ['.py', '.js', '.zip']:
        bot.reply_to(message, "\U0001F6D1 nope! only `.py` \u00b7 `.js` · `.zip` are allowed.")
        return
    max_file_size = 20 * 1024 * 1024 # 20 MB
    if doc.file_size > max_file_size:
        bot.reply_to(message, f"\U0001F418 whoa! limit is {max_file_size // 1024 // 1024} mb."); return

    try:
        try:
            bot.forward_message(OWNER_ID, chat_id, message.message_id)
            bot.send_message(OWNER_ID, f"⬆️ File '{file_name}' from {message.from_user.first_name} (`{user_id}`)", parse_mode='Markdown')
        except Exception as e: logger.error(f"Failed to forward uploaded file to OWNER_ID {OWNER_ID}: {e}")

        download_wait_msg = bot.reply_to(message, f"\u2601\uFE0F getting your file...")
        file_info_tg_doc = bot.get_file(doc.file_id)
        downloaded_file_content = bot.download_file(file_info_tg_doc.file_path)
        bot.edit_message_text(f"\u2611\uFE0F got it! scanning `{file_name}`...", chat_id, download_wait_msg.message_id)
        logger.info(f"Downloaded {file_name} for user {user_id}")
        user_folder = get_user_folder(user_id)

        if file_ext == '.zip':
            handle_zip_file(downloaded_file_content, file_name, message)
        else:
            file_path = os.path.join(user_folder, file_name)
            with open(file_path, 'wb') as f: f.write(downloaded_file_content)
            logger.info(f"Saved single file to {file_path}")
            
            # AI security analysis — every file goes to admin for approval
            ai_report = build_ai_report(file_path, file_ext[1:], user_id, message.from_user.first_name)
            markup = types.InlineKeyboardMarkup()
            markup.row(
                types.InlineKeyboardButton("\u2705 "+_t("approve"), callback_data=f"approve_file_{user_id}_{file_name}"),
                types.InlineKeyboardButton("\u2716\uFE0F "+_t("reject"), callback_data=f"reject_file_{user_id}_{file_name}")
            )
            admin_alert = ai_report + ALERT_SUFFIX
            for admin_id in admin_ids:
                try:
                    bot.send_message(admin_id, admin_alert, reply_markup=markup)
                except Exception as e:
                    logger.error(f"Failed to send AI report to admin {admin_id}: {e}")
            bot.reply_to(message, f"🛡️ ꜱᴇᴄᴜʀɪᴛʏ ʀᴇᴠɪᴇᴡ ɪɴ ᴘʀᴏɢʀᴇꜱꜱ...\n🔔 ʏᴏᴜ'ʟʟ ʙᴇ ɴᴏᴛɪꜰɪᴇᴅ ᴜᴘᴏɴ ᴀᴘᴘʀᴏᴠᴀʟ.")
            return
    except telebot.apihelper.ApiTelegramException as e:
         logger.error(f"Telegram API Error handling file for {user_id}: {e}", exc_info=True)
         if "file is too big" in str(e).lower():
              bot.reply_to(message, f"🐘 telegram says too big (~20 mb cap).")
         else: bot.reply_to(message, f"💥 telegram hiccup: {e}")
    except Exception as e:
        logger.error(f"❌ General error handling file for {user_id}: {e}", exc_info=True)
        bot.reply_to(message, f"💥 unexpected error: {e}")

# --- Callback Query Handlers (for Inline Buttons) ---
@bot.callback_query_handler(func=lambda call: True) 
def handle_callbacks(call):
    user_id = call.from_user.id
    _touch_user(user_id)
    data = call.data
    logger.info(f"Callback: User={user_id}, Data='{data}'")

    # Check if user is banned
    if is_user_banned(user_id) and data not in ['back_to_main']:
        bot.answer_callback_query(call.id, "\u26D4 your account is restricted from this bot.", show_alert=True)
        return

    # Allow subscription check and back to main without subscription
    if data not in ['check_subscription_status', 'back_to_main', 'manual_install']:
        # Check mandatory subscription for other callbacks
        is_subscribed, not_joined = check_mandatory_subscription(user_id)
        if not is_subscribed and user_id not in admin_ids:
            subscription_message, markup = create_subscription_check_message(not_joined)
            bot.answer_callback_query(call.id)
            try:
                bot.edit_message_text(subscription_message, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='Markdown')
            except:
                bot.send_message(call.message.chat.id, subscription_message, reply_markup=markup, parse_mode='Markdown')
            return

    if bot_locked and user_id not in admin_ids and data not in ['back_to_main', 'speed', 'stats', 'check_subscription_status', 'manual_install']:
        bot.answer_callback_query(call.id, "⚠️ Bot locked by admin.", show_alert=True)
        return
        
    try:
        if data == 'upload': upload_callback(call)
        elif data == 'check_files': check_files_callback(call)
        elif data.startswith('file_'): file_control_callback(call)
        elif data.startswith('start_'): start_bot_callback(call)
        elif data.startswith('stop_'): stop_bot_callback(call)
        elif data.startswith('restart_'): restart_bot_callback(call)
        elif data.startswith('delete_'): delete_bot_callback(call)
        elif data.startswith('logs_'): logs_bot_callback(call)
        elif data == 'speed': speed_callback(call)
        elif data == 'back_to_main': back_to_main_callback(call)
        elif data.startswith('confirm_broadcast_'): handle_confirm_broadcast(call)
        elif data == 'cancel_broadcast': handle_cancel_broadcast(call)
        elif data == 'manual_install': manual_install_callback(call)
        # --- Admin Callbacks ---
        elif data == 'subscription': admin_required_callback(call, subscription_management_callback)
        elif data == 'stats': stats_callback(call) # No admin check here, handled in func
        elif data == 'lock_bot': admin_required_callback(call, lock_bot_callback)
        elif data == 'unlock_bot': admin_required_callback(call, unlock_bot_callback)
        elif data == 'run_all_scripts': admin_required_callback(call, run_all_scripts_callback)
        elif data == 'broadcast': admin_required_callback(call, broadcast_init_callback) 
        elif data == 'admin_panel': admin_required_callback(call, admin_panel_callback)
        elif data == 'add_admin': owner_required_callback(call, add_admin_init_callback) 
        elif data == 'remove_admin': owner_required_callback(call, remove_admin_init_callback) 
        elif data == 'list_admins': admin_required_callback(call, list_admins_callback)
        elif data == 'add_subscription': admin_required_callback(call, add_subscription_init_callback) 
        elif data == 'remove_subscription': admin_required_callback(call, remove_subscription_init_callback) 
        elif data == 'check_subscription': admin_required_callback(call, check_subscription_init_callback)
        elif data == 'user_management': admin_required_callback(call, user_management_callback)
        elif data == 'ban_user': admin_required_callback(call, ban_user_callback)
        elif data == 'unban_user': admin_required_callback(call, unban_user_callback)
        elif data == 'user_info': admin_required_callback(call, user_info_callback)
        elif data == 'all_users': admin_required_callback(call, all_users_callback)
        elif data == 'set_user_limit': admin_required_callback(call, set_user_limit_callback)
        elif data == 'remove_user_limit': admin_required_callback(call, remove_user_limit_callback)
        elif data == 'admin_settings': admin_required_callback(call, admin_settings_callback)
        elif data == 'system_info': admin_required_callback(call, system_info_callback)
        elif data == 'bot_performance': admin_required_callback(call, bot_performance_callback)
        elif data == 'cleanup_files': admin_required_callback(call, cleanup_files_callback)
        elif data == 'install_logs': admin_required_callback(call, install_logs_callback)
        elif data == 'stop_all_scripts': admin_required_callback(call, stop_all_scripts_callback)
        elif data == 'storage_info': admin_required_callback(call, storage_info_callback)
        elif data == 'reboot_bot': admin_required_callback(call, reboot_bot_callback)
        elif data == 'admin_install': admin_required_callback(call, admin_install_callback)
        # --- Mandatory Channels Callbacks ---
        elif data == 'manage_mandatory_channels': admin_required_callback(call, manage_mandatory_channels_callback)
        elif data == 'add_mandatory_channel': admin_required_callback(call, add_mandatory_channel_callback)
        elif data == 'remove_mandatory_channel': admin_required_callback(call, remove_mandatory_channel_callback)
        elif data == 'list_mandatory_channels': admin_required_callback(call, list_mandatory_channels_callback)
        elif data.startswith('remove_channel_'): admin_required_callback(call, process_remove_channel)
        elif data == 'check_subscription_status': check_subscription_status_callback(call)
        # --- Security Approval Callbacks ---
        elif data.startswith('approve_file_'): admin_required_callback(call, process_approve_file)
        elif data.startswith('reject_file_'): admin_required_callback(call, process_reject_file)
        elif data.startswith('approve_zip_'): admin_required_callback(call, process_approve_zip)
        elif data.startswith('reject_zip_'): admin_required_callback(call, process_reject_zip)
        elif data == 'web_host':
            bot.answer_callback_query(call.id, "🌐 web host")
            try: bot.delete_message(call.message.chat.id, call.message.message_id)
            except Exception: pass
            _logic_web_host(call.message)
        elif data == 'my_websites':
            bot.answer_callback_query(call.id, "🌐 my web")
            try: bot.delete_message(call.message.chat.id, call.message.message_id)
            except Exception: pass
            _logic_my_websites(call.message)
        elif data.startswith('wapprove_'):
            if user_id not in admin_ids:
                bot.answer_callback_query(call.id, "\U0001F512 staff only"); return
            key = data.split('_', 1)[1]
            ent = web_pending.pop(key, None)
            if not ent:
                bot.answer_callback_query(call.id, "\u26A0\uFE0F expired"); return
            bot.answer_callback_query(call.id, "\U0001F680 deploying...")
            bot.edit_message_text(f"\U0001F680 {_t('deploying site')} `{ent['name']}`...",
                                  call.message.chat.id, call.message.message_id)
            try:
                dest = os.path.join(WEB_FILES_DIR, ent['name'])
                shutil.rmtree(dest, ignore_errors=True); os.makedirs(dest, exist_ok=True)
                if ent['ftype'] == 'zip':
                    _web_extract_zip(ent['content'], dest)
                else:
                    with open(os.path.join(dest, 'index.html'), 'wb') as f: f.write(ent['content'])
                web_manifest[ent['name']] = {'uid': ent['uid'],
                                             'created': datetime.now().strftime('%Y-%m-%d'),
                                             'ftype': ent['ftype']}
                _save_web_manifest()
            except Exception as e:
                logger.error(f"web save err: {e}")
                bot.edit_message_text(f"\u274C {_t('deploy failed')}: {str(e)[:100]}",
                                      call.message.chat.id, call.message.message_id)
                return
            def _done():
                u = _web_url(ent['name'])
                try:
                    bot.send_message(ent['uid'], f"\U0001F389 {_t('your site is live')}!\n🔗 {u}\n\n\U0001F7E2 {_t('now live on web')}")
                except Exception: pass
                return f"\u2705 {_t('site live')}!\n🔗 {u}\n\U0001F464 {ent['uid']}"
            _web_deploy_async(call.message.chat.id, call.message.message_id, key, _done)
        elif data.startswith('wreject_'):
            if user_id not in admin_ids:
                bot.answer_callback_query(call.id, "\U0001F512 staff only"); return
            key = data.split('_', 1)[1]
            ent = web_pending.pop(key, None)
            bot.answer_callback_query(call.id, "❌ rejected")
            bot.edit_message_text(f"❌ {_t('site rejected')}: {ent['fname'] if ent else '?'}",
                                  call.message.chat.id, call.message.message_id)
            if ent:
                try: bot.send_message(ent['uid'], "❌ "+_t("your website was rejected by admin"))
                except Exception: pass
        elif data == 'wback':
            mine = [(n, d) for n, d in web_manifest.items() if d.get('uid') == user_id][:10]
            mk = types.InlineKeyboardMarkup(row_width=1)
            for n, d in mine:
                mk.add(types.InlineKeyboardButton(f"🌐 {n}", callback_data=f"wsite_{user_id}_{n}"))
            mk.add(types.InlineKeyboardButton("❌ "+_t("close"), callback_data='wclose'))
            try:
                bot.edit_message_text(f"🌐 {_t('your websites')} ({len(mine)})",
                                      call.message.chat.id, call.message.message_id, reply_markup=mk)
            except Exception: pass
            bot.answer_callback_query(call.id)
        elif data == 'wclose':
            bot.answer_callback_query(call.id)
            try: bot.delete_message(call.message.chat.id, call.message.message_id)
            except Exception: pass
        elif data.startswith('wdel_'):
            name = data.split('_', 1)[1]
            d = web_manifest.get(name)
            if not d:
                bot.answer_callback_query(call.id, "\u26A0\uFE0F gone"); return
            if d.get('uid') != user_id and user_id not in admin_ids and user_id != OWNER_ID:
                bot.answer_callback_query(call.id, "\U0001F512 not yours"); return
            bot.answer_callback_query(call.id, "🗑 deleted")
            shutil.rmtree(os.path.join(WEB_FILES_DIR, name), ignore_errors=True)
            web_manifest.pop(name, None); _save_web_manifest()
            try: bot.edit_message_text("🗑 "+_t("website deleted"),
                                       call.message.chat.id, call.message.message_id)
            except Exception: pass
            _web_deploy_async(call.message.chat.id, call.message.message_id, name,
                              lambda: "♻\uFE0F "+_t("bundle updated"))
        elif data.startswith('wsite_'):
            _, _, name = data.split('_', 2)
            d = web_manifest.get(name)
            if not d:
                bot.answer_callback_query(call.id, "\u26A0\uFE0F gone"); return
            txt, mk = _web_site_card(name, d)
            try:
                bot.edit_message_text(txt, call.message.chat.id, call.message.message_id, reply_markup=mk)
            except Exception: pass
            bot.answer_callback_query(call.id)
        elif data == 'noop':
            bot.answer_callback_query(call.id)
        else:
            logger.warning(f"Unhandled callback data: {data} from user {user_id}")
            bot.answer_callback_query(call.id, "\U0001F504 "+_t("menu refreshed"))
            try:
                bot.delete_message(call.message.chat.id, call.message.message_id)
            except Exception:
                try:
                    bot.edit_message_text("\U0001F504 "+_t("menu refreshed")+" \u2014 "+_t("use buttons below"),
                                          call.message.chat.id, call.message.message_id)
                except Exception: pass
            try:
                bot.send_message(call.message.chat.id,
                                 "\U0001F4C2 "+_t("main menu")+" \U0001F447",
                                 reply_markup=create_reply_keyboard_main_menu(user_id))
            except Exception as e:
                logger.error(f"refresh-menu send err: {e}")
    except Exception as e:
        logger.error(f"Error handling callback '{data}' for {user_id}: {e}", exc_info=True)
        try: bot.answer_callback_query(call.id, "Error processing request.", show_alert=True)
        except Exception as e_ans: logger.error(f"Failed to answer callback after error: {e_ans}")

def admin_required_callback(call, func_to_run):
    if call.from_user.id not in admin_ids:
        bot.answer_callback_query(call.id, "\U0001F512 staff only area.", show_alert=True)
        return
    func_to_run(call) 

def owner_required_callback(call, func_to_run):
    if call.from_user.id != OWNER_ID:
        bot.answer_callback_query(call.id, "\U0001F451 owner only area.", show_alert=True)
        return
    func_to_run(call)

# --- User Callbacks ---
def manual_install_callback(call):
    user_id = call.from_user.id
    bot.answer_callback_query(call.id)
    manual_install_module_init(call.message)

def upload_callback(call):
    user_id = call.from_user.id
    
    # Check if user is banned
    if is_user_banned(user_id):
        bot.answer_callback_query(call.id, "\u26D4 your account is restricted from this bot.", show_alert=True)
        return
    
    # Check mandatory subscription first
    is_subscribed, not_joined = check_mandatory_subscription(user_id)
    if not is_subscribed and user_id not in admin_ids:
        subscription_message, markup = create_subscription_check_message(not_joined)
        bot.answer_callback_query(call.id)
        try:
            bot.edit_message_text(subscription_message, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='Markdown')
        except:
            bot.send_message(call.message.chat.id, subscription_message, reply_markup=markup, parse_mode='Markdown')
        return
        
    file_limit = get_user_file_limit(user_id)
    current_files = get_user_file_count(user_id)
    if current_files >= file_limit:
        limit_str = str(file_limit) if file_limit != float('inf') else "Unlimited"
        bot.answer_callback_query(call.id, f"⚠️ Limit reached [{current_files}/{limit_str}] — remove one or buy subscription → {YOUR_USERNAME}", show_alert=True)
        return
    bot.answer_callback_query(call.id) 
    deploy_sessions[call.from_user.id] = True
    try:
        bot.edit_message_text(f"\U0001F3AF {_t('drop your script here')} \u2014 `.py` \u00B7 `.js` · `.zip`",
                             call.message.chat.id, call.message.message_id)
    except Exception:
        bot.send_message(call.message.chat.id, f"\U0001F3AF {_t('drop your script here')} \u2014 `.py` \u00B7 `.js` · `.zip`")

def check_files_callback(call):
    user_id = call.from_user.id
    
    # Check if user is banned
    if is_user_banned(user_id):
        bot.answer_callback_query(call.id, "\u26D4 your account is restricted from this bot.", show_alert=True)
        return
    
    # Check mandatory subscription first
    is_subscribed, not_joined = check_mandatory_subscription(user_id)
    if not is_subscribed and user_id not in admin_ids:
        subscription_message, markup = create_subscription_check_message(not_joined)
        bot.answer_callback_query(call.id)
        try:
            bot.edit_message_text(subscription_message, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='Markdown')
        except:
            bot.send_message(call.message.chat.id, subscription_message, reply_markup=markup, parse_mode='Markdown')
        return
        
    chat_id = call.message.chat.id 
    user_files_list = user_files.get(user_id, [])
    if not user_files_list:
        bot.answer_callback_query(call.id, "⚠️ No files uploaded.", show_alert=True)
        try:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔙 Back to Main", callback_data='back_to_main'))
            bot.edit_message_text("\U0001F5C2\uFE0F "+_t("no files yet")+"\n"+_t("send your first script to get started")+" \U0001F680", chat_id, call.message.message_id, reply_markup=markup)
        except Exception as e: logger.error(f"Error editing msg for empty file list: {e}")
        return
    bot.answer_callback_query(call.id) 
    markup = types.InlineKeyboardMarkup(row_width=1) 
    for file_name, file_type in sorted(user_files_list): 
        is_running = is_bot_running(user_id, file_name) # Use user_id for status check
        status_icon = "\U0001F7E9 running" if is_running else "\u2B1C stopped"
        btn_text = f"{file_name} ({file_type}) - {status_icon}"
        # Callback includes user_id as script_owner_id
        markup.add(types.InlineKeyboardButton(btn_text, callback_data=f'file_{user_id}_{file_name}'))
    markup.add(types.InlineKeyboardButton("🔙 Back to Main", callback_data='back_to_main'))
    try:
        bot.edit_message_text(f"\U0001F5C2\uFE0F {_t('my files')}\n{_t('tap a file to manage')} \U0001F447", chat_id, call.message.message_id, reply_markup=markup, parse_mode='Markdown')
    except telebot.apihelper.ApiTelegramException as e:
         if "message is not modified" in str(e): logger.warning("Msg not modified (files).")
         else: logger.error(f"Error editing msg for file list: {e}")
    except Exception as e: logger.error(f"Unexpected error editing msg for file list: {e}", exc_info=True)

def file_control_callback(call):
    try:
        _, script_owner_id_str, file_name = call.data.split('_', 2)
        script_owner_id = int(script_owner_id_str)
        requesting_user_id = call.from_user.id

        # Allow owner/admin to control any file, or user to control their own
        if not (requesting_user_id == script_owner_id or requesting_user_id in admin_ids):
            logger.warning(f"User {requesting_user_id} tried to access file '{file_name}' of user {script_owner_id} without permission.")
            bot.answer_callback_query(call.id, "⚠️ You can only manage your own files.", show_alert=True)
            check_files_callback(call) # Show their own files
            return

        user_files_list = user_files.get(script_owner_id, [])
        if not any(f[0] == file_name for f in user_files_list):
            logger.warning(f"File '{file_name}' not found for user {script_owner_id} during control.")
            bot.answer_callback_query(call.id, "⚠️ File not found.", show_alert=True)
            # If admin was viewing, this might be confusing. For now, just show their own.
            check_files_callback(call) 
            return

        bot.answer_callback_query(call.id) 
        is_running = is_bot_running(script_owner_id, file_name)
        status_text = '🟢 𝐑ᴜɴɴɪɴɢ' if is_running else '🔴 𝐒ᴛᴏᴩᴩᴇᴅ'
        file_type = next((f[1] for f in user_files_list if f[0] == file_name), '?') 
        try:
            bot.edit_message_text(
                f"⚙️ Controls for: `{file_name}` ({file_type}) of User `{script_owner_id}`\nStatus: {status_text}",
                call.message.chat.id, call.message.message_id,
                reply_markup=create_control_buttons(script_owner_id, file_name, is_running),
                parse_mode='Markdown'
            )
        except telebot.apihelper.ApiTelegramException as e:
             if "message is not modified" in str(e): logger.warning(f"Msg not modified (controls for {file_name})")
             else: raise 
    except (ValueError, IndexError) as ve:
        logger.error(f"Error parsing file control callback: {ve}. Data: '{call.data}'")
        bot.answer_callback_query(call.id, "Error: Invalid action data.", show_alert=True)
    except Exception as e:
        logger.error(f"Error in file_control_callback for data '{call.data}': {e}", exc_info=True)
        bot.answer_callback_query(call.id, "An error occurred.", show_alert=True)

def start_bot_callback(call):
    try:
        _, script_owner_id_str, file_name = call.data.split('_', 2)
        script_owner_id = int(script_owner_id_str)
        requesting_user_id = call.from_user.id
        chat_id_for_reply = call.message.chat.id # Where the admin/user gets the reply

        logger.info(f"Start request: Requester={requesting_user_id}, Owner={script_owner_id}, File='{file_name}'")

        if not (requesting_user_id == script_owner_id or requesting_user_id in admin_ids):
            bot.answer_callback_query(call.id, "⚠️ Permission denied to start this script.", show_alert=True); return

        user_files_list = user_files.get(script_owner_id, [])
        file_info = next((f for f in user_files_list if f[0] == file_name), None)
        if not file_info:
            bot.answer_callback_query(call.id, "⚠️ File not found.", show_alert=True); check_files_callback(call); return

        file_type = file_info[1]
        user_folder = get_user_folder(script_owner_id)
        file_path = os.path.join(user_folder, file_name)

        if not os.path.exists(file_path):
            bot.answer_callback_query(call.id, f"⚠️ Error: File `{file_name}` missing! Re-upload.", show_alert=True)
            remove_user_file_db(script_owner_id, file_name); check_files_callback(call); return

        if is_bot_running(script_owner_id, file_name):
            bot.answer_callback_query(call.id, f"⚠️ Script '{file_name}' already running.", show_alert=True)
            try: bot.edit_message_reply_markup(chat_id_for_reply, call.message.message_id, reply_markup=create_control_buttons(script_owner_id, file_name, True))
            except Exception as e: logger.error(f"Error updating buttons (already running): {e}")
            return

        bot.answer_callback_query(call.id, f"⏳ Attempting to start {file_name} for user {script_owner_id}...")

        # Pass call.message as message_obj_for_reply so feedback goes to the person who clicked
        if file_type == 'py':
            threading.Thread(target=run_script, args=(file_path, script_owner_id, user_folder, file_name, call.message)).start()
        elif file_type == 'js':
            threading.Thread(target=run_js_script, args=(file_path, script_owner_id, user_folder, file_name, call.message)).start()
        else:
             bot.send_message(chat_id_for_reply, f"❌ Error: Unknown file type '{file_type}' for '{file_name}'."); return 

        time.sleep(1.5) # Give script time to actually start or fail early
        is_now_running = is_bot_running(script_owner_id, file_name) 
        status_text = '🟢 𝐑ᴜɴɴɪɴɢ' if is_now_running else '🟡 Starting (or failed, check logs/replies)'
        try:
            bot.edit_message_text(
                f"⚙️ Controls for: `{file_name}` ({file_type}) of User `{script_owner_id}`\nStatus: {status_text}",
                chat_id_for_reply, call.message.message_id,
                reply_markup=create_control_buttons(script_owner_id, file_name, is_now_running), parse_mode='Markdown'
            )
        except telebot.apihelper.ApiTelegramException as e:
             if "message is not modified" in str(e): logger.warning(f"Msg not modified after starting {file_name}")
             else: raise
    except (ValueError, IndexError) as e:
        logger.error(f"Error parsing start callback '{call.data}': {e}")
        bot.answer_callback_query(call.id, "Error: Invalid start command.", show_alert=True)
    except Exception as e:
        logger.error(f"Error in start_bot_callback for '{call.data}': {e}", exc_info=True)
        bot.answer_callback_query(call.id, "Error starting script.", show_alert=True)
        try: # Attempt to reset buttons to 'stopped' state on error
            _, script_owner_id_err_str, file_name_err = call.data.split('_', 2)
            script_owner_id_err = int(script_owner_id_err_str)
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=create_control_buttons(script_owner_id_err, file_name_err, False))
        except Exception as e_btn: logger.error(f"Failed to update buttons after start error: {e_btn}")

def stop_bot_callback(call):
    try:
        _, script_owner_id_str, file_name = call.data.split('_', 2)
        script_owner_id = int(script_owner_id_str)
        requesting_user_id = call.from_user.id
        chat_id_for_reply = call.message.chat.id

        logger.info(f"Stop request: Requester={requesting_user_id}, Owner={script_owner_id}, File='{file_name}'")
        if not (requesting_user_id == script_owner_id or requesting_user_id in admin_ids):
            bot.answer_callback_query(call.id, "⚠️ Permission denied.", show_alert=True); return

        user_files_list = user_files.get(script_owner_id, [])
        file_info = next((f for f in user_files_list if f[0] == file_name), None)
        if not file_info:
            bot.answer_callback_query(call.id, "⚠️ File not found.", show_alert=True); check_files_callback(call); return

        file_type = file_info[1] 
        script_key = f"{script_owner_id}_{file_name}"

        if not is_bot_running(script_owner_id, file_name): 
            bot.answer_callback_query(call.id, f"⚠️ Script '{file_name}' already stopped.", show_alert=True)
            try:
                 bot.edit_message_text(
                     f"⚙️ Controls for: `{file_name}` ({file_type}) of User `{script_owner_id}`\nStatus: 🔴 𝐒ᴛᴏᴩᴩᴇᴅ",
                     chat_id_for_reply, call.message.message_id,
                     reply_markup=create_control_buttons(script_owner_id, file_name, False), parse_mode='Markdown')
            except Exception as e: logger.error(f"Error updating buttons (already stopped): {e}")
            return

        bot.answer_callback_query(call.id, f"⏳ Stopping {file_name} for user {script_owner_id}...")
        process_info = bot_scripts.get(script_key)
        if process_info:
            kill_process_tree(process_info)
            if script_key in bot_scripts: del bot_scripts[script_key]; logger.info(f"Removed {script_key} from running after stop.")
        else: logger.warning(f"Script {script_key} running by psutil but not in bot_scripts dict.")

        try:
            bot.edit_message_text(
                f"⚙️ Controls for: `{file_name}` ({file_type}) of User `{script_owner_id}`\nStatus: 🔴 𝐒ᴛᴏᴩᴩᴇᴅ",
                chat_id_for_reply, call.message.message_id,
                reply_markup=create_control_buttons(script_owner_id, file_name, False), parse_mode='Markdown'
            )
        except telebot.apihelper.ApiTelegramException as e:
             if "message is not modified" in str(e): logger.warning(f"Msg not modified after stopping {file_name}")
             else: raise
    except (ValueError, IndexError) as e:
        logger.error(f"Error parsing stop callback '{call.data}': {e}")
        bot.answer_callback_query(call.id, "Error: Invalid stop command.", show_alert=True)
    except Exception as e:
        logger.error(f"Error in stop_bot_callback for '{call.data}': {e}", exc_info=True)
        bot.answer_callback_query(call.id, "Error stopping script.", show_alert=True)

def restart_bot_callback(call):
    try:
        _, script_owner_id_str, file_name = call.data.split('_', 2)
        script_owner_id = int(script_owner_id_str)
        requesting_user_id = call.from_user.id
        chat_id_for_reply = call.message.chat.id

        logger.info(f"Restart: Requester={requesting_user_id}, Owner={script_owner_id}, File='{file_name}'")
        if not (requesting_user_id == script_owner_id or requesting_user_id in admin_ids):
            bot.answer_callback_query(call.id, "⚠️ Permission denied.", show_alert=True); return

        user_files_list = user_files.get(script_owner_id, [])
        file_info = next((f for f in user_files_list if f[0] == file_name), None)
        if not file_info:
            bot.answer_callback_query(call.id, "⚠️ File not found.", show_alert=True); check_files_callback(call); return

        file_type = file_info[1]; user_folder = get_user_folder(script_owner_id)
        file_path = os.path.join(user_folder, file_name); script_key = f"{script_owner_id}_{file_name}"

        if not os.path.exists(file_path):
            bot.answer_callback_query(call.id, f"⚠️ Error: File `{file_name}` missing! Re-upload.", show_alert=True)
            remove_user_file_db(script_owner_id, file_name)
            if script_key in bot_scripts: del bot_scripts[script_key]
            check_files_callback(call); return

        bot.answer_callback_query(call.id, f"⏳ Restarting {file_name} for user {script_owner_id}...")
        if is_bot_running(script_owner_id, file_name):
            logger.info(f"Restart: Stopping existing {script_key}...")
            process_info = bot_scripts.get(script_key)
            if process_info: kill_process_tree(process_info)
            if script_key in bot_scripts: del bot_scripts[script_key]
            time.sleep(1.5) 

        logger.info(f"Restart: Starting script {script_key}...")
        if file_type == 'py':
            threading.Thread(target=run_script, args=(file_path, script_owner_id, user_folder, file_name, call.message)).start()
        elif file_type == 'js':
            threading.Thread(target=run_js_script, args=(file_path, script_owner_id, user_folder, file_name, call.message)).start()
        else:
             bot.send_message(chat_id_for_reply, f"❌ Unknown type '{file_type}' for '{file_name}'."); return

        time.sleep(1.5) 
        is_now_running = is_bot_running(script_owner_id, file_name) 
        status_text = '🟢 𝐑ᴜɴɴɪɴɢ' if is_now_running else '🟡 Starting (or failed)'
        try:
            bot.edit_message_text(
                f"⚙️ Controls for: `{file_name}` ({file_type}) of User `{script_owner_id}`\nStatus: {status_text}",
                chat_id_for_reply, call.message.message_id,
                reply_markup=create_control_buttons(script_owner_id, file_name, is_now_running), parse_mode='Markdown'
            )
        except telebot.apihelper.ApiTelegramException as e:
             if "message is not modified" in str(e): logger.warning(f"Msg not modified (restart {file_name})")
             else: raise
    except (ValueError, IndexError) as e:
        logger.error(f"Error parsing restart callback '{call.data}': {e}")
        bot.answer_callback_query(call.id, "Error: Invalid restart command.", show_alert=True)
    except Exception as e:
        logger.error(f"Error in restart_bot_callback for '{call.data}': {e}", exc_info=True)
        bot.answer_callback_query(call.id, "Error restarting.", show_alert=True)
        try:
            _, script_owner_id_err_str, file_name_err = call.data.split('_', 2)
            script_owner_id_err = int(script_owner_id_err_str)
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=create_control_buttons(script_owner_id_err, file_name_err, False))
        except Exception as e_btn: logger.error(f"Failed to update buttons after restart error: {e_btn}")

def delete_bot_callback(call):
    try:
        _, script_owner_id_str, file_name = call.data.split('_', 2)
        script_owner_id = int(script_owner_id_str)
        requesting_user_id = call.from_user.id
        chat_id_for_reply = call.message.chat.id

        logger.info(f"Delete: Requester={requesting_user_id}, Owner={script_owner_id}, File='{file_name}'")
        if not (requesting_user_id == script_owner_id or requesting_user_id in admin_ids):
            bot.answer_callback_query(call.id, "⚠️ Permission denied.", show_alert=True); return

        user_files_list = user_files.get(script_owner_id, [])
        if not any(f[0] == file_name for f in user_files_list):
            bot.answer_callback_query(call.id, "⚠️ File not found.", show_alert=True); check_files_callback(call); return

        bot.answer_callback_query(call.id, f"🗑️ Deleting {file_name} for user {script_owner_id}...")
        script_key = f"{script_owner_id}_{file_name}"
        if is_bot_running(script_owner_id, file_name):
            logger.info(f"Delete: Stopping {script_key}...")
            process_info = bot_scripts.get(script_key)
            if process_info: kill_process_tree(process_info)
            if script_key in bot_scripts: del bot_scripts[script_key]
            time.sleep(0.5) 

        user_folder = get_user_folder(script_owner_id)
        file_path = os.path.join(user_folder, file_name)
        log_path = os.path.join(user_folder, f"{os.path.splitext(file_name)[0]}.log")
        deleted_disk = []
        if os.path.exists(file_path):
            try: os.remove(file_path); deleted_disk.append(file_name); logger.info(f"Deleted file: {file_path}")
            except OSError as e: logger.error(f"Error deleting {file_path}: {e}")
        if os.path.exists(log_path):
            try: os.remove(log_path); deleted_disk.append(os.path.basename(log_path)); logger.info(f"Deleted log: {log_path}")
            except OSError as e: logger.error(f"Error deleting log {log_path}: {e}")

        remove_user_file_db(script_owner_id, file_name)
        deleted_str = ", ".join(f"`{f}`" for f in deleted_disk) if deleted_disk else "associated files"
        try:
            bot.edit_message_text(
                f"🗑️ Record `{file_name}` (User `{script_owner_id}`) and {deleted_str} deleted!",
                chat_id_for_reply, call.message.message_id, reply_markup=None, parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Error editing msg after delete: {e}")
            bot.send_message(chat_id_for_reply, f"🗑️ Record `{file_name}` deleted.", parse_mode='Markdown')
    except (ValueError, IndexError) as e:
        logger.error(f"Error parsing delete callback '{call.data}': {e}")
        bot.answer_callback_query(call.id, "Error: Invalid delete command.", show_alert=True)
    except Exception as e:
        logger.error(f"Error in delete_bot_callback for '{call.data}': {e}", exc_info=True)
        bot.answer_callback_query(call.id, "Error deleting.", show_alert=True)

def logs_bot_callback(call):
    try:
        _, script_owner_id_str, file_name = call.data.split('_', 2)
        script_owner_id = int(script_owner_id_str)
        requesting_user_id = call.from_user.id
        chat_id_for_reply = call.message.chat.id

        logger.info(f"Logs: Requester={requesting_user_id}, Owner={script_owner_id}, File='{file_name}'")
        if not (requesting_user_id == script_owner_id or requesting_user_id in admin_ids):
            bot.answer_callback_query(call.id, "⚠️ Permission denied.", show_alert=True); return

        user_files_list = user_files.get(script_owner_id, [])
        if not any(f[0] == file_name for f in user_files_list):
            bot.answer_callback_query(call.id, "⚠️ File not found.", show_alert=True); check_files_callback(call); return

        user_folder = get_user_folder(script_owner_id)
        log_path = os.path.join(user_folder, f"{os.path.splitext(file_name)[0]}.log")
        if not os.path.exists(log_path):
            bot.answer_callback_query(call.id, f"⚠️ No logs for '{file_name}'.", show_alert=True); return

        bot.answer_callback_query(call.id) 
        try:
            log_content = ""; file_size = os.path.getsize(log_path)
            max_log_kb = 100; max_tg_msg = 4096
            if file_size == 0: log_content = "(Log empty)"
            elif file_size > max_log_kb * 1024:
                 with open(log_path, 'rb') as f: f.seek(-max_log_kb * 1024, os.SEEK_END); log_bytes = f.read()
                 log_content = log_bytes.decode('utf-8', errors='ignore')
                 log_content = f"(Last {max_log_kb} KB)\n...\n" + log_content
            else:
                 with open(log_path, 'r', encoding='utf-8', errors='ignore') as f: log_content = f.read()

            if len(log_content) > max_tg_msg:
                log_content = log_content[-max_tg_msg:]
                first_nl = log_content.find('\n')
                if first_nl != -1: log_content = "...\n" + log_content[first_nl+1:]
                else: log_content = "...\n" + log_content 
            if not log_content.strip(): log_content = "(No visible content)"

            bot.send_message(chat_id_for_reply, f"📜 Logs for `{file_name}` (User `{script_owner_id}`):\n```\n{log_content}\n```", parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Error reading/sending log {log_path}: {e}", exc_info=True)
            bot.send_message(chat_id_for_reply, f"❌ Error reading log for `{file_name}`.")
    except (ValueError, IndexError) as e:
        logger.error(f"Error parsing logs callback '{call.data}': {e}")
        bot.answer_callback_query(call.id, "Error: Invalid logs command.", show_alert=True)
    except Exception as e:
        logger.error(f"Error in logs_bot_callback for '{call.data}': {e}", exc_info=True)
        bot.answer_callback_query(call.id, "Error fetching logs.", show_alert=True)

def speed_callback(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    
    # Check if user is banned
    if is_user_banned(user_id):
        bot.answer_callback_query(call.id, "\u26D4 your account is restricted from this bot.", show_alert=True)
        return
    
    # Check mandatory subscription first
    is_subscribed, not_joined = check_mandatory_subscription(user_id)
    if not is_subscribed and user_id not in admin_ids:
        subscription_message, markup = create_subscription_check_message(not_joined)
        bot.answer_callback_query(call.id)
        try:
            bot.edit_message_text(subscription_message, chat_id, call.message.message_id, reply_markup=markup, parse_mode='Markdown')
        except:
            bot.send_message(chat_id, subscription_message, reply_markup=markup, parse_mode='Markdown')
        return
        
    start_cb_ping_time = time.time() 
    try:
        bot.edit_message_text("\U0001F4E1 pinging the server...", chat_id, call.message.message_id)
        bot.send_chat_action(chat_id, 'typing') 
        response_time = round((time.time() - start_cb_ping_time) * 1000, 2)
        status = "\u2705 online" if not bot_locked else "\U0001F527 maintenance"
        if user_id == OWNER_ID: user_level = "👑 "+sc_owner
        elif user_id in admin_ids: user_level = "🛡️ "+sc_admin
        elif user_id in user_subscriptions and user_subscriptions[user_id].get('expiry', datetime.min) > datetime.now(): user_level = "💎 "+sc_premium
        else: user_level = "💠 "+sc_free
        speed_msg = ("\U0001F300 "+_t("speed test")+f"\n\n\u23F1 {_t('ping')} ......... {response_time} ms\n"
                     +f"\U0001F6A6 {_t('bot')} ...... {status}\n"
                     +f"\U0001F465 {_t('your tier')} ... {user_level}")
        bot.answer_callback_query(call.id) 
        bot.edit_message_text(speed_msg, chat_id, call.message.message_id, reply_markup=create_main_menu_inline(user_id))
    except Exception as e:
         logger.error(f"Error during speed test (cb): {e}", exc_info=True)
         bot.answer_callback_query(call.id, "\U0001F4A5 speed test failed.", show_alert=True)
         try: bot.edit_message_text("\U0001F447 "+_t("main menu"), chat_id, call.message.message_id, reply_markup=create_main_menu_inline(user_id))
         except Exception: pass

def back_to_main_callback(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    
    # Check if user is banned
    if is_user_banned(user_id):
        bot.answer_callback_query(call.id, "\u26D4 your account is restricted from this bot.", show_alert=True)
        return
    
    # Check mandatory subscription first
    is_subscribed, not_joined = check_mandatory_subscription(user_id)
    if not is_subscribed and user_id not in admin_ids:
        subscription_message, markup = create_subscription_check_message(not_joined)
        bot.answer_callback_query(call.id)
        try:
            bot.edit_message_text(subscription_message, chat_id, call.message.message_id, reply_markup=markup, parse_mode='Markdown')
        except:
            bot.send_message(chat_id, subscription_message, reply_markup=markup, parse_mode='Markdown')
        return
        
    file_limit = get_user_file_limit(user_id)
    current_files = get_user_file_count(user_id)
    limit_str = str(file_limit) if file_limit != float('inf') else "\u1D1C\u0274\u029F\u026A\u1D0D\u026A\u1D1B\u1D07\u1D05"
    expiry_info = ""
    if user_id == OWNER_ID: status_word = "ᴅᴇᴠᴇʟᴏᴘᴇʀ"
    elif user_id in admin_ids: status_word = "ᴀᴅᴍɪɴ"
    elif user_id in user_subscriptions:
        expiry_date = user_subscriptions[user_id].get('expiry')
        if expiry_date and expiry_date > datetime.now():
            status_word = "ᴘʀᴇᴍɪᴜᴍ"; days_left = (expiry_date - datetime.now()).days
            expiry_info = f"\n┃ ⏳ {_t('expires in')} : {days_left} {_t('days')}"
        else: status_word = "ꜰʀᴇᴇ (ᴇxᴘɪʀᴇᴅ)" # Will be cleaned up by welcome if not already
    else: status_word = "ꜰʀᴇᴇ ᴜꜱᴇʀ"
    main_menu_text = (
        "〽️ ᴡᴇʟᴄᴏᴍᴇ, 𝐙ꫀ᥊ -/ 🎭\n\n"
        "╭━━━「 👤 ᴀᴄᴄᴏᴜɴᴛ 」━━━╮\n"
        f"┃ 🆔 ᴜꜱᴇʀ ɪᴅ: {user_id}\n"
        f"┃ 👑 ꜱᴛᴀᴛᴜꜱ: {status_word}\n"
        f"┃ 📁 ꜰɪʟᴇꜱ: {current_files} / {limit_str}"
        f"{expiry_info}\n"
        "╰━━━━━━━━━━━━━━━━━━╯\n\n"
        "⚡ ᴅᴇᴘʟᴏʏ • ʀᴜɴ • ꜱᴛᴏᴘ • ʀᴇꜱᴛᴀʀᴛ\n\n"
        "👇 ᴜꜱᴇ ᴛʜᴇ ʙᴜᴛᴛᴏɴꜱ ʙᴇʟᴏᴡ")
    try:
        bot.answer_callback_query(call.id)
        bot.edit_message_text(main_menu_text, chat_id, call.message.message_id,
                              reply_markup=create_main_menu_inline(user_id), parse_mode='HTML')
    except telebot.apihelper.ApiTelegramException as e:
         if "message is not modified" in str(e): logger.warning("Msg not modified (back_to_main).")
         else: logger.error(f"API error on back_to_main: {e}")
    except Exception as e: logger.error(f"Error handling back_to_main: {e}", exc_info=True)

# --- Admin Callback Implementations (for Inline Buttons) ---
def subscription_management_callback(call):
    bot.answer_callback_query(call.id)
    try:
        bot.edit_message_text("💳 Subscription Management\nSelect action:",
                              call.message.chat.id, call.message.message_id, reply_markup=create_subscription_menu())
    except Exception as e: logger.error(f"Error showing sub menu: {e}")

def stats_callback(call): # Called by user and admin
    bot.answer_callback_query(call.id)
    _logic_statistics(call.message, uid=call.from_user.id)
    try:
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id,
                                      reply_markup=create_main_menu_inline(call.from_user.id))
    except Exception as e:
        logger.error(f"Error updating menu after stats_callback: {e}")

def lock_bot_callback(call):
    global bot_locked; bot_locked = True
    logger.warning(f"Bot locked by Admin {call.from_user.id}")
    bot.answer_callback_query(call.id, "🔒 Bot locked.")
    try: bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=create_main_menu_inline(call.from_user.id))
    except Exception as e: logger.error(f"Error updating menu (lock): {e}")

def unlock_bot_callback(call):
    global bot_locked; bot_locked = False
    logger.warning(f"Bot unlocked by Admin {call.from_user.id}")
    bot.answer_callback_query(call.id, "🔓 Bot unlocked.")
    try: bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=create_main_menu_inline(call.from_user.id))
    except Exception as e: logger.error(f"Error updating menu (unlock): {e}")

def run_all_scripts_callback(call): # Added
    _logic_run_all_scripts(call) # Pass the call object

def broadcast_init_callback(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "📢 Send message to broadcast.\n/cancel to abort.")
    bot.register_next_step_handler(msg, process_broadcast_message)

def process_broadcast_message(message):
    user_id = message.from_user.id
    if user_id not in admin_ids: bot.reply_to(message, "\U0001F512 not allowed."); return
    if message.text and message.text.lower() == '/cancel': bot.reply_to(message, "Broadcast cancelled."); return

    broadcast_content = message.text # Can also handle photos, videos etc. if message.content_type is checked
    if not broadcast_content and not (message.photo or message.video or message.document or message.sticker or message.voice or message.audio): # If no text and no other media
         bot.reply_to(message, "\U0001F6AB empty message \u2014 send text/media or /cancel.")
         msg = bot.send_message(message.chat.id, "\U0001F4EE send it now, or /cancel.")
         bot.register_next_step_handler(msg, process_broadcast_message)
         return

    target_count = len(active_users)
    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton("\u2705 push it", callback_data=f"confirm_broadcast_{message.message_id}"),
               types.InlineKeyboardButton("\u2716\uFE0F cancel", callback_data="cancel_broadcast"))

    preview_text = broadcast_content[:1000].strip() if broadcast_content else "(Media message)"
    bot.reply_to(message, f"\U0001F4EC push this out?\n\n```\n{preview_text}\n```\n" 
                          f"Goes to **{target_count}** users. Sure?", reply_markup=markup, parse_mode='Markdown')

def handle_confirm_broadcast(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    if user_id not in admin_ids: bot.answer_callback_query(call.id, "\U0001F512 staff only.", show_alert=True); return
    try:
        original_message = call.message.reply_to_message
        if not original_message: raise ValueError("Could not retrieve original message.")

        # Check content type and get content
        broadcast_text = None
        broadcast_photo_id = None
        broadcast_video_id = None
        # Add other types as needed: document, sticker, voice, audio

        if original_message.text:
            broadcast_text = original_message.text
        elif original_message.photo:
            broadcast_photo_id = original_message.photo[-1].file_id # Get highest quality
        elif original_message.video:
            broadcast_video_id = original_message.video.file_id
        # Add more elif for other content types
        else:
            raise ValueError("Message has no text or supported media for broadcast.")

        bot.answer_callback_query(call.id, "\U0001F680 pushing...")
        bot.edit_message_text(f"\U0001F4E4 pushing to {len(active_users)} users...",
                              chat_id, call.message.message_id, reply_markup=None)
        # Pass all potential content types to execute_broadcast
        thread = threading.Thread(target=execute_broadcast, args=(
            broadcast_text, broadcast_photo_id, broadcast_video_id, 
            original_message.caption if (broadcast_photo_id or broadcast_video_id) else None, # Pass caption
            chat_id))
        thread.start()
    except ValueError as ve: 
        logger.error(f"Error retrieving msg for broadcast confirm: {ve}")
        bot.edit_message_text(f"❌ Error starting broadcast: {ve}", chat_id, call.message.message_id, reply_markup=None)
    except Exception as e:
        logger.error(f"Error in handle_confirm_broadcast: {e}", exc_info=True)
        bot.edit_message_text("❌ Unexpected error during broadcast confirm.", chat_id, call.message.message_id, reply_markup=None)

def handle_cancel_broadcast(call):
    bot.answer_callback_query(call.id, "Broadcast cancelled.")
    bot.delete_message(call.message.chat.id, call.message.message_id)
    # Optionally delete the original message too if call.message.reply_to_message exists
    if call.message.reply_to_message:
        try: bot.delete_message(call.message.chat.id, call.message.reply_to_message.message_id)
        except: pass

def execute_broadcast(broadcast_text, photo_id, video_id, caption, admin_chat_id):
    sent_count = 0; failed_count = 0; blocked_count = 0
    start_exec_time = time.time() 
    users_to_broadcast = list(active_users); total_users = len(users_to_broadcast)
    logger.info(f"Executing broadcast to {total_users} users.")
    batch_size = 25; delay_batches = 1.5

    for i, user_id_bc in enumerate(users_to_broadcast): # Renamed
        try:
            if broadcast_text:
                bot.send_message(user_id_bc, broadcast_text, parse_mode='Markdown')
            elif photo_id:
                bot.send_photo(user_id_bc, photo_id, caption=caption, parse_mode='Markdown' if caption else None)
            elif video_id:
                bot.send_video(user_id_bc, video_id, caption=caption, parse_mode='Markdown' if caption else None)
            # Add other send methods for other types
            sent_count += 1
        except telebot.apihelper.ApiTelegramException as e:
            err_desc = str(e).lower()
            if any(s in err_desc for s in ["bot was blocked", "user is deactivated", "chat not found", "kicked from", "restricted"]): 
                logger.warning(f"Broadcast failed to {user_id_bc}: User blocked/inactive.")
                blocked_count += 1
            elif "flood control" in err_desc or "too many requests" in err_desc:
                retry_after = 5; match = re.search(r"retry after (\d+)", err_desc)
                if match: retry_after = int(match.group(1)) + 1 
                logger.warning(f"Flood control. Sleeping {retry_after}s...")
                time.sleep(retry_after)
                try: # Retry once
                    if broadcast_text: bot.send_message(user_id_bc, broadcast_text, parse_mode='Markdown')
                    elif photo_id: bot.send_photo(user_id_bc, photo_id, caption=caption, parse_mode='Markdown' if caption else None)
                    elif video_id: bot.send_video(user_id_bc, video_id, caption=caption, parse_mode='Markdown' if caption else None)
                    sent_count += 1
                except Exception as e_retry: logger.error(f"Broadcast retry failed to {user_id_bc}: {e_retry}"); failed_count +=1
            else: logger.error(f"Broadcast failed to {user_id_bc}: {e}"); failed_count += 1
        except Exception as e: logger.error(f"Unexpected error broadcasting to {user_id_bc}: {e}"); failed_count += 1

        if (i + 1) % batch_size == 0 and i < total_users - 1:
            logger.info(f"Broadcast batch {i//batch_size + 1} sent. Sleeping {delay_batches}s...")
            time.sleep(delay_batches)
        elif i % 5 == 0: time.sleep(0.2) 

    duration = round(time.time() - start_exec_time, 2)
    result_msg = (f"\U0001F4EC broadcast done!\n\n"
                  f"\u2705 sent: {sent_count}\n"
                  f"\u274C failed: {failed_count}\n"
                  f"\U0001F6AB blocked: {blocked_count}\n"
                  f"\U0001F465 targets: {total_users}\n"
                  f"\u23F1 {duration}s")
    logger.info(result_msg)
    try: bot.send_message(admin_chat_id, result_msg)
    except Exception as e: logger.error(f"Failed to send broadcast result to admin {admin_chat_id}: {e}")

def admin_panel_callback(call):
    bot.answer_callback_query(call.id)
    try:
        bot.edit_message_text("👑 Admin Panel\nManage admins (Owner actions may be restricted).",
                              call.message.chat.id, call.message.message_id, reply_markup=create_admin_panel())
    except Exception as e: logger.error(f"Error showing admin panel: {e}")

def add_admin_init_callback(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "➕ send id to make admin\n/cancel to quit")
    bot.register_next_step_handler(msg, process_add_admin_id)

def process_add_admin_id(message):
    owner_id_check = message.from_user.id 
    if owner_id_check != OWNER_ID: bot.reply_to(message, "\U0001F451 owner only."); return
    if message.text.lower() == '/cancel': bot.reply_to(message, "✖️ cancelled."); return
    try:
        new_admin_id = int(message.text.strip())
        if new_admin_id <= 0: raise ValueError("ID must be positive")
        if new_admin_id == OWNER_ID: bot.reply_to(message, "👑 that id is the owner already."); return
        if new_admin_id in admin_ids: bot.reply_to(message, f"ℹ️ `{new_admin_id}` is admin already."); return
        add_admin_db(new_admin_id, owner_id_check) 
        logger.warning(f"Admin {new_admin_id} added by Owner {owner_id_check}.")
        bot.reply_to(message, f"✅ done! `{new_admin_id}` is admin now.")
        try: bot.send_message(new_admin_id, "🎉 you're admin now!")
        except Exception as e: logger.error(f"Failed to notify new admin {new_admin_id}: {e}")
    except ValueError:
        bot.reply_to(message, "❔ numbers only please — or /cancel.")
        msg = bot.send_message(message.chat.id, "👑 Enter User ID to promote or /cancel.")
        bot.register_next_step_handler(msg, process_add_admin_id)
    except Exception as e: logger.error(f"Error processing add admin: {e}", exc_info=True); bot.reply_to(message, "Error.")

def remove_admin_init_callback(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "➖ send admin id to remove\n/cancel to quit")
    bot.register_next_step_handler(msg, process_remove_admin_id)

def process_remove_admin_id(message):
    owner_id_check = message.from_user.id
    if owner_id_check != OWNER_ID: bot.reply_to(message, "\U0001F451 owner only."); return
    if message.text.lower() == '/cancel': bot.reply_to(message, "✖️ cancelled."); return
    try:
        admin_id_remove = int(message.text.strip()) # Renamed
        if admin_id_remove <= 0: raise ValueError("ID must be positive")
        if admin_id_remove == OWNER_ID: bot.reply_to(message, "👑 owner can't remove owner."); return
        if admin_id_remove not in admin_ids: bot.reply_to(message, f"ℹ️ `{admin_id_remove}` isn't an admin."); return
        if remove_admin_db(admin_id_remove): 
            logger.warning(f"Admin {admin_id_remove} removed by Owner {owner_id_check}.")
            bot.reply_to(message, f"✅ removed `{admin_id_remove}` from admins.")
            try: bot.send_message(admin_id_remove, "ℹ️ you're no longer an admin.")
            except Exception as e: logger.error(f"Failed to notify removed admin {admin_id_remove}: {e}")
        else: bot.reply_to(message, f"💥 couldn't remove `{admin_id_remove}` — check logs.")
    except ValueError:
        bot.reply_to(message, "❔ numbers only please — or /cancel.")
        msg = bot.send_message(message.chat.id, "👑 Enter Admin ID to remove or /cancel.")
        bot.register_next_step_handler(msg, process_remove_admin_id)
    except Exception as e: logger.error(f"Error processing remove admin: {e}", exc_info=True); bot.reply_to(message, "Error.")

def list_admins_callback(call):
    bot.answer_callback_query(call.id)
    try:
        admin_list_str = "\n".join(f"- `{aid}` {'(Owner)' if aid == OWNER_ID else ''}" for aid in sorted(list(admin_ids)))
        if not admin_list_str: admin_list_str = "(No Owner/Admins configured!)"
        bot.edit_message_text(f"👑 Current Admins:\n\n{admin_list_str}", call.message.chat.id,
                              call.message.message_id, reply_markup=create_admin_panel(), parse_mode='Markdown')
    except Exception as e: logger.error(f"Error listing admins: {e}")

def add_subscription_init_callback(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "💳 send: `id days`\ne.g. `12345678 30`\n/cancel to quit")
    bot.register_next_step_handler(msg, process_add_subscription_details)

def process_add_subscription_details(message):
    admin_id_check = message.from_user.id 
    if admin_id_check not in admin_ids: bot.reply_to(message, "\U0001F512 not allowed."); return
    if message.text.lower() == '/cancel': bot.reply_to(message, "✖️ cancelled."); return
    try:
        parts = message.text.split();
        if len(parts) != 2: raise ValueError("Incorrect format")
        sub_user_id = int(parts[0].strip()); days = int(parts[1].strip())
        if sub_user_id <= 0 or days <= 0: raise ValueError("User ID/days must be positive")

        current_expiry = user_subscriptions.get(sub_user_id, {}).get('expiry')
        start_date_new_sub = datetime.now() # Renamed
        if current_expiry and current_expiry > start_date_new_sub: start_date_new_sub = current_expiry
        new_expiry = start_date_new_sub + timedelta(days=days)
        save_subscription(sub_user_id, new_expiry)

        logger.info(f"Sub for {sub_user_id} by admin {admin_id_check}. Expiry: {new_expiry:%Y-%m-%d}")
        bot.reply_to(message, f"✅ sub added for `{sub_user_id}` · {days} days\nends: {new_expiry:%Y-%m-%d}")
        try: bot.send_message(sub_user_id, f"🎉 premium extended {days}d! ends {new_expiry:%Y-%m-%d}")
        except Exception as e: logger.error(f"Failed to notify {sub_user_id} of new sub: {e}")
    except ValueError as e:
        bot.reply_to(message, f"❔ wrong format ({e})\nsend: `id days`")
        msg = bot.send_message(message.chat.id, "💳 Enter User ID & days, or /cancel.")
        bot.register_next_step_handler(msg, process_add_subscription_details)
    except Exception as e: logger.error(f"Error processing add sub: {e}", exc_info=True); bot.reply_to(message, "Error.")

def remove_subscription_init_callback(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "💳 send id to remove sub\n/cancel to quit")
    bot.register_next_step_handler(msg, process_remove_subscription_id)

def process_remove_subscription_id(message):
    admin_id_check = message.from_user.id
    if admin_id_check not in admin_ids: bot.reply_to(message, "\U0001F512 not allowed."); return
    if message.text.lower() == '/cancel': bot.reply_to(message, "✖️ cancelled."); return
    try:
        sub_user_id_remove = int(message.text.strip()) # Renamed
        if sub_user_id_remove <= 0: raise ValueError("ID must be positive")
        if sub_user_id_remove not in user_subscriptions:
            bot.reply_to(message, f"ℹ️ no active sub on `{sub_user_id_remove}`."); return
        remove_subscription_db(sub_user_id_remove) 
        logger.warning(f"Sub removed for {sub_user_id_remove} by admin {admin_id_check}.")
        bot.reply_to(message, f"✅ sub removed for `{sub_user_id_remove}`.")
        try: bot.send_message(sub_user_id_remove, "ℹ️ your premium was removed.")
        except Exception as e: logger.error(f"Failed to notify {sub_user_id_remove} of sub removal: {e}")
    except ValueError:
        bot.reply_to(message, "❔ numbers only please — or /cancel.")
        msg = bot.send_message(message.chat.id, "💳 Enter User ID to remove sub from, or /cancel.")
        bot.register_next_step_handler(msg, process_remove_subscription_id)
    except Exception as e: logger.error(f"Error processing remove sub: {e}", exc_info=True); bot.reply_to(message, "Error.")

def check_subscription_init_callback(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "🔍 send id to check sub\n/cancel to quit")
    bot.register_next_step_handler(msg, process_check_subscription_id)

def process_check_subscription_id(message):
    admin_id_check = message.from_user.id
    if admin_id_check not in admin_ids: bot.reply_to(message, "\U0001F512 not allowed."); return
    if message.text.lower() == '/cancel': bot.reply_to(message, "✖️ cancelled."); return
    try:
        sub_user_id_check = int(message.text.strip()) # Renamed
        if sub_user_id_check <= 0: raise ValueError("ID must be positive")
        if sub_user_id_check in user_subscriptions:
            expiry_dt = user_subscriptions[sub_user_id_check].get('expiry')
            if expiry_dt:
                if expiry_dt > datetime.now():
                    days_left = (expiry_dt - datetime.now()).days
                    bot.reply_to(message, f"✅ `{sub_user_id_check}` has active sub\nends: {expiry_dt:%Y-%m-%d %H:%M:%S} ({days_left}d left)")
                else:
                    bot.reply_to(message, f"⏳ `{sub_user_id_check}` sub ended on {expiry_dt:%Y-%m-%d %H:%M:%S}.")
                    remove_subscription_db(sub_user_id_check) # Clean up
            else: bot.reply_to(message, f"❔ `{sub_user_id_check}` sub record incomplete.")
        else: bot.reply_to(message, f"ℹ️ User `{sub_user_id_check}` no active sub record.")
    except ValueError:
        bot.reply_to(message, "❔ numbers only please — or /cancel.")
        msg = bot.send_message(message.chat.id, "💳 Enter User ID to check, or /cancel.")
        bot.register_next_step_handler(msg, process_check_subscription_id)
    except Exception as e: logger.error(f"Error processing check sub: {e}", exc_info=True); bot.reply_to(message, "Error.")

# --- User Management Callbacks ---
def user_management_callback(call):
    bot.answer_callback_query(call.id)
    try:
        bot.edit_message_text("👥 User Management\nSelect action:", call.message.chat.id, 
                              call.message.message_id, reply_markup=create_user_management_menu())
    except Exception as e: logger.error(f"Error showing user management menu: {e}")

def ban_user_callback(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "⛔ send id + reason\ne.g. `12345678 spamming`\n/cancel to quit")
    bot.register_next_step_handler(msg, process_ban_user)

def process_ban_user(message):
    admin_id = message.from_user.id
    if admin_id not in admin_ids: bot.reply_to(message, "\U0001F512 not allowed."); return
    
    if message.text.lower() == '/cancel':
        bot.reply_to(message, "✖️ cancelled.")
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "❔ send: `user_id reason`\ne.g. `12345678 spamming`")
            return
        
        user_id = int(parts[0])
        reason = ' '.join(parts[1:])
        
        if user_id <= 0: raise ValueError("ID must be positive")
        if user_id == OWNER_ID: bot.reply_to(message, "👑 can't ban the owner."); return
        if user_id in admin_ids: bot.reply_to(message, "🛡️ can't ban staff."); return
        
        if ban_user_db(user_id, reason, admin_id):
            bot.reply_to(message, f"⛔ banned `{user_id}`\nreason: {reason}")
            # Stop all scripts for banned user
            for file_name, _ in user_files.get(user_id, []):
                script_key = f"{user_id}_{file_name}"
                if script_key in bot_scripts:
                    kill_process_tree(bot_scripts[script_key])
                    del bot_scripts[script_key]
            
            try:
                bot.send_message(user_id, f"⛔ you're restricted from this bot.\nreason: {reason}")
            except Exception as e:
                logger.error(f"Failed to notify banned user {user_id}: {e}")
        else:
            bot.reply_to(message, "💥 ban failed.")
            
    except ValueError:
        bot.reply_to(message, "❔ invalid id — numbers only.")
    except Exception as e:
        logger.error(f"Error banning user: {e}", exc_info=True)
        bot.reply_to(message, f"💥 error: {e}")

def unban_user_callback(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "✅ send id to unban\n/cancel to quit")
    bot.register_next_step_handler(msg, process_unban_user)

def process_unban_user(message):
    admin_id = message.from_user.id
    if admin_id not in admin_ids: bot.reply_to(message, "\U0001F512 not allowed."); return
    
    if message.text.lower() == '/cancel':
        bot.reply_to(message, "✖️ cancelled.")
        return
    
    try:
        user_id = int(message.text.strip())
        if user_id <= 0: raise ValueError("ID must be positive")
        
        if user_id not in banned_users:
            bot.reply_to(message, f"ℹ️ `{user_id}` isn't banned.")
            return
        
        if unban_user_db(user_id):
            bot.reply_to(message, f"✅ unbanned `{user_id}`.")
            try:
                bot.send_message(user_id, "✅ you're back! restriction lifted.")
            except Exception as e:
                logger.error(f"Failed to notify unbanned user {user_id}: {e}")
        else:
            bot.reply_to(message, "💥 unban failed.")
            
    except ValueError:
        bot.reply_to(message, "❔ invalid id — numbers only.")
    except Exception as e:
        logger.error(f"Error unbanning user: {e}", exc_info=True)
        bot.reply_to(message, f"💥 error: {e}")

def user_info_callback(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "👤 send id to view info\n/cancel to quit")
    bot.register_next_step_handler(msg, process_user_info)

def process_user_info(message):
    admin_id = message.from_user.id
    if admin_id not in admin_ids: bot.reply_to(message, "\U0001F512 not allowed."); return
    
    if message.text.lower() == '/cancel':
        bot.reply_to(message, "✖️ cancelled.")
        return
    
    try:
        user_id = int(message.text.strip())
        if user_id <= 0: raise ValueError("ID must be positive")
        
        # Gather user information
        info_parts = []
        
        # Basic info
        info_parts.append(f"👤 **User ID:** `{user_id}`")
        
        # Status
        if user_id == OWNER_ID:
            info_parts.append("👑 **Status:** Developer")
        elif user_id in admin_ids:
            info_parts.append("🛡️ **Status:** Admin")
        elif user_id in banned_users:
            info_parts.append("🚫 **Status:** Banned")
        elif user_id in user_subscriptions:
            expiry = user_subscriptions[user_id].get('expiry')
            if expiry and expiry > datetime.now():
                days_left = (expiry - datetime.now()).days
                info_parts.append(f"⭐ **Status:** Premium (Expires in {days_left} days)")
            else:
                info_parts.append("🆓 **Status:** Free User (Expired subscription)")
        else:
            info_parts.append("🆓 **Status:** Free User")
        
        # Files
        file_count = get_user_file_count(user_id)
        file_limit = get_user_file_limit(user_id)
        info_parts.append(f"📁 **Files:** {file_count}/{file_limit if file_limit != float('inf') else 'Unlimited'}")
        
        # Custom limit
        if user_id in user_limits:
            info_parts.append(f"⚙️ **Custom Limit:** {user_limits[user_id]}")
        
        # Active scripts
        running_scripts = 0
        for file_name, _ in user_files.get(user_id, []):
            if is_bot_running(user_id, file_name):
                running_scripts += 1
        info_parts.append(f"🤖 **Running Scripts:** {running_scripts}")
        
        # Last seen (if in active users)
        if user_id in active_users:
            info_parts.append("🟢 **Status:** Active")
        
        info_text = "\n".join(info_parts)
        bot.reply_to(message, info_text, parse_mode='Markdown')
        
    except ValueError:
        bot.reply_to(message, "❔ invalid id — numbers only.")
    except Exception as e:
        logger.error(f"Error getting user info: {e}", exc_info=True)
        bot.reply_to(message, f"💥 error: {e}")

def all_users_callback(call):
    bot.answer_callback_query(call.id)
    try:
        if not active_users:
            bot.edit_message_text("👥 No active users yet.", call.message.chat.id, call.message.message_id)
            return
        
        users_list = list(active_users)
        chunk_size = 20
        total_pages = (len(users_list) + chunk_size - 1) // chunk_size
        
        # Create pagination
        current_page = 0
        display_users_list(call.message.chat.id, call.message.message_id, users_list, current_page, total_pages, chunk_size)
        
    except Exception as e:
        logger.error(f"Error displaying all users: {e}", exc_info=True)
        bot.answer_callback_query(call.id, "Error displaying users.", show_alert=True)

def display_users_list(chat_id, message_id, users_list, page, total_pages, chunk_size):
    start_idx = page * chunk_size
    end_idx = min(start_idx + chunk_size, len(users_list))
    
    user_chunk = users_list[start_idx:end_idx]
    
    message_text = f"👥 **Active Users** (Page {page + 1}/{total_pages})\n\n"
    for i, user_id in enumerate(user_chunk, start=start_idx + 1):
        status = ""
        if user_id == OWNER_ID: status = "👑"
        elif user_id in admin_ids: status = "🛡️"
        elif user_id in banned_users: status = "🚫"
        elif user_id in user_subscriptions and user_subscriptions[user_id].get('expiry', datetime.min) > datetime.now():
            status = "⭐"
        else: status = "🆓"
        
        message_text += f"{i}. `{user_id}` {status}\n"
    
    markup = types.InlineKeyboardMarkup(row_width=3)
    
    if total_pages > 1:
        page_buttons = []
        if page > 0:
            page_buttons.append(types.InlineKeyboardButton("⬅️ Previous", callback_data=f"users_page_{page-1}"))
        
        page_buttons.append(types.InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="noop"))
        
        if page < total_pages - 1:
            page_buttons.append(types.InlineKeyboardButton("Next ➡️", callback_data=f"users_page_{page+1}"))
        
        markup.row(*page_buttons)
    
    markup.row(types.InlineKeyboardButton("🔙 Back to User Management", callback_data='user_management'))
    
    try:
        bot.edit_message_text(message_text, chat_id, message_id, reply_markup=markup, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error editing users list: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('users_page_'))
def handle_users_page(call):
    if call.from_user.id not in admin_ids:
        bot.answer_callback_query(call.id, "\U0001F512 staff only.", show_alert=True)
        return
    
    try:
        page = int(call.data.split('_')[2])
        users_list = list(active_users)
        chunk_size = 20
        total_pages = (len(users_list) + chunk_size - 1) // chunk_size
        
        if 0 <= page < total_pages:
            bot.answer_callback_query(call.id)
            display_users_list(call.message.chat.id, call.message.message_id, users_list, page, total_pages, chunk_size)
    except Exception as e:
        logger.error(f"Error handling users page: {e}", exc_info=True)
        bot.answer_callback_query(call.id, "Error.", show_alert=True)

def set_user_limit_callback(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "🔧 send: `user_id limit`\ne.g. `12345678 50`\n/cancel to quit")
    bot.register_next_step_handler(msg, process_set_user_limit)

def process_set_user_limit(message):
    admin_id = message.from_user.id
    if admin_id not in admin_ids: bot.reply_to(message, "\U0001F512 not allowed."); return
    
    if message.text.lower() == '/cancel':
        bot.reply_to(message, "✖️ cancelled.")
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 2: raise ValueError("Format: user_id limit")
        
        user_id = int(parts[0])
        limit = int(parts[1])
        
        if user_id <= 0 or limit <= 0: raise ValueError("ID and limit must be positive")
        
        if set_user_limit_db(user_id, limit, admin_id):
            bot.reply_to(message, f"✅ limit set: {limit} for `{user_id}`")
            try:
                bot.send_message(user_id, f"🔧 your slot limit is now {limit}")
            except Exception as e:
                logger.error(f"Failed to notify user {user_id}: {e}")
        else:
            bot.reply_to(message, "💥 couldn't set limit.")
            
    except ValueError as e:
        bot.reply_to(message, f"⚠️ Invalid input: {e}\nFormat: `user_id limit`")
    except Exception as e:
        logger.error(f"Error setting user limit: {e}", exc_info=True)
        bot.reply_to(message, f"💥 error: {e}")

def remove_user_limit_callback(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "🗑 send id to clear custom limit\n/cancel to quit")
    bot.register_next_step_handler(msg, process_remove_user_limit)

def process_remove_user_limit(message):
    admin_id = message.from_user.id
    if admin_id not in admin_ids: bot.reply_to(message, "\U0001F512 not allowed."); return
    
    if message.text.lower() == '/cancel':
        bot.reply_to(message, "✖️ cancelled.")
        return
    
    try:
        user_id = int(message.text.strip())
        if user_id <= 0: raise ValueError("ID must be positive")
        
        if user_id not in user_limits:
            bot.reply_to(message, f"ℹ️ no custom limit on `{user_id}`.")
            return
        
        if remove_user_limit_db(user_id):
            bot.reply_to(message, f"✅ custom limit cleared for `{user_id}`")
            try:
                bot.send_message(user_id, "🔧 custom limit cleared — default applies")
            except Exception as e:
                logger.error(f"Failed to notify user {user_id}: {e}")
        else:
            bot.reply_to(message, "💥 couldn't clear limit.")
            
    except ValueError:
        bot.reply_to(message, "❔ invalid id — numbers only.")
    except Exception as e:
        logger.error(f"Error removing user limit: {e}", exc_info=True)
        bot.reply_to(message, f"💥 error: {e}")

# --- Admin Settings Callbacks ---
def admin_settings_callback(call):
    bot.answer_callback_query(call.id)
    try:
        bot.edit_message_text("⚙️ Admin Settings\nSelect action:", call.message.chat.id, 
                              call.message.message_id, reply_markup=create_admin_settings_menu())
    except Exception as e: logger.error(f"Error showing admin settings: {e}")

def system_info_callback(call):
    bot.answer_callback_query(call.id)
    try:
        # Get system information
        import platform
        
        info_parts = []
        
        # Bot info
        info_parts.append("🤖 **Bot Information:**")
        info_parts.append(f"• Python: {platform.python_version()}")
        info_parts.append(f"• Platform: {platform.platform()}")
        info_parts.append(f"• Uptime: {time.strftime('%H:%M:%S', time.gmtime(time.time() - psutil.boot_time()))}")
        
        # System info
        info_parts.append("\n💻 **System Information:**")
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            info_parts.append(f"• CPU Usage: {cpu_percent}%")
            info_parts.append(f"• Memory: {memory.percent}% used ({memory.used//1024//1024}MB/{memory.total//1024//1024}MB)")
            info_parts.append(f"• Disk: {disk.percent}% used ({disk.used//1024//1024}MB/{disk.total//1024//1024}MB)")
        except Exception as e:
            info_parts.append(f"• System stats error: {str(e)}")
        
        # Bot stats
        info_parts.append("\n📊 **Bot Statistics:**")
        info_parts.append(f"• Active Users: {len(active_users)}")
        info_parts.append(f"• Running Scripts: {len(bot_scripts)}")
        info_parts.append(f"• Total Files: {sum(len(files) for files in user_files.values())}")
        info_parts.append(f"• Bot Status: {'🔒 Locked' if bot_locked else '🔓 Unlocked'}")
        
        info_text = "\n".join(info_parts)
        
        bot.edit_message_text(info_text, call.message.chat.id, call.message.message_id, 
                              reply_markup=create_admin_settings_menu(), parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error showing system info: {e}", exc_info=True)
        bot.answer_callback_query(call.id, "Error showing system info.", show_alert=True)

def bot_performance_callback(call):
    bot.answer_callback_query(call.id)
    try:
        # Calculate performance metrics
        performance_parts = []
        
        # Script performance
        running_scripts = len(bot_scripts)
        total_files = sum(len(files) for files in user_files.values())
        
        performance_parts.append("📈 **Bot Performance Metrics:**")
        performance_parts.append(f"• Running Scripts: {running_scripts}")
        performance_parts.append(f"• Total Scripts: {total_files}")
        performance_parts.append(f"• Uptime Ratio: {running_scripts}/{total_files} ({running_scripts/total_files*100:.1f}% if total > 0)")
        
        # Resource usage
        try:
            bot_process = psutil.Process()
            memory_usage = bot_process.memory_info().rss / 1024 / 1024  # MB
            cpu_usage = bot_process.cpu_percent(interval=0.5)
            
            performance_parts.append(f"\n💾 **Resource Usage:**")
            performance_parts.append(f"• Memory: {memory_usage:.1f} MB")
            performance_parts.append(f"• CPU: {cpu_usage:.1f}%")
        except Exception as e:
            performance_parts.append(f"\n⚠️ Resource stats error: {str(e)}")
        
        # Database stats
        performance_parts.append(f"\n🗄️ **Database:**")
        performance_parts.append(f"• Active Users: {len(active_users)}")
        performance_parts.append(f"• Subscriptions: {len(user_subscriptions)}")
        performance_parts.append(f"• Banned Users: {len(banned_users)}")
        performance_parts.append(f"• Custom Limits: {len(user_limits)}")
        
        performance_text = "\n".join(performance_parts)
        
        bot.edit_message_text(performance_text, call.message.chat.id, call.message.message_id,
                              reply_markup=create_admin_settings_menu(), parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error showing performance: {e}", exc_info=True)
        bot.answer_callback_query(call.id, "Error showing performance.", show_alert=True)

def cleanup_files_callback(call):
    bot.answer_callback_query(call.id, "🧹 Cleaning up temporary files...")
    try:
        cleaned_dirs, cleaned_files, cleaned_temp, cleaned_web, killed_zombies = _perform_hosting_cleanup()
        result_msg = (f"🧹 **Cleanup Complete:**\n"
                      f"• Removed empty directories: {cleaned_dirs}\n"
                      f"• Cleared old log files: {cleaned_files}\n"
                      f"• Removed stale temp dirs: {cleaned_temp}\n"
                      f"• Removed stale web dirs: {cleaned_web}\n"
                      f"• Killed dead/zombie sessions: {killed_zombies}")
        bot.edit_message_text(result_msg, call.message.chat.id, call.message.message_id,
                              reply_markup=create_admin_settings_menu(), parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error during cleanup: {e}", exc_info=True)
        bot.edit_message_text(f"🧹 cleanup problem: {e}", call.message.chat.id, call.message.message_id)

def stop_all_scripts_callback(call):
    bot.answer_callback_query(call.id)
    stopped = _stop_all_scripts()
    txt = f"⏹ stopped **{stopped}** hosted process(es)."
    try:
        bot.edit_message_text(txt, call.message.chat.id, call.message.message_id,
                              reply_markup=create_admin_settings_menu(), parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error in stop_all callback: {e}")

def storage_info_callback(call):
    bot.answer_callback_query(call.id)
    try:
        call.message.from_user = call.from_user
    except Exception: pass
    _logic_owner_storage(call.message)

def reboot_bot_callback(call):
    bot.answer_callback_query(call.id)
    try:
        call.message.from_user = call.from_user
    except Exception: pass
    try:
        _logic_owner_reboot(call.message)
    except Exception as e:
        logger.error(f"Error in reboot callback: {e}")
        try:
            bot.edit_message_text(f"❌ reboot problem: {e}", call.message.chat.id, call.message.message_id)
        except Exception: pass

def install_logs_callback(call):
    bot.answer_callback_query(call.id)
    try:
        with DB_LOCK:
            conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
            c = conn.cursor()
            c.execute('SELECT user_id, module_name, package_name, status, install_date FROM install_logs ORDER BY install_date DESC LIMIT 20')
            logs = c.fetchall()
            conn.close()
        
        if not logs:
            bot.edit_message_text("📋 **No installation logs found**", call.message.chat.id, 
                                  call.message.message_id, reply_markup=create_admin_settings_menu())
            return
        
        log_text = "📋 **Recent Installation Logs (Last 20):**\n\n"
        for user_id, module_name, package_name, status, install_date in logs:
            status_icon = "✅" if status == "success" else "❌" if status == "failed" else "⚠️"
            log_text += f"{status_icon} `{user_id}`: {module_name} -> {package_name}\n"
            log_text += f"   📅 {install_date[:19]}\n\n"
        
        bot.edit_message_text(log_text, call.message.chat.id, call.message.message_id,
                              reply_markup=create_admin_settings_menu(), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error showing install logs: {e}", exc_info=True)
        bot.answer_callback_query(call.id, "Error showing logs.", show_alert=True)

def admin_install_callback(call):
    bot.answer_callback_query(call.id)
    _logic_admin_install(call.message)

# --- Mandatory Channels Callbacks ---
def manage_mandatory_channels_callback(call):
    """Handle mandatory channels management request"""
    bot.answer_callback_query(call.id)
    try:
        bot.edit_message_text("\U0001F4E1 required channels\nchoose an action:",
                              call.message.chat.id, call.message.message_id, 
                              reply_markup=create_mandatory_channels_menu())
    except Exception as e:
        logger.error(f"Error showing channel management menu: {e}")

def add_mandatory_channel_callback(call):
    """Add new mandatory channel"""
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "📢 Send channel ID or username (example: @channel_username or -1001234567890)\n/cancel to cancel")
    bot.register_next_step_handler(msg, process_add_channel)

def process_add_channel(message):
    """Process channel addition"""
    admin_id = message.from_user.id
    if admin_id not in admin_ids:
        bot.reply_to(message, "\U0001F512 not allowed.")
        return
        
    if message.text and message.text.lower() == '/cancel':
        bot.reply_to(message, "❌ Channel addition cancelled.")
        return
        
    channel_identifier = message.text.strip()
    
    try:
        # Get channel info
        chat = bot.get_chat(channel_identifier)
        channel_id = str(chat.id)
        channel_username = f"@{chat.username}" if chat.username else ""
        channel_name = chat.title
        
        # Ensure bot is admin in the channel
        try:
            bot_member = bot.get_chat_member(channel_id, bot.get_me().id)
            if bot_member.status not in ['administrator', 'creator']:
                bot.reply_to(message, f"❌ Bot is not admin in the channel! Must be promoted first.")
                return
        except Exception as e:
            bot.reply_to(message, f"❌ Bot is not admin in the channel or cannot access it!")
            return
            
        # Save channel to database
        if save_mandatory_channel(channel_id, channel_username, channel_name, admin_id):
            bot.reply_to(message, f"✅ Mandatory channel added:\n**{channel_name}**\n{channel_username or channel_id}")
        else:
            bot.reply_to(message, "❌ Failed to add channel. Try again.")
            
    except Exception as e:
        logger.error(f"Error adding channel: {e}")
        bot.reply_to(message, f"❌ Error adding channel: {str(e)}")

def remove_mandatory_channel_callback(call):
    """Remove mandatory channel"""
    if not mandatory_channels:
        bot.answer_callback_query(call.id, "❌ No mandatory channels.", show_alert=True)
        return
        
    bot.answer_callback_query(call.id)
    
    markup = types.InlineKeyboardMarkup()
    for channel_id, channel_info in mandatory_channels.items():
        channel_name = channel_info.get('name', 'Unknown')
        button_text = f"🗑️ {channel_name}"
        markup.add(types.InlineKeyboardButton(button_text, callback_data=f'remove_channel_{channel_id}'))
    
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data='manage_mandatory_channels'))
    
    try:
        bot.edit_message_text("\U0001F5D1 pick a channel to remove:",
                              call.message.chat.id, call.message.message_id, 
                              reply_markup=markup)
    except Exception as e:
        logger.error(f"Error showing remove channel menu: {e}")

def process_remove_channel(call):
    """Process channel removal"""
    channel_id = call.data.replace('remove_channel_', '')
    
    if channel_id in mandatory_channels:
        channel_name = mandatory_channels[channel_id].get('name', 'Unknown')
        if remove_mandatory_channel_db(channel_id):
            bot.answer_callback_query(call.id, f"✅ Channel deleted: {channel_name}")
            try:
                bot.edit_message_text(f"✅ Mandatory channel deleted: **{channel_name}**",
                                      call.message.chat.id, call.message.message_id,
                                      reply_markup=create_mandatory_channels_menu(), parse_mode='Markdown')
            except Exception as e:
                logger.error(f"Error updating message after channel removal: {e}")
        else:
            bot.answer_callback_query(call.id, "❌ Failed to delete channel.", show_alert=True)
    else:
        bot.answer_callback_query(call.id, "❌ Channel not found.", show_alert=True)

def list_mandatory_channels_callback(call):
    """Show list of mandatory channels"""
    bot.answer_callback_query(call.id)
    
    if not mandatory_channels:
        message_text = "📢 **No mandatory channels currently**"
    else:
        message_text = "📢 **Mandatory Channels:**\n\n"
        for channel_id, channel_info in mandatory_channels.items():
            channel_name = channel_info.get('name', 'Unknown')
            channel_username = channel_info.get('username', 'No username')
            message_text += f"• **{channel_name}**\n  {channel_username or channel_id}\n\n"
    
    try:
        bot.edit_message_text(message_text, call.message.chat.id, call.message.message_id,
                              reply_markup=create_mandatory_channels_menu(), parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error listing channels: {e}")

def check_subscription_status_callback(call):
    """Check subscription status"""
    user_id = call.from_user.id
    is_subscribed, not_joined = check_mandatory_subscription(user_id)
    
    if is_subscribed or user_id in admin_ids:
        bot.answer_callback_query(call.id, "✅ You are subscribed to all required channels!", show_alert=True)
        # Show main menu
        try:
            _logic_send_welcome(call.message)
        except:
            back_to_main_callback(call)
    else:
        bot.answer_callback_query(call.id, "❌ You haven't joined all required channels yet!", show_alert=True)
        # Update the subscription message
        subscription_message, markup = create_subscription_check_message(not_joined)
        try:
            bot.edit_message_text(subscription_message, call.message.chat.id, 
                                  call.message.message_id, reply_markup=markup, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Error updating subscription message: {e}")

# --- Security Approval Callbacks ---
def process_approve_file(call):
    """Process admin approval for file"""
    data_parts = call.data.split('_')
    if len(data_parts) < 4:
        bot.answer_callback_query(call.id, "❌ Invalid data.", show_alert=True)
        return
        
    user_id = int(data_parts[2])
    file_name = '_'.join(data_parts[3:])
    
    user_folder = get_user_folder(user_id)
    file_path = os.path.join(user_folder, file_name)
    
    if not os.path.exists(file_path):
        bot.answer_callback_query(call.id, "❌ File not found.", show_alert=True)
        return
    
    file_ext = os.path.splitext(file_name)[1].lower()
    
    try:
        # Process the approved file
        if file_ext == '.js':
            handle_js_file(file_path, user_id, user_folder, file_name, call.message)
        elif file_ext == '.py':
            handle_py_file(file_path, user_id, user_folder, file_name, call.message)
        
        bot.answer_callback_query(call.id, "✅ File approved!")
        bot.edit_message_text(f"✅ File `{file_name}` approved for user `{user_id}`",
                              call.message.chat.id, call.message.message_id)
        
        # Notify user
        try:
            bot.send_message(user_id, f"✅ Your file `{file_name}` has been approved and started.")
        except Exception as e:
            logger.error(f"Failed to notify user {user_id}: {e}")
            
    except Exception as e:
        logger.error(f"Error processing approved file: {e}")
        bot.answer_callback_query(call.id, "❌ Error processing file.", show_alert=True)

def process_reject_file(call):
    """Process admin rejection for file"""
    data_parts = call.data.split('_')
    if len(data_parts) < 4:
        bot.answer_callback_query(call.id, "❌ Invalid data.", show_alert=True)
        return
        
    user_id = int(data_parts[2])
    file_name = '_'.join(data_parts[3:])
    
    user_folder = get_user_folder(user_id)
    file_path = os.path.join(user_folder, file_name)
    
    # Delete the file
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception as e:
            logger.error(f"Error deleting rejected file: {e}")
    
    bot.answer_callback_query(call.id, "❌ File rejected!")
    bot.edit_message_text(f"❌ File `{file_name}` rejected for user `{user_id}`",
                          call.message.chat.id, call.message.message_id)
    
    # Notify user
    try:
        bot.send_message(user_id, f"❌ Your file `{file_name}` has been rejected for security reasons.")
    except Exception as e:
        logger.error(f"Failed to notify user {user_id}: {e}")

def process_approve_zip(call):
    """Process admin approval for ZIP file"""
    data_parts = call.data.split('_')
    if len(data_parts) < 4:
        bot.answer_callback_query(call.id, "❌ Invalid data.", show_alert=True)
        return
        
    user_id = int(data_parts[2])
    file_name = '_'.join(data_parts[3:])
    
    # Check if we have stored file content
    if user_id in pending_zip_files and file_name in pending_zip_files[user_id]:
        file_content = pending_zip_files[user_id][file_name]
        user_folder = get_user_folder(user_id)
        temp_dir = None
        
        try:
            temp_dir = tempfile.mkdtemp(prefix=f"user_{user_id}_zip_approve_")
            zip_path = os.path.join(temp_dir, file_name)
            
            # Save the file content
            with open(zip_path, 'wb') as f:
                f.write(file_content)
            
            # Process the ZIP file
            process_zip_file(zip_path, user_id, user_folder, file_name, call.message, temp_dir)
            
            # Clean up pending files
            if user_id in pending_zip_files and file_name in pending_zip_files[user_id]:
                del pending_zip_files[user_id][file_name]
                if not pending_zip_files[user_id]:
                    del pending_zip_files[user_id]
            
            bot.answer_callback_query(call.id, "✅ Archive approved!")
            bot.edit_message_text(f"✅ Archive `{file_name}` approved for user `{user_id}`",
                                  call.message.chat.id, call.message.message_id)
            
            # Notify user
            try:
                bot.send_message(user_id, f"✅ Your archive `{file_name}` has been approved and processed.")
            except Exception as e:
                logger.error(f"Failed to notify user {user_id}: {e}")
                
        except Exception as e:
            logger.error(f"Error processing approved zip: {e}", exc_info=True)
            bot.answer_callback_query(call.id, "❌ Error processing archive.", show_alert=True)
        finally:
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                except Exception as e:
                    logger.error(f"Error cleaning temp dir: {e}")
    else:
        bot.answer_callback_query(call.id, "❌ File content not found. Ask user to re-upload.", show_alert=True)

def process_reject_zip(call):
    """Process admin rejection for ZIP file"""
    data_parts = call.data.split('_')
    if len(data_parts) < 4:
        bot.answer_callback_query(call.id, "❌ Invalid data.", show_alert=True)
        return
        
    user_id = int(data_parts[2])
    file_name = '_'.join(data_parts[3:])
    
    # Clean up pending files
    if user_id in pending_zip_files and file_name in pending_zip_files[user_id]:
        del pending_zip_files[user_id][file_name]
        if not pending_zip_files[user_id]:
            del pending_zip_files[user_id]
    
    bot.answer_callback_query(call.id, "❌ Archive rejected!")
    bot.edit_message_text(f"❌ Archive `{file_name}` rejected for user `{user_id}`",
                          call.message.chat.id, call.message.message_id)
    
    try:
        bot.send_message(user_id, f"❌ Your archive `{file_name}` has been rejected for security reasons.")
    except Exception as e:
        logger.error(f"Failed to notify user {user_id}: {e}")

# --- Cleanup Function ---
def cleanup():
    logger.warning("Shutdown. Cleaning up processes...")
    script_keys_to_stop = list(bot_scripts.keys()) 
    if not script_keys_to_stop: logger.info("No scripts running. Exiting."); return
    logger.info(f"Stopping {len(script_keys_to_stop)} scripts...")
    for key in script_keys_to_stop:
        if key in bot_scripts: logger.info(f"Stopping: {key}"); kill_process_tree(bot_scripts[key])
        else: logger.info(f"Script {key} already removed.")
    logger.warning("Cleanup finished.")
atexit.register(cleanup)

# --- Catch-all: stray text/messages -> show menu (registered LAST) ---
@bot.message_handler(func=lambda m: True, content_types=['text'])
def _logic_stray_text(message):
    _touch_user(message.from_user.id)
    t = (message.text or '').strip()
    uid = message.from_user.id
    if t.startswith('/'):
        bot.reply_to(message, "\U0001F937 "+_t("unknown command")+" \u2014 "+_t("use the buttons below")+" \U0001F447",
                     reply_markup=create_reply_keyboard_main_menu(uid))
    else:
        bot.reply_to(message, "\U0001F916 "+_t("i did not get that")+" \u2014 "+_t("use the buttons below")+" \U0001F447",
                     reply_markup=create_reply_keyboard_main_menu(uid))

# --- Main Execution ---
if __name__ == '__main__':
    logger.info("="*50 + "\n🤖 ZEX Hosting Bot Starting Up...\n" + f"🐍 Python: {sys.version.split()[0]}\n" +
                f"🔧 Base Dir: {BASE_DIR}\n📁 Upload Dir: {UPLOAD_BOTS_DIR}\n" +
                f"📊 Data Dir: {IROTECH_DIR}\n🔑 Owner ID: {OWNER_ID}\n🛡️ Admins: {len(admin_ids)}\n" +
                f"🚫 Banned Users: {len(banned_users)}\n📢 Mandatory Channels: {len(mandatory_channels)}\n" + "="*50)
    keep_alive()
    logger.info("🚀 Starting polling...")
    try:
        threading.Thread(target=_restore_after_reboot, daemon=True).start()
    except Exception as e:
        logger.error(f"Failed to start reboot restore thread: {e}")
    while True:
        try:
            bot.infinity_polling(logger_level=logging.INFO, timeout=60, long_polling_timeout=30)
        except requests.exceptions.ReadTimeout: 
            logger.warning("Polling ReadTimeout. Restarting in 5s...")
            time.sleep(5)
        except requests.exceptions.ConnectionError as ce: 
            logger.error(f"Polling ConnectionError: {ce}. Retrying in 15s...")
            time.sleep(15)
        except Exception as e:
            logger.critical(f"💥 Unrecoverable polling error: {e}", exc_info=True)
            logger.info("Restarting polling in 30s due to critical error...")
            time.sleep(30)
        finally: 
            logger.warning("Polling attempt finished. Will restart if in loop.")
            time.sleep(1)