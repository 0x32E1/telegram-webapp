import datetime
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

import config
import database as db
from notifier import bot
from texts import t

logger = logging.getLogger(__name__)


async def check_and_send_reminders():
    now = datetime.datetime.now()
    pending = await db.get_pending_reminders()

    for b in pending:
        try:
            appt_dt = datetime.datetime.strptime(f"{b['date']} {b['time']}", "%Y-%m-%d %H:%M")
        except ValueError:
            continue

        minutes_left = (appt_dt - now).total_seconds() / 60
        if minutes_left < 0:
            await db.mark_reminder_sent(b["id"])
            continue

        if minutes_left <= config.REMINDER_MINUTES_BEFORE:
            lang = await db.get_user_lang(b["user_id"])
            try:
                await bot.send_message(
                    b["user_id"],
                    t("reminder_text", lang, service=b[f"name_{lang}"], employee=b["employee_name"], time=b["time"]),
                )
            except Exception as e:
                logger.warning(f"Could not send reminder to {b['user_id']}: {e}")
            await db.mark_reminder_sent(b["id"])


def setup_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(check_and_send_reminders, "interval", minutes=1)
    return scheduler
