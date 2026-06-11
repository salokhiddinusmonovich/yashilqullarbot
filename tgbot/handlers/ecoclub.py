from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InputFile, InlineKeyboardMarkup, InlineKeyboardButton
from asgiref.sync import sync_to_async
from django.utils import timezone
from app_telegram.models import TGUser, EcoProject, ProjectParticipation

CHANNEL_ID = "@yashilqollar"


class EventStates(StatesGroup):
    waiting_for_registration = State()


# --- КЛАВИАТУРЫ ---

def get_events_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(KeyboardButton("📅 Kelgusi tadbirlar"), KeyboardButton("📜 O'tgan tadbirlar"))
    kb.row(KeyboardButton("⬅️ Orqaga"))
    return kb

def get_registration_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.add(KeyboardButton("✅ Ro'yxatdan o'tish"))
    kb.add(KeyboardButton("⬅️ Orqaga"))
    return kb


# --- ХЕНДЛЕРЫ ---

async def show_events_menu(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("<b>Tadbirlar bo'limi</b> ✨", reply_markup=get_events_menu(), parse_mode="HTML")


async def list_upcoming_events(message: types.Message, state: FSMContext):
    await state.finish()

    user = await sync_to_async(TGUser.objects.get)(tg_id=message.from_user.id)

    tashkent_regions = ['tashkent_s', 'tashkent_v']

    if user.region in tashkent_regions:
        projects = await sync_to_async(list)(
            EcoProject.objects.filter(
                is_active=True,
                date__gt=timezone.now(),
                region__in=tashkent_regions
            ).order_by('date')
        )
    else:
        projects = await sync_to_async(list)(
            EcoProject.objects.filter(
                is_active=True,
                date__gt=timezone.now(),
                region=user.region
            ).order_by('date')
        )

    if not projects:
        await message.answer(
            "😊 Sizning hududingizda hozircha yangi tadbirlar yo'q.\n"
            "Kuzatib boring, tez orada e'lon qilinadi!",
            reply_markup=get_events_menu()
        )
        return

    # Проверка подписки один раз
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

        if current_count >= p.max_participants:
            text += f"\n❌ <b>Afsuski, joylar tugadi.</b> Keyingi tadbirlarni kuzatib boring! 🌱"
            kb = get_events_menu()

        elif not is_subscribed:
            text += (
                f"\n⚠️ <b>Ro'yxatdan o'tish uchun avval kanalimizga a'zo bo'ling!</b>\n"
                f"Kanalga a'zo bo'lib, ushbu bo'limga qaytadan kiring."
            )
            kb = InlineKeyboardMarkup().add(
                InlineKeyboardButton(
                    text="📢 Kanalga a'zo bo'lish",
                    url=f"https://t.me/{CHANNEL_ID.replace('@', '')}"
                )
            )

        else:
            text += f"\n<i>Ro'yxatdan o'tish uchun pastdagi tugmani bosing 👇</i>"
            kb = get_registration_kb()
            # Сохраняем project_id в state для этого юзера
            await state.update_data(project_id=p.id)
            await EventStates.waiting_for_registration.set()

        if p.photo:
            try:
                await message.answer_photo(
                    photo=InputFile(p.photo.path),
                    caption=text,
                    reply_markup=kb,
                    parse_mode="HTML"
                )
            except Exception:
                await message.answer(text, reply_markup=kb, parse_mode="HTML")
        else:
            await message.answer(text, reply_markup=kb, parse_mode="HTML")


async def process_registration(message: types.Message, state: FSMContext):
    data = await state.get_data()
    project_id = data.get('project_id')

    if not project_id:
        await message.answer("Xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.", reply_markup=get_events_menu())
        await state.finish()
        return

    # Проверка подписки
    try:
        member = await message.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=message.from_user.id)
        if member.status not in ['creator', 'administrator', 'member']:
            await message.answer(
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

    user = await sync_to_async(TGUser.objects.get)(tg_id=message.from_user.id)

    project = await sync_to_async(
        EcoProject.objects.filter(id=project_id, is_active=True).first
    )()

    if not project:
        await message.answer("Bu tadbir endi mavjud emas.", reply_markup=get_events_menu())
        await state.finish()
        return

    # Двойная проверка лимита
    current_count = await sync_to_async(project.participants.exclude(status='rejected').count)()

    if current_count >= project.max_participants:
        await message.answer(
            "❌ Kechirasiz, joylar qolmagan.",
            reply_markup=get_events_menu()
        )
        await state.finish()
        return

    part, created = await sync_to_async(ProjectParticipation.objects.get_or_create)(
        user=user, project=project
    )

    await state.finish()

    if created:
        await message.answer(
            "✅ <b>Muvaffaqiyatli ro'yxatdan o'tdingiz!</b>\n\n"
            "Arizangiz ko'rib chiqilmoqda.",
            reply_markup=get_events_menu(),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            "Siz allaqachon ariza topshirgansiz. 👍",
            reply_markup=get_events_menu()
        )


async def list_past_events(message: types.Message, state: FSMContext):
    await state.finish()
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
    dp.register_message_handler(
        process_registration,
        lambda m: "Ro'yxatdan o'tish" in m.text,
        state=EventStates.waiting_for_registration
    )