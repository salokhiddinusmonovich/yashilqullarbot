from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

from tgbot.i18n import t, LANG_BUTTON, LANG_NAMES, REGIONS, LANGS, current_lang


def hi_there(is_admin: bool = False, lang: str = None):
    # Самое нужное — сверху: мероприятия и QR.
    keyboard = [
        [KeyboardButton(text=t("btn_events", lang)), KeyboardButton(text=t("btn_qr", lang))],
        [KeyboardButton(text=t("btn_profile", lang)), KeyboardButton(text=t("btn_guide", lang))],
        [KeyboardButton(text=t("btn_about", lang)), KeyboardButton(text=t("btn_join", lang))],
        [KeyboardButton(text=t("btn_invite", lang)), KeyboardButton(text=LANG_BUTTON)],
    ]
    if is_admin:
        keyboard.append([KeyboardButton(text=t("btn_admin", lang))])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def auth_btn():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t("btn_register"))], [KeyboardButton(text=LANG_BUTTON)]],
        resize_keyboard=True, one_time_keyboard=True,
    )


def contact_btn():
    phone = KeyboardButton(text=t("btn_phone"), request_contact=True)
    return ReplyKeyboardMarkup(keyboard=[[phone]], resize_keyboard=True, one_time_keyboard=True)


def region_kb(with_back: bool = False, row_width: int = 1):
    lang_idx = LANGS.index(current_lang.get())
    kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=not with_back, row_width=row_width)
    kb.add(*[KeyboardButton(labels[lang_idx]) for labels in REGIONS.values()])
    if with_back:
        kb.add(KeyboardButton(t("btn_back")))
    return kb


def lang_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(*[InlineKeyboardButton(LANG_NAMES[code], callback_data=f"setlang:{code}") for code in LANGS])
    return kb


async def main_menu(tg_id: int):
    """Главное меню с кнопкой админки для тех, у кого is_admin."""
    from asgiref.sync import sync_to_async
    from app_telegram.models import TGUser
    is_admin = await sync_to_async(TGUser.objects.filter(tg_id=tg_id, is_admin=True).exists)()
    return hi_there(is_admin)
