from html import escape

from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from asgiref.sync import sync_to_async

from app_telegram.models import TGUser, ProjectParticipation
from tgbot.i18n import t, variants, region_label, role_label, rank_label, region_from_text
from ..keyboards import reply
from ..keyboards.known_buttons import is_menu_button_text
from ..services.photo_cache import send_cached_photo, file_cache_key


class ProfileUpdate(StatesGroup):
    waiting_for_name = State()
    waiting_for_photo = State()
    waiting_for_region = State()


def profile_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(t("btn_view_profile"))
    kb.add(t("btn_change_photo"), t("btn_change_name"))
    kb.add(t("btn_change_region"))
    kb.add(t("btn_back"))
    return kb


def _phone(phone: str) -> str:
    if not phone:
        return "—"
    return phone if phone.startswith("+") else f"+{phone}"


# --- 1. МЕНЮ ПРОФИЛЯ ---
async def profile_menu(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer(t("profile_menu_title"), reply_markup=profile_kb())


# --- 2. ПРОСМОТР ПРОФИЛЯ ---
async def view_my_profile(message: types.Message):
    user = await sync_to_async(TGUser.objects.filter(tg_id=message.from_user.id).first)()
    if not user:
        await message.answer(t("not_registered"))
        return

    attended = await sync_to_async(list)(
        ProjectParticipation.objects.filter(user=user, status='attended')
        .select_related('project').order_by('-project__date')
    )
    titles = "\n".join(f"✅ {escape(p.project.title)}" for p in attended) or t("profile_no_events")

    text = t(
        "profile_card",
        role=role_label(user.role),
        rank=rank_label(user.balance),
        balance=user.balance,
        events=len(attended),
        name=escape(user.fullname or "—"),
        phone=_phone(user.phone),
        region=region_label(user.region),
    )
    if user.region not in TGUser.Region.values:
        text += t("profile_region_warning")
    text += t("profile_events", list=titles)

    if user.photo:
        try:
            # Подпись к фото в Telegram — максимум 1024 символа
            short = len(text) <= 1024
            await send_cached_photo(
                message, file_cache_key(user.photo.path), lambda: open(user.photo.path, 'rb'),
                caption=text if short else None,
            )
            if not short:
                await message.answer(text)
            return
        except Exception:
            pass
    await message.answer(text)


# --- 3. ИМЯ ---
async def ask_for_name(message: types.Message):
    await message.answer(t("ask_new_name"), reply_markup=types.ReplyKeyboardRemove())
    await ProfileUpdate.waiting_for_name.set()


async def save_new_name(message: types.Message, state: FSMContext):
    if is_menu_button_text(message.text):
        await profile_menu(message, state)
        return
    new_name = message.text.strip()[:255]
    await sync_to_async(TGUser.objects.filter(tg_id=message.from_user.id).update)(fullname=new_name)
    await message.answer(t("name_saved", name=escape(new_name)))
    await profile_menu(message, state)


# --- 4. ФОТО ---
async def ask_for_photo(message: types.Message):
    await message.answer(t("ask_new_photo"))
    await ProfileUpdate.waiting_for_photo.set()


async def save_new_photo(message: types.Message, state: FSMContext):
    if not message.photo:
        await message.answer(t("send_photo"))
        return

    user = await sync_to_async(TGUser.objects.get)(tg_id=message.from_user.id)
    photo_name = f"users_photos/user_{user.tg_id}.jpg"
    await message.photo[-1].download(destination_file=f"media/{photo_name}")

    user.photo = photo_name
    await sync_to_async(user.save)(update_fields=['photo'])

    await message.answer(t("photo_saved"))
    await profile_menu(message, state)


# --- 5. РЕГИОН ---
async def ask_for_region(message: types.Message):
    await message.answer(t("ask_new_region"), reply_markup=reply.region_kb(with_back=True, row_width=2))
    await ProfileUpdate.waiting_for_region.set()


async def save_new_region(message: types.Message, state: FSMContext):
    if message.text in variants("btn_back"):
        await profile_menu(message, state)
        return

    region = region_from_text(message.text)
    if not region:
        await message.answer(t("use_buttons"))
        return

    await sync_to_async(TGUser.objects.filter(tg_id=message.from_user.id).update)(region=region)
    await message.answer(t("region_saved", region=region_label(region)))
    await profile_menu(message, state)


# --- 6. НАЗАД В ГЛАВНОЕ МЕНЮ ---
async def go_back_to_main(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer(t("back_to_main"), reply_markup=await reply.main_menu(message.from_user.id))


def register_profile(dp: Dispatcher):
    dp.register_message_handler(profile_menu, text=variants("btn_profile"), state="*")
    dp.register_message_handler(view_my_profile, text=variants("btn_view_profile"), state="*")
    dp.register_message_handler(ask_for_name, text=variants("btn_change_name"), state="*")
    dp.register_message_handler(ask_for_photo, text=variants("btn_change_photo"), state="*")
    dp.register_message_handler(ask_for_region, text=variants("btn_change_region"), state="*")

    dp.register_message_handler(save_new_name, state=ProfileUpdate.waiting_for_name)
    dp.register_message_handler(save_new_photo, content_types=['photo'], state=ProfileUpdate.waiting_for_photo)
    dp.register_message_handler(save_new_photo, state=ProfileUpdate.waiting_for_photo)
    dp.register_message_handler(save_new_region, state=ProfileUpdate.waiting_for_region)


def register_back(dp: Dispatcher):
    """Общая кнопка «Назад» → главное меню. Регистрируется ПОСЛЕ всех
    хендлеров состояний, чтобы «Назад» внутри выбора региона вёл в профиль."""
    dp.register_message_handler(go_back_to_main, text=variants("btn_back"), state="*")
