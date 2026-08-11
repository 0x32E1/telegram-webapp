import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "PUT_YOUR_TOKEN_HERE")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()]
DB_PATH = os.getenv("DB_PATH", "salon.db")

# Public https URL where this app is hosted (needed for the Telegram WebApp button).
# When testing locally without HTTPS, leave empty — /start will just say "not configured".
WEBAPP_URL = os.getenv("WEBAPP_URL", "")

# When true, skips Telegram initData signature verification and treats every request
# as a fixed demo user. ONLY for local design review in a plain browser — never enable
# this in anything reachable by the public.
DEV_MODE = os.getenv("DEV_MODE", "false").lower() == "true"

WORK_START_HOUR = 9
WORK_END_HOUR = 19
BOOKING_DAYS_AHEAD = 14
REMINDER_MINUTES_BEFORE = 60
