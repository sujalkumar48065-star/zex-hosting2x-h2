#!/usr/bin/env python3
"""Render cron job target. Render invokes this every 5 minutes (see render.yaml).
It pings the web service's /health endpoint to stop Render's free web service
from sleeping, i.e. the inbuilt uptime robot for Render."""
import os
import sys
import urllib.request

url = (os.environ.get('HEALTH_URL') or 'https://hosting-panel.onrender.com/health').strip()
try:
    with urllib.request.urlopen(url, timeout=20) as resp:
        body = resp.read(200)
        print(f"PING {url} -> {resp.status} {body!r}")
        if resp.status != 200:
            sys.exit(1)
except Exception as exc:
    print(f"PING {url} FAILED: {exc}")
    sys.exit(1)
