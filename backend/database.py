import datetime

import aiosqlite

import config

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    full_name TEXT,
    lang TEXT DEFAULT 'ru'
);

CREATE TABLE IF NOT EXISTS services (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name_ru TEXT, name_en TEXT, name_uz TEXT,
    duration_min INTEGER NOT NULL,
    price INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS employees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    specialty_ru TEXT, specialty_en TEXT, specialty_uz TEXT
);

CREATE TABLE IF NOT EXISTS employee_services (
    employee_id INTEGER NOT NULL,
    service_id INTEGER NOT NULL,
    FOREIGN KEY(employee_id) REFERENCES employees(id),
    FOREIGN KEY(service_id) REFERENCES services(id)
);

CREATE TABLE IF NOT EXISTS bookings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    service_id INTEGER NOT NULL,
    employee_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    time TEXT NOT NULL,
    status TEXT DEFAULT 'active',
    reminder_sent INTEGER DEFAULT 0,
    created_at TEXT NOT NULL
);
"""

_SEED_SERVICES = [
    ("Женская стрижка", "Women's haircut", "Ayollar soch turmagi", 60, 150000),
    ("Мужская стрижка", "Men's haircut", "Erkaklar soch turmagi", 30, 80000),
    ("Окрашивание", "Hair coloring", "Soch bo'yash", 120, 350000),
    ("Маникюр", "Manicure", "Manikyur", 60, 120000),
    ("Педикюр", "Pedicure", "Pedikyur", 60, 150000),
    ("Макияж", "Makeup", "Makiyaj", 45, 200000),
]

_SEED_EMPLOYEES = [
    ("Malika", "Парикмахер-стилист", "Hair stylist", "Soch ustasi", [0, 1, 2]),
    ("Dilnoza", "Мастер маникюра/педикюра", "Nail specialist", "Manikyur ustasi", [3, 4]),
    ("Kamila", "Визажист", "Makeup artist", "Vizajist", [5]),
    ("Aziza", "Парикмахер-стилист", "Hair stylist", "Soch ustasi", [0, 1, 2, 5]),
]


async def init_db():
    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.executescript(_SCHEMA)
        await db.commit()

        cur = await db.execute("SELECT COUNT(*) FROM services")
        (count,) = await cur.fetchone()
        if count == 0:
            for s in _SEED_SERVICES:
                await db.execute(
                    "INSERT INTO services (name_ru, name_en, name_uz, duration_min, price) VALUES (?,?,?,?,?)", s
                )
            await db.commit()
            for name, spec_ru, spec_en, spec_uz, service_idxs in _SEED_EMPLOYEES:
                cur = await db.execute(
                    "INSERT INTO employees (name, specialty_ru, specialty_en, specialty_uz) VALUES (?,?,?,?)",
                    (name, spec_ru, spec_en, spec_uz),
                )
                emp_id = cur.lastrowid
                for idx in service_idxs:
                    await db.execute(
                        "INSERT INTO employee_services (employee_id, service_id) VALUES (?, ?)", (emp_id, idx + 1)
                    )
            await db.commit()


async def upsert_user(user_id: int, username: str | None, full_name: str, lang: str | None = None):
    async with aiosqlite.connect(config.DB_PATH) as db:
        cur = await db.execute("SELECT lang FROM users WHERE user_id=?", (user_id,))
        row = await cur.fetchone()
        if row is None:
            await db.execute(
                "INSERT INTO users (user_id, username, full_name, lang) VALUES (?,?,?,?)",
                (user_id, username, full_name, lang or "ru"),
            )
        else:
            await db.execute("UPDATE users SET username=?, full_name=? WHERE user_id=?", (username, full_name, user_id))
        await db.commit()


async def set_user_lang(user_id: int, lang: str):
    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.execute("UPDATE users SET lang=? WHERE user_id=?", (lang, user_id))
        await db.commit()


async def get_user_lang(user_id: int) -> str:
    async with aiosqlite.connect(config.DB_PATH) as db:
        cur = await db.execute("SELECT lang FROM users WHERE user_id=?", (user_id,))
        row = await cur.fetchone()
        return row[0] if row else "ru"


async def get_services() -> list[dict]:
    async with aiosqlite.connect(config.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM services ORDER BY id")
        return [dict(r) for r in await cur.fetchall()]


async def get_service(service_id: int) -> dict | None:
    async with aiosqlite.connect(config.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM services WHERE id=?", (service_id,))
        row = await cur.fetchone()
        return dict(row) if row else None


async def get_employees_for_service(service_id: int) -> list[dict]:
    async with aiosqlite.connect(config.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """SELECT e.* FROM employees e JOIN employee_services es ON es.employee_id = e.id
               WHERE es.service_id = ? ORDER BY e.id""",
            (service_id,),
        )
        return [dict(r) for r in await cur.fetchall()]


async def get_employee(employee_id: int) -> dict | None:
    async with aiosqlite.connect(config.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM employees WHERE id=?", (employee_id,))
        row = await cur.fetchone()
        return dict(row) if row else None


async def get_booked_times(employee_id: int, date: str) -> set[str]:
    async with aiosqlite.connect(config.DB_PATH) as db:
        cur = await db.execute(
            "SELECT time FROM bookings WHERE employee_id=? AND date=? AND status='active'", (employee_id, date)
        )
        return {r[0] for r in await cur.fetchall()}


async def get_available_slots(employee_id: int, date: str, duration_min: int) -> list[str]:
    booked = await get_booked_times(employee_id, date)
    is_today = datetime.date.today().isoformat() == date
    now = datetime.datetime.now()

    day = datetime.date.fromisoformat(date)
    cursor = datetime.datetime.combine(day, datetime.time(config.WORK_START_HOUR, 0))
    closing = datetime.datetime.combine(day, datetime.time(config.WORK_END_HOUR, 0))
    step = datetime.timedelta(minutes=30)
    duration = datetime.timedelta(minutes=duration_min)

    slots = []
    while cursor + duration <= closing:
        time_str = cursor.strftime("%H:%M")
        if time_str not in booked and (not is_today or cursor > now):
            slots.append(time_str)
        cursor += step
    return slots


async def create_booking(user_id: int, service_id: int, employee_id: int, date: str, time: str) -> int:
    async with aiosqlite.connect(config.DB_PATH) as db:
        cur = await db.execute(
            """INSERT INTO bookings (user_id, service_id, employee_id, date, time, status, created_at)
               VALUES (?,?,?,?,?, 'active', ?)""",
            (user_id, service_id, employee_id, date, time, datetime.datetime.now().isoformat()),
        )
        await db.commit()
        return cur.lastrowid


async def get_active_bookings_for_user(user_id: int) -> list[dict]:
    async with aiosqlite.connect(config.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """SELECT b.*, s.name_ru, s.name_en, s.name_uz, s.price, e.name as employee_name
               FROM bookings b JOIN services s ON s.id = b.service_id JOIN employees e ON e.id = b.employee_id
               WHERE b.user_id=? AND b.status='active' ORDER BY b.date, b.time""",
            (user_id,),
        )
        return [dict(r) for r in await cur.fetchall()]


async def get_booking(booking_id: int) -> dict | None:
    async with aiosqlite.connect(config.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """SELECT b.*, s.name_ru, s.name_en, s.name_uz, s.duration_min, e.name as employee_name
               FROM bookings b JOIN services s ON s.id = b.service_id JOIN employees e ON e.id = b.employee_id
               WHERE b.id=?""",
            (booking_id,),
        )
        row = await cur.fetchone()
        return dict(row) if row else None


async def cancel_booking(booking_id: int):
    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.execute("UPDATE bookings SET status='cancelled' WHERE id=?", (booking_id,))
        await db.commit()


async def mark_reminder_sent(booking_id: int):
    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.execute("UPDATE bookings SET reminder_sent=1 WHERE id=?", (booking_id,))
        await db.commit()


async def get_pending_reminders() -> list[dict]:
    async with aiosqlite.connect(config.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """SELECT b.*, s.name_ru, s.name_en, s.name_uz, e.name as employee_name
               FROM bookings b JOIN services s ON s.id = b.service_id JOIN employees e ON e.id = b.employee_id
               WHERE b.status='active' AND b.reminder_sent=0"""
        )
        return [dict(r) for r in await cur.fetchall()]
