# Deploy to Render (24/7)

Deploys the Telegram Hosting Panel to [Render](https://render.com) as a **webhook
web service** that stays awake 24/7.

## Files

| File            | Purpose                                                           |
|-----------------|-------------------------------------------------------------------|
| `render_app.py` | Flask webhook server + bot thread (Render entry point)            |
| `render.yaml`   | Blueprint: web service + persistent disk (no cron job)            |

## 1. Push to a Git repo

Render deploys from a Git repo (GitHub/GitLab). Put the whole `vip/` folder in a
repo, and in the Render dashboard choose **New → Blueprint** and point it at the
repo. Render reads `render.yaml` and creates the web service automatically.

## 2. Required env vars (set in Render dashboard → Environment)

| Variable             | Example                        | Notes                                       |
|----------------------|--------------------------------|---------------------------------------------|
| `HOSTING_TOKEN_KEY`  | `LoaB...q04=`                 | Fernet key to decrypt the embedded bot token |
| `HOSTING_OWNER_ID`   | `8799679469`                  | Your Telegram ID (admin/owner)              |
| `PUBLIC_BASE_URL`    | `https://hosting-panel.onrender.com` | Full public URL of the web service    |
| `HOSTING_WEBHOOK_SECRET` | `some_long_random`         | Used in the `/webhook/<secret>` URL         |
| `SUB_LINK`           | `https://t.me/YourChannel`     | (optional) paid/subscription link           |

> The bot token is **never stored in plaintext.** `src/main.py` holds a Fernet
> **encrypted** token and decrypts it at startup using `HOSTING_TOKEN_KEY`.
> Generate a fresh key with:
> ```bash
> python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
> ```
> You **must** set that exact key in `HOSTING_TOKEN_KEY` or the bot can't start.
> (Optional) to override the embedded token without the key, set `HOSTING_BOT_TOKEN`.

Optional TiDB failover (keeps project files even if the disk is wiped):
`TIDB1_HOST`, `TIDB1_USER`, `TIDB1_PASS` and `TIDB2_HOST`, `TIDB2_USER`,
`TIDB2_PASS`.

⚠ **Important:** the bot's webhook URL is `https://<PUBLIC_BASE_URL>/webhook/<secret>`.
Set `PUBLIC_BASE_URL` to the exact service URL (without trailing `/`). The bot sets
the webhook itself on startup, so no manual Telegram config is needed.

## 3. Keep it awake 24/7 (uptime robot, no cron)

Render free web services **sleep after ~15 min** with no inbound traffic. This
setup deliberately does **not** use Render's cron service. Instead:

1. **Internal keep-alive thread** (in `render_app.py`): pings `/health` every 60s
   while the service is running.
2. **External uptime monitor** (free [UptimeRobot](https://uptimerobot.com)): create
   an HTTP(S) monitor that hits `https://<PUBLIC_BASE_URL>/health` ***every 5 min***.
   Each external hit counts as inbound traffic, so Render never marks the service
   idle and it stays awake 24/7 around the clock.

Render's built-in **Health Check Path** (`/health`) restarts the service
automatically if it ever becomes unresponsive, so a crash self-heals.

## 4. Health check

The web service exposes:
- `/` — "HOSTING BOT is running 24/7"
- `/health` — JSON status (`ok` / `starting` / `degraded`)
- `/webhook/<secret>` — Telegram update receiver (POST)

`Render → hosting-panel → Settings → Health Check Path` is set to `/health` in
`render.yaml`, so Render restarts the service if it ever becomes unresponsive.

## Proxy note

Render **can** reach `api.telegram.org` directly, so this setup does **not** route
through the HF proxy. If you ever need the proxy again, set `TG_API_PROXY` (e.g.
`https://tgproxy-pages.pages.dev`) in the dashboard.
