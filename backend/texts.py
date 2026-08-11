TEXTS = {
    "reminder_text": {
        "ru": "⏰ Напоминание! Через час у вас запись:\n💇 {service}\n👤 {employee}\n🕐 {time}",
        "en": "⏰ Reminder! Your appointment is in 1 hour:\n💇 {service}\n👤 {employee}\n🕐 {time}",
        "uz": "⏰ Eslatma! Bir soatdan so'ng qabulingiz bor:\n💇 {service}\n👤 {employee}\n🕐 {time}",
    },
    "admin_new_booking": {
        "ru": "🆕 Новая запись!\n👤 Клиент: {client}\n💇 {service} — {employee}\n📅 {date} 🕐 {time}",
    },
    "admin_cancel_notice": {
        "ru": "⚠️ Клиент {client} отменил запись на {date} {time}.",
    },
    "welcome": {
        "ru": "✨ Добро пожаловать в Salon Beauty! Нажмите кнопку ниже, чтобы записаться.",
        "en": "✨ Welcome to Salon Beauty! Tap the button below to book.",
        "uz": "✨ Salon Beauty'ga xush kelibsiz! Yozilish uchun quyidagi tugmani bosing.",
    },
    "open_app_button": {
        "ru": "📅 Записаться",
        "en": "📅 Book now",
        "uz": "📅 Yozilish",
    },
    "not_configured": {
        "ru": "Мини-приложение ещё не настроено (нет WEBAPP_URL в .env).",
        "en": "The mini app isn't configured yet (WEBAPP_URL missing in .env).",
        "uz": "Mini ilova hali sozlanmagan (.env faylida WEBAPP_URL yo'q).",
    },
}


def t(key: str, lang: str, **kwargs) -> str:
    entry = TEXTS[key]
    text = entry.get(lang, entry.get("ru"))
    return text.format(**kwargs) if kwargs else text
