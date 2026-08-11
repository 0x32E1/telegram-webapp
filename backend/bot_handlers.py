from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

import config
import database as db
from texts import t

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    await db.upsert_user(message.from_user.id, message.from_user.username, message.from_user.full_name)
    lang = message.from_user.language_code if message.from_user.language_code in ("ru", "en", "uz") else "ru"
    await db.set_user_lang(message.from_user.id, lang)

    if not config.WEBAPP_URL:
        await message.answer(t("not_configured", lang))
        return

    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=t("open_app_button", lang), web_app=WebAppInfo(url=config.WEBAPP_URL))]]
    )
    await message.answer(t("welcome", lang), reply_markup=kb)
