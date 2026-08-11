import asyncio
import contextlib
import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from aiogram import Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

import config
import database as db
from notifier import bot
from telegram_auth import verify_init_data, InitDataError
from texts import t
from scheduler import setup_scheduler
from bot_handlers import router as bot_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"

_background_tasks: list[asyncio.Task] = []


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    await db.init_db()

    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(bot_router)
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        _background_tasks.append(asyncio.create_task(dp.start_polling(bot)))
    except Exception as e:
        # Don't let a bad/unreachable BOT_TOKEN take down the API + frontend -
        # the Mini App itself doesn't need the bot connection, only /start and
        # notifications do. Common during local dev before a real token is set.
        logger.warning(f"Bot polling did not start ({e}). /start, admin alerts and reminders won't work until BOT_TOKEN is valid.")

    scheduler = setup_scheduler()
    scheduler.start()

    yield

    scheduler.shutdown(wait=False)
    for task in _background_tasks:
        task.cancel()
    await bot.session.close()


app = FastAPI(lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def _auth(init_data: str) -> dict:
    try:
        return verify_init_data(init_data)
    except InitDataError as e:
        raise HTTPException(status_code=401, detail=str(e))


def _lang(code: str | None) -> str:
    return code if code in ("ru", "en", "uz") else "ru"


# ---------- request bodies ----------

class BookingCreate(BaseModel):
    init_data: str
    service_id: int
    employee_id: int
    date: str
    time: str


class InitDataOnly(BaseModel):
    init_data: str


class LangSet(BaseModel):
    init_data: str
    lang: str


# ---------- API ----------

@app.get("/api/bootstrap")
async def bootstrap(init_data: str):
    """Called once when the Mini App opens: verifies the user, registers them,
    and returns everything the first screen needs."""
    user = _auth(init_data)
    await db.upsert_user(user["id"], user.get("username"), f"{user.get('first_name','')} {user.get('last_name','')}".strip())
    lang = await db.get_user_lang(user["id"])
    return {
        "user_id": user["id"],
        "lang": lang,
        "services": await db.get_services(),
        "booking_days_ahead": config.BOOKING_DAYS_AHEAD,
    }


@app.post("/api/lang")
async def set_lang(body: LangSet):
    user = _auth(body.init_data)
    if body.lang not in ("ru", "en", "uz"):
        raise HTTPException(400, "bad lang")
    await db.set_user_lang(user["id"], body.lang)
    return {"ok": True}


@app.get("/api/employees")
async def employees(service_id: int, init_data: str):
    _auth(init_data)
    service = await db.get_service(service_id)
    if not service:
        raise HTTPException(404, "service not found")
    return await db.get_employees_for_service(service_id)


@app.get("/api/slots")
async def slots(employee_id: int, service_id: int, date: str, init_data: str):
    _auth(init_data)
    service = await db.get_service(service_id)
    if not service:
        raise HTTPException(404, "service not found")
    return await db.get_available_slots(employee_id, date, service["duration_min"])


@app.post("/api/bookings")
async def create_booking(body: BookingCreate):
    user = _auth(body.init_data)
    service = await db.get_service(body.service_id)
    employee = await db.get_employee(body.employee_id)
    if not service or not employee:
        raise HTTPException(404, "service or employee not found")

    # Re-check the slot right before writing to close the race window between
    # the client loading slots and tapping "confirm".
    free_slots = await db.get_available_slots(body.employee_id, body.date, service["duration_min"])
    if body.time not in free_slots:
        raise HTTPException(409, "slot no longer available")

    booking_id = await db.create_booking(user["id"], body.service_id, body.employee_id, body.date, body.time)

    for admin_id in config.ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                t(
                    "admin_new_booking",
                    "ru",
                    client=f"@{user.get('username')}" if user.get("username") else user.get("first_name", "?"),
                    service=service["name_ru"],
                    employee=employee["name"],
                    date=body.date,
                    time=body.time,
                ),
            )
        except Exception:
            pass

    booking = await db.get_booking(booking_id)
    return booking


@app.get("/api/my-bookings")
async def my_bookings(init_data: str):
    user = _auth(init_data)
    return await db.get_active_bookings_for_user(user["id"])


@app.post("/api/bookings/{booking_id}/cancel")
async def cancel_booking(booking_id: int, body: InitDataOnly):
    user = _auth(body.init_data)
    booking = await db.get_booking(booking_id)
    if not booking or booking["user_id"] != user["id"]:
        raise HTTPException(404, "booking not found")

    await db.cancel_booking(booking_id)

    for admin_id in config.ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                t(
                    "admin_cancel_notice",
                    "ru",
                    client=f"@{user.get('username')}" if user.get("username") else user.get("first_name", "?"),
                    date=booking["date"],
                    time=booking["time"],
                ),
            )
        except Exception:
            pass

    return {"ok": True}


# Static frontend last, so /api/* above always takes priority over the catch-all.
app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
