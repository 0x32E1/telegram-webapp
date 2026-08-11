# Salon Beauty — Telegram Mini App (Demo)

The chat-flow bot rebuilt as a Telegram **Mini App**: a real web UI that opens inside Telegram
when the client taps a button, instead of tapping through inline keyboards.

**Stack:** FastAPI + aiosqlite (backend/API) · vanilla HTML/CSS/JS (frontend) · aiogram
(just for `/start` and push notifications) · APScheduler (reminders).

## Design

The UI is built around a "ticket stub" — a perforated appointment card, since that's literally
what a salon booking is. Deep burgundy/ink palette instead of the generic AI cream+terracotta
look, Fraunces (serif) for headings, Inter for UI text, IBM Plex Mono for times/prices (so
they read like a receipt printer). 5-step flow: service → specialist → date → time → confirm,
each step a fresh "ticket," ending in a stamped confirmation with a booking number.

## How it fits together

```
Client taps "Book" in the bot chat
        ↓
Telegram opens frontend/index.html inside the app (a Mini App webview)
        ↓
app.js calls the FastAPI backend, sending Telegram's initData with every request
        ↓
Backend verifies initData's signature (proves the request really came from Telegram)
        ↓
Same aiosqlite database + slot logic as the original bot
```

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env`:
- `BOT_TOKEN` — from @BotFather
- `ADMIN_IDS` — your Telegram user id(s), comma-separated (message @userinfobot to get yours)
- `WEBAPP_URL` — see below

Run it:

```bash
cd backend
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
```

### Getting a public HTTPS URL (required for real Telegram testing)

Telegram Mini Apps **must** be served over HTTPS — `http://localhost` will not open inside
Telegram. Easiest path for a demo:

```bash
ngrok http 8000
```

Copy the `https://xxxx.ngrok-free.app` URL ngrok gives you into `WEBAPP_URL` in `.env`,
restart the server, then message your bot and tap "Book now" from your phone.

### Reviewing the design without Telegram at all

Set `DEV_MODE=true` in `.env`, restart the server, and open `http://localhost:8000` directly
in a desktop browser. This skips Telegram's signature check and logs every request in as one
fixed demo user — it's for looking at the UI only. **Never leave `DEV_MODE=true` on anything
publicly reachable** — it disables the check that proves a request actually came from Telegram.

## What's demo data vs. what you'd customize per client

Same as before — swap the seed data in `backend/database.py` (`_SEED_SERVICES` /
`_SEED_EMPLOYEES`), working hours and reminder timing in `backend/config.py`, and salon
name/copy in `frontend/index.html` / `frontend/app.js`'s `UI` object.

## Project structure

```
backend/
  main.py             FastAPI app - API routes, serves the frontend, runs the bot + scheduler
  config.py           settings
  database.py         aiosqlite schema + queries (same booking logic as the chat-bot version)
  telegram_auth.py    verifies Telegram's initData signature
  bot_handlers.py     /start -> sends the "Book now" WebApp button
  notifier.py         shared Bot instance for admin alerts + reminders
  scheduler.py        background reminder job
  texts.py            RU/EN/UZ strings used server-side (bot + notifications)
frontend/
  index.html          Mini App shell
  style.css           the ticket/stub design system
  app.js              state machine driving the 5-step flow, talks to the API
```

## Not included (same as before, intentionally, for a demo)

Payment collection, a staff-side admin panel, multi-branch support — natural "phase 2" upsells.
