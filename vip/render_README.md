# Deploy to Render (24/7)

Deploys the Telegram Hosting Panel to [Render](https://render.com) as a **webhook
web service** that stays awake 24/7.

## Files

| File            | Purpose                                                           |
|-----------------|-------------------------------------------------------------------|
| `render_app.py` | Flask webhook server + bot thread (Render entry point)            |
| `ping_health.py`| Cron-job target that pings `/health` (uptime robot)               |
| `render.yaml`   | Blueprint: web service + persistent disk + cron job               |

## 1. Push to a Git repo

Render deploys from a Git repo (GitHub/GitLab). Put the whole `vip/` folder in a
repo, and in the Render dashboard choose **New → Blueprint** and point it at the
repo. Render reads `render.yaml` and creates both services automatically.

## 2. Required env vars (set in Render dashboard → Environment)

| Variable             | Example                        | Notes                                       |
|----------------------|--------------------------------|---------------------------------------------|
| `HOSTING_BOT_TOKEN`  | `123456:ABC...`                | From @BotFather                              |
| `HOSTING_OWNER_ID`   | `8799679469`                   | Your Telegram ID (admin/owner)              |
| `PUBLIC_BASE_URL`    | `https://hosting-panel.onrender.com` | Full public URL of the web service    |
| `HOSTING_WEBHOOK_SECRET` | `some_long_random`         | Used in the `/webhook/<secret>` URL         |
| `SUB_LINK`           | `https://t.me/YourChannel`     | (optional) paid/subscription link           |

Optional TiDB failover (keeps project files even if the disk is wiped):
`TIDB1_HOST`, `TIDB1_USER`, `TIDB1_PASS` and `TIDB2_HOST`, `TIDB2_USER`,
`TIDB2_PASS`.

⚠ **Important:** the bot's webhook URL is `https://<PUBLIC_BASE_URL>/webhook/<secret>`.
Set `PUBLIC_BASE_URL` to the exact service URL (without trailing `/`). The bot sets
the webhook itself on startup, so no manual Telegram config is needed.

## 3. Keep it awake 24/7 (uptime robot)

Render free web services **sleep after ~15 min** with no inbound traffic. Two
layers handle this:

1. **Internal keep-alive thread** (in `render_app.py`): pings `/health` every 60s
   while the service is running. This keeps the bot loop alive during active use.
2. **Cron job** (`hosting-keepalive` in `render.yaml`): pings
   `/health` every 5 min from outside so the service never looks idle.

> **Note:** Render free **cron** jobs are limited to **once per day**. For true
> 24/7 wake-ups every 5 minutes, either upgrade the cron service to the paid
> `starter` plan (cheap) **or** create a free [UptimeRobot](https://uptimerobot.com)
> monitor that hits `https://<PUBLIC_BASE_URL>/health` every 5 min. Both work —
> pick whichever you prefer.

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
