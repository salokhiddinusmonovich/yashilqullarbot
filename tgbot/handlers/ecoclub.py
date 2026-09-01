from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from asgiref.sync import sync_to_async
from django.db.models import Count, Q
from django.utils import timezone
from app_telegram.models import TGUser, EcoProject, ProjectParticipation
from tgbot.services.photo_cache import send_cached_photo, file_cache_key

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

    # ИСПРАВЛЕНО: participants_count считаем одним annotate() сразу для
    # всех проектов, а не отдельным count()-запросом на КАЖДЫЙ проект в
    # цикле ниже — раньше список из 10 мероприятий делал 10 лишних
    # круговых походов в базу просто чтобы узнать "сколько людей записано".
    participants_count = Count('participants', filter=~Q(participants__status='rejected'))

    if user.region in tashkent_regions:
        projects = await sync_to_async(list)(
            EcoProject.objects.filter(
                is_active=True,
                date__gt=timezone.now(),
                region__in=tashkent_regions
            ).annotate(participants_count=participants_count).order_by('date')
        )
    else:
        projects = await sync_to_async(list)(
            EcoProject.objects.filter(
                is_active=True,
                date__gt=timezone.now(),
                region=user.region
            ).annotate(participants_count=participants_count).order_by('date')
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

    # ИСПРАВЛЕНО: одним запросом получаем id всех проектов, на которые
    # юзер уже подал заявку — чтобы для каждого проекта в списке сразу
    # знать "уже записан" без похода в базу на каждой итерации цикла.
    already_joined_ids = await sync_to_async(set)(
        ProjectParticipation.objects.filter(user=user, project__in=projects).values_list('project_id', flat=True)
    )

    for p in projects:
        current_count = p.participants_count

        text = f"🚀 <b>{p.title}</b>\n\n"
        if p.description:
            text += f"{p.description}\n\n"
        text += f"👥 <b>Joylar:</b> {current_count}/{p.max_participants}\n"

        if p.id in already_joined_ids:
            # ИСПРАВЛЕНО: уже зарегистрирован — говорим об этом сразу,
            # в самом списке мероприятий, даже не показывая кнопку регистрации.
            text += "\n✅ <b>Siz bu tadbirga allaqachon yozilgansiz.</b>"
            kb = get_events_menu()

        elif current_count >= p.max_participants:
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
            await state.update_data(project_id=p.id)
            await EventStates.waiting_for_registration.set()

        if p.photo:
            try:
                # Одна и та же фотка мероприятия шлётся ВСЕМ юзерам региона
                # при каждом заходе в раздел — кэш file_id экономит повторную
                # загрузку с диска и аплоад в Telegram на каждый показ.
                await send_cached_photo(
                    message, file_cache_key(p.photo.path), lambda path=p.photo.path: open(path, 'rb'),
                    caption=text, reply_markup=kb, parse_mode="HTML"
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

    user = await sync_to_async(TGUser.objects.get)(tg_id=message.from_user.id)

    # ИСПРАВЛЕНО: ПЕРВЫМ ДЕЛОМ проверяем в базе, не зарегистрирован ли
    # юзер уже на этот проект — это быстрый локальный запрос к БД.
    # Раньше здесь СНАЧАЛА шёл сетевой запрос get_chat_member (проверка
    # подписки на канал), и только потом — проверка "а не записан ли уже".
    # Из-за этого уже зарегистрированный юзер каждый раз ждал лишний
    # сетевой round-trip в Telegram API просто чтобы услышать "ты и так
    # уже записан". Теперь для уже записанных — мгновенный ответ, без
    # единого сетевого запроса.
    existing = await sync_to_async(
        ProjectParticipation.objects.filter(user=user, project_id=project_id).first
    )()
    if existing:
        await state.finish()
        await message.answer(
            "Siz allaqachon ariza topshirgansiz. 👍",
            reply_markup=get_events_menu()
        )
        return

    # Проверка подписки — только для НОВОЙ регистрации
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

    project = await sync_to_async(
        EcoProject.objects.filter(id=project_id, is_active=True).first
    )()

    if not project:
        await message.answer("Bu tadbir endi mavjud emas.", reply_markup=get_events_menu())
        await state.finish()
        return

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
        # ИЗМЕНЕНО: раньше тут просто говорили "ждите, вас проверят",
        # а ссылку на чат отправлял админ отдельно, вручную запуская
        # действие "approve_and_invite" в админке. Раз регистрация теперь
        # СРАЗУ approved (без промежуточного "Ожидание") — ссылку кидаем
        # сразу же, в этом самом сообщении, без ручного шага админа.
        if project.chat_link:
            text = (
                "✅ <b>Arizangiz qabul qilindi!</b>\n\n"
                f"Loyiha guruhiga qo'shiling: {project.chat_link}"
            )
        else:
            text = (
                "✅ <b>Arizangiz qabul qilindi!</b>\n\n"
                "Tez orada tafsilotlar bilan bog'lanamiz. 🌱"
            )
        await message.answer(text, reply_markup=get_events_menu(), parse_mode="HTML")
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
                await send_cached_photo(
                    message, file_cache_key(event.photo.path), lambda path=event.photo.path: open(path, 'rb'),
                    caption=caption, parse_mode="HTML"
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