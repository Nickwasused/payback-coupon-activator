# Project Memory – payback-coupon-activator

## Overview
Automatically activates all PAYBACK coupons on https://www.payback.de/coupons using Playwright (headless Chromium) with cookies exported from a logged-in browser session. Runs in Docker with a small FastAPI web UI for status, cookie upload and manual trigger.

## Structure
- `src/main.py` – entry point: logging, APScheduler jobs (activation + hourly keepalive), starts uvicorn web server
- `src/coupon_activator.py` – `activate_batch()` (activates up to N coupons on one page), `keep_session_alive()`
- `src/browser.py` – `create_browser()` / `create_browser_context()` context managers, cookie loading
- `src/config.py` – settings from env vars
- `src/web/app.py` – FastAPI routes: `/`, `/api/status`, `/api/cookies` (upload), `/api/trigger`
- `src/web/state.py` – shared `app_state`, cookie metadata extraction (never reads cookie values)
- `src/web/static/index.html` – dashboard

## Current settings (docker-compose / .env)
```
TZ=Europe/Berlin
SCHEDULE_INTERVAL_HOURS=8
COOLDOWN_SECONDS=5
HEADLESS=true
RATE_LIMIT_BATCH_SIZE=44
RATE_LIMIT_PAUSE_HOURS=1
```
Web UI on port 8080. Cookies in `./data/cookies.json` (container: `/app/data/cookies.json`), logs in `./logs`.

## Rebuild / run
```
docker compose up -d --build
```

## Changes 2026-11-23
1. **Web UI not reachable after start** – `main()` awaited the first activation before starting uvicorn. With rate-limit pauses this blocked the web UI for hours. Fix: first activation now runs via `asyncio.create_task(...)` so the web server starts immediately.
2. **Browser stayed open during rate-limit pause** – Chromium was kept alive during the 1h `asyncio.sleep`. Fix: activation is split into batches. `run_activation()` in `main.py` loops: open browser → `activate_batch(page, RATE_LIMIT_BATCH_SIZE)` → close browser → sleep → repeat until `limit_reached` is False. `activate_all_coupons()` was removed/replaced by `activate_batch()`.

## Known quirks / ideas
- If exactly `RATE_LIMIT_BATCH_SIZE` coupons remain, one unnecessary pause happens before an empty final batch.
- The hourly keepalive job may still open a second browser while an activation pause is running (harmless, short).
- Progress log counts across batches (`Progress: x/total`); `total` is the count found in the first batch.
