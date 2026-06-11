from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InputFile, InlineKeyboardMarkup, InlineKeyboardButton
from asgiref.sync import sync_to_async
from django.utils import timezone
from app_telegram.models import TGUser, EcoProject, ProjectParticipation

CHANNEL_ID = "@yashilqollar"


# --- КЛАВИАТУРЫ ---

def get_events_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(KeyboardButton("📅 Kelgusi tadbirlar"), KeyboardButton("📜 O'tgan tadbirlar"))
    kb.row(KeyboardButton("⬅️ Orqaga"))
    return kb

def get_registration_kb(project_id: int):
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton(
        text="✅ Ro'yxatdan o'tish",
        callback_data=f"reg_{project_id}"
    ))
    return kb


# --- ХЕНДЛЕРЫ ---

async def show_events_menu(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("<b>Tadbirlar bo'limi</b> ✨", reply_markup=get_events_menu(), parse_mode="HTML")


async def list_upcoming_events(message: types.Message, state: FSMContext):
    user = await sync_to_async(TGUser.objects.get)(tg_id=message.from_user.id)

    projects = await sync_to_async(list)(
        EcoProject.objects.filter(is_active=True, date__gt=timezone.now()).order_by('date')
    )

    if not projects:
        await message.answer("Hozircha yangi tadbirlar yo'q. 😊", reply_markup=get_events_menu())
        return

    is_subscribed = True
    try:
        member = await message.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=message.from_user.id)
        if member.status not in ['creator', 'administrator', 'member']:
            is_subscribed = False
    except Exception as e:
        print(f"Subscription check error: {e}")
        is_subscribed = True

    for p in projects:
        current_count = await sync_to_async(p.participants.exclude(status='rejected').count)()

        text = f"🚀 <b>{p.title}</b>\n\n"
        if p.description:
            text += f"{p.description}\n\n"
        text += f"👥 <b>Joylar:</b> {current_count}/{p.max_participants}\n"

        project_region = getattr(p, 'region', 'tashkent_s')
        tashkent_regions = ['tashkent_s', 'tashkent_v']

        if project_region in tashkent_regions:
            region_allowed = user.region in tashkent_regions
        else:
            region_allowed = user.region == project_region

        if not region_allowed:
            user_reg_name = dict(TGUser.Region.choices).get(user.region, user.region)
            text += (
                f"\n⚠️ <b>Diqqat:</b> Siz <b>{user_reg_name}</b> hududidansiz.\n"
                f"Ushbu tadbirda faqat mahalliy ko'ngillilar qatnasha oladi."
            )
            kb = get_events_menu()

        elif current_count >= p.max_participants:
            text += f"\n❌ <b>Afsuski, joylar tugadi.</b> Keyingi tadbirlarni kuzatib boring! 🌱"
            kb = get_events_menu()

        elif not is_subscribed:
            text += (
                f"\n⚠️ <b>Ro'yxatdan o'tish uchun avval kanalimizga a'zo bo'ling!</b>\n"
                f"Kanalga a'zo bo'lib, ushbu bo'limga qaytadan kiring. (📅 Kelgusi tadbirlar)"
            )
            kb = InlineKeyboardMarkup().add(
                InlineKeyboardButton(
                    text="📢 Kanalga a'zo bo'lish",
                    url=f"https://t.me/{CHANNEL_ID.replace('@', '')}"
                )
            )

        else:
            text += f"\n<i>Ro'yxatdan o'tish uchun pastdagi tugmani bosing 👇</i>"
            kb = get_registration_kb(p.id)  # ← передаём ID проекта

        if p.photo:
            try:
                await message.answer_photo(photo=InputFile(p.photo.path), caption=text, reply_markup=kb, parse_mode="HTML")
            except Exception:
                await message.answer(text, reply_markup=kb, parse_mode="HTML")
        else:
            await message.answer(text, reply_markup=kb, parse_mode="HTML")


async def process_registration(callback: types.CallbackQuery):
    await callback.answer()

    project_id = int(callback.data.split("_")[1])

    # Проверка подписки
    try:
        member = await callback.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=callback.from_user.id)
        if member.status not in ['creator', 'administrator', 'member']:
            await callback.message.answer(
                "⚠️ <b>Ro'yxatdan o'tish rad etildi!</b>\n\n"
                "Avval kanalimizga a'zo bo'ling.",
                reply_markup=InlineKeyboardMarkup().add(
                    InlineKeyboardButton(
                        text="📢 Kanalga a'zo bo'lish",
                        url=f"https://t.me/{CHANNEL_ID.replace('@', '')}"
                    )
                ),
                parse_mode="HTML"
            )
            return
    except Exception as e:
        print(f"Subscription check error during registration: {e}")

    user = await sync_to_async(TGUser.objects.get)(tg_id=callback.from_user.id)

    project = await sync_to_async(
        EcoProject.objects.filter(id=project_id, is_active=True).first
    )()

    if not project:
        await callback.message.answer("Bu tadbir endi mavjud emas.")
        return

    current_count = await sync_to_async(project.participants.exclude(status='rejected').count)()

    if current_count >= project.max_participants:
        await callback.message.answer(
            "❌ Kechirasiz, joylar qolmagan.",
            reply_markup=get_events_menu()
        )
        return

    part, created = await sync_to_async(ProjectParticipation.objects.get_or_create)(
        user=user, project=project
    )

    if created:
        await callback.message.answer(
            "✅ <b>Muvaffaqiyatli ro'yxatdan o'tdingiz!</b>\n\n"
            "Arizangiz ko'rib chiqilmoqda.",
            reply_markup=get_events_menu(),
            parse_mode="HTML"
        )
    else:
        await callback.message.answer("Siz allaqachon ariza topshirgansiz. 👍")


async def list_past_events(message: types.Message):
    past_events = await sync_to_async(lambda: list(
        EcoProject.objects.filter(date__lt=timezone.now()).order_by('-date')
    ))()

    if not past_events:
        await message.answer("📜 O'tgan tadbirlar arxivi hozircha bo'sh.")
        return

    for event in past_events:
        caption = f"<b>{event.title}</b>"
        if event.description:
            caption += f"\n\n{event.description}"

        if event.photo:
            try:
                await message.answer_photo(
                    photo=InputFile(event.photo.path),
                    caption=caption,
                    parse_mode="HTML"
                )
            except Exception as e:
                print(f"Photo error: {e}")
                await message.answer(caption, parse_mode="HTML")
        else:
            await message.answer(caption, parse_mode="HTML")


async def handle_back(message: types.Message, state: FSMContext):
    await state.finish()
    from ..keyboards import reply
    await message.answer("Asosiy menyu", reply_markup=reply.hi_there())


# --- РЕГИСТРАЦИЯ ---

def register_eco_clubs(dp: Dispatcher):
    dp.register_message_handler(show_events_menu, lambda m: "Tadbirlar" in m.text, state="*")
    dp.register_message_handler(list_upcoming_events, lambda m: "Kelgusi" in m.text, state="*")
    dp.register_message_handler(list_past_events, lambda m: "O'tgan" in m.text, state="*")
    dp.register_message_handler(handle_back, lambda m: "Orqaga" in m.text, state="*")
    dp.register_callback_query_handler(
        process_registration,
        lambda c: c.data and c.data.startswith("reg_"),
        state="*"
    )