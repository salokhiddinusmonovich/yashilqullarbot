"""
Ответы на частые вопросы — БЕЗ ИИ (бесплатно, мгновенно, без выдумок).

Вопрос нормализуется (узбекская кириллица → латиница, апострофы, регистр),
разбивается на слова и сравнивается с ключевыми словами каждой записи —
с учётом опечаток и окончаний. Нашлась уверенная запись — отвечаем ею;
не нашлась — вопрос уходит бесплатному ИИ (tgbot/services/ai.py), которому
весь этот FAQ передаётся как справочник (knowledge_text).

Добавить ответ: новая запись в FAQ — ключевые слова (uz латиницей, ru, en)
и ответ на трёх языках. Ключевое слово — начало слова («ro'yxat» ловит
«ro'yxatdan», «ro'yxatga»); фраза через пробел — все слова должны встретиться.
"""
import re
from difflib import SequenceMatcher

# ─────────────────────────── нормализация ───────────────────────────

_UZ_CYR = {
    "ў": "o'", "қ": "q", "ғ": "g'", "ҳ": "h", "ё": "yo", "ю": "yu", "я": "ya", "ш": "sh", "ч": "ch",
    "ц": "ts", "щ": "sh", "ж": "j", "й": "y", "х": "x", "а": "a", "б": "b", "в": "v", "г": "g",
    "д": "d", "е": "e", "з": "z", "и": "i", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o",
    "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f", "э": "e", "ъ": "'", "ь": "", "ы": "i",
}
_UZ_ONLY = set("ўқғҳ")
_APOS = re.compile(r"[ʻʼ‘’`´]")


def normalize(text: str) -> str:
    s = _APOS.sub("'", (text or "").lower())
    # узбекский кириллицей («паролни унутдим») → латиница; русский оставляем как есть
    if any(ch in _UZ_ONLY for ch in s) or _looks_uz_cyrillic(s):
        s = "".join(_UZ_CYR.get(ch, ch) for ch in s)
    return s


_UZ_CYR_MARKERS = ("қандай", "нима", "қаерда", "қачон", "керак", "мумкин", "қилиш", "бўл", "ўт", "ни ", "дан ", "га ", "лар")


def _looks_uz_cyrillic(s: str) -> bool:
    return any(m in s for m in _UZ_CYR_MARKERS) and not re.search(r"\b(как|где|что|почему|когда|не|я|мне|мой)\b", s)


def words(text: str) -> list[str]:
    return re.findall(r"[a-zа-яё0-9']+", normalize(text))


def _hit(stem: str, toks: list[str]) -> bool:
    for w in toks:
        if w.startswith(stem):
            return True
        # опечатки: сравниваем начало слова такой же длины
        if len(stem) >= 5 and SequenceMatcher(None, stem, w[:len(stem)]).ratio() >= 0.82:
            return True
    return False


# ─────────────────────────── база ответов ───────────────────────────
# kw — ключевые слова; weight 2 у фраз (несколько слов), 1 у одиночных.

FAQ = [
    {
        "id": "register_bot",
        "kw": ["ro'yxat", "ro'yxatdan o't", "qanday qo'shil", "a'zo bo'l", "регистрац", "зарегистр", "sign up", "register", "registration"],
        "uz": "📝 <b>Botda ro'yxatdan o'tish</b> (bir marta, ~1 daqiqa):\n1) /start → tilni tanlang\n2) «🆕 Yo'q, birinchi marta» ni bosing (saytda hisobingiz bo'lsa — «✅ Ha»)\n3) «📝 Ro'yxatdan o'tish» → 8 ta savol: ism, yosh, email, hudud, o'qish joyi, tajriba, rasm\n4) Telefon raqamni <b>«📱 Raqamni yuborish»</b> tugmasi bilan yuboring.\n\n❗ Bu hali tadbirga yozilish emas — tadbirga alohida yoziling.",
        "ru": "📝 <b>Регистрация в боте</b> (один раз, ~1 минута):\n1) /start → выберите язык\n2) «🆕 Нет, я здесь впервые» (если есть аккаунт на сайте — «✅ Да»)\n3) «📝 Регистрация» → 8 вопросов: имя, возраст, email, регион, учёба, опыт, фото\n4) Номер телефона — кнопкой <b>«📱 Отправить номер»</b>.\n\n❗ Это ещё не запись на мероприятие — на него записываются отдельно.",
        "en": "📝 <b>Signing up in the bot</b> (once, ~1 minute):\n1) /start → pick a language\n2) «🆕 No, I'm new here» (have a website account? — «✅ Yes»)\n3) «📝 Sign up» → 8 questions: name, age, email, region, studies, experience, photo\n4) Share your phone with the <b>«📱 Share my number»</b> button.\n\n❗ This is not an event sign-up yet — you join each event separately.",
    },
    {
        "id": "join_event",
        "kw": ["tadbirga yozil", "tadbirga qanday", "yozilaman", "yozilish", "qatnash", "записат", "запис на", "как попасть", "участвов", "join event", "join an event", "attend"],
        "uz": "🌱 <b>Tadbirga yozilish:</b>\n• Botda: <b>🌱 Tadbirlar → 📅 Kelgusi tadbirlar</b> → tadbirni tanlang → <b>«✅ Ro'yxatdan o'tish»</b>\n• Yoki ilovada: chap pastdagi <b>«Ilova»</b> → Tadbirlar → «Yozilish».\n\nYozilgach tadbir guruhiga qo'shiling. Tadbir kuni QR-kodingizni koordinatorga ko'rsating.\n📍 Faqat o'z hududingiz tadbirlariga yozilish mumkin.",
        "ru": "🌱 <b>Как записаться на мероприятие:</b>\n• В боте: <b>🌱 Мероприятия → 📅 Предстоящие</b> → выберите → <b>«✅ Записаться»</b>\n• Или в приложении: кнопка <b>«Ilova»</b> слева внизу → События → «Записаться».\n\nПосле записи вступите в группу мероприятия. В день мероприятия покажите QR-код координатору.\n📍 Записаться можно только на мероприятия своего региона.",
        "en": "🌱 <b>Joining an event:</b>\n• In the bot: <b>🌱 Events → 📅 Upcoming</b> → pick one → <b>«✅ Sign up»</b>\n• Or in the app: the <b>«Ilova»</b> button at the bottom left → Events → «Join».\n\nThen join the event group. On the day, show your QR code to the coordinator.\n📍 You can only join events in your own region.",
    },
    {
        "id": "qr",
        "kw": ["qr", "kod", "код", "qr-kod", "qr code", "skaner qil", "сканир"],
        "uz": "🌿 <b>QR-kod</b> — botdagi <b>«🌿 Mening QR-kodim»</b> tugmasi yoki ilovadagi <b>«QR»</b> bo'limi.\nTadbir kuni uni koordinatorga ko'rsating — skaner qilgach sizga <b>+10 ball</b> tushadi.\n💡 Ilovadagi QR internetsiz ham ochiladi. Ekran yorqinligini oshiring.",
        "ru": "🌿 <b>QR-код</b> — кнопка <b>«🌿 Мой QR-код»</b> в боте или раздел <b>«QR»</b> в приложении.\nВ день мероприятия покажите его координатору — после сканирования начислится <b>+10 баллов</b>.\n💡 QR в приложении открывается даже без интернета. Прибавьте яркость экрана.",
        "en": "🌿 <b>QR code</b> — the <b>«🌿 My QR code»</b> button in the bot or the <b>«QR»</b> tab in the app.\nShow it to the coordinator on the event day — you get <b>+10 points</b> after the scan.\n💡 The app's QR works offline too. Turn up screen brightness.",
    },
    {
        "id": "certificate",
        "kw": ["sertifikat", "сертификат", "certificate", "diplom", "грамот"],
        "uz": "🎓 <b>Sertifikat</b> tadbirdan keyingi kuni ertalab botga o'zi keladi (PDF). Barcha sertifikatlaringiz: /sertifikat yoki ilovada Profil → «Sertifikatlarim».\n❗ Faqat QR-kodi skaner qilinganlar (kelgani tasdiqlanganlar) sertifikat oladi.",
        "ru": "🎓 <b>Сертификат</b> приходит в бот сам на следующее утро после мероприятия (PDF). Все ваши сертификаты: /sertifikat или в приложении Профиль → «Мои сертификаты».\n❗ Сертификат получают только те, чей QR-код отсканирован (участие подтверждено).",
        "en": "🎓 Your <b>certificate</b> arrives in the bot automatically the morning after the event (PDF). All your certificates: /sertifikat or in the app Profile → «My certificates».\n❗ Only people whose QR code was scanned get a certificate.",
    },
    {
        "id": "points",
        "kw": ["ball", "балл", "points", "point", "reyting", "рейтинг", "daraja", "уровень", "level", "leaderboard"],
        "uz": "⭐ <b>Ballar:</b> har bir tadbirda QR-kodingiz skaner qilinganda <b>+10 ball</b>.\nBallaringiz, darajangiz va reytingdagi o'rningiz — ilovada (<b>«Ilova»</b> → Asosiy / Reyting).\n🛍 Tez orada ballarni Eko-do'konda sovg'alarga almashtirish mumkin bo'ladi.",
        "ru": "⭐ <b>Баллы:</b> <b>+10</b> за каждое мероприятие, когда отсканировали ваш QR-код.\nБаллы, уровень и место в рейтинге — в приложении (<b>«Ilova»</b> → Главная / Рейтинг).\n🛍 Скоро баллы можно будет обменять на подарки в Эко-магазине.",
        "en": "⭐ <b>Points:</b> <b>+10</b> for every event where your QR code is scanned.\nYour points, level and leaderboard place are in the app (<b>«Ilova»</b> → Home / Top).\n🛍 Soon you'll swap points for gifts in the Eco shop.",
    },
    {
        "id": "no_points",
        "kw": ["ball tushmadi", "ball kelmadi", "ball yo'q", "ball qo'shilmadi", "не начисл", "не пришли балл", "баллы не", "no points", "points not"],
        "uz": "🤔 Ball faqat <b>QR-kodingiz tadbirda skaner qilinganda</b> tushadi (+10). Skaner qilinmagan bo'lsa — tadbir koordinatoriga yozing, u sizni belgilab qo'yadi.\nKoordinatorlar: ilova → Reyting → «Jamoa».",
        "ru": "🤔 Баллы начисляются только когда <b>ваш QR-код отсканировали на мероприятии</b> (+10). Если не сканировали — напишите координатору мероприятия, он вас отметит.\nКоординаторы: приложение → Рейтинг → «Команда».",
        "en": "🤔 Points are added only when <b>your QR code is scanned at the event</b> (+10). If it wasn't — message the event coordinator, they can check you in.\nCoordinators: app → Top → «Team».",
    },
    {
        "id": "password",
        "kw": ["parol", "пароль", "password", "unutdim", "забыл", "forgot", "kira olmayapman", "не могу войти", "can't log in", "cannot login"],
        "uz": "🔑 <b>Parolni unutdingizmi?</b>\n• Botda /start → «✅ Ha, saytda ro'yxatdan o'tganman» → emailingiz → <b>«📧 Emailga kod yuborish»</b> — hisobingiz botga ulanadi, parol kerak emas.\n• Yangi parol: ilova → Profil → «Parol o'rnatish».\n• Saytga Telegram orqali ham kirish mumkin.",
        "ru": "🔑 <b>Забыли пароль?</b>\n• В боте /start → «✅ Да, я зарегистрирован на сайте» → ваш email → <b>«📧 Отправить код на email»</b> — аккаунт привяжется к боту, пароль не нужен.\n• Новый пароль: приложение → Профиль → «Задать пароль».\n• На сайт можно войти и через Telegram.",
        "en": "🔑 <b>Forgot your password?</b>\n• In the bot /start → «✅ Yes, I have a website account» → your email → <b>«📧 Send a code to my email»</b> — your account gets linked, no password needed.\n• New password: app → Profile → «Set password».\n• You can also log in to the website with Telegram.",
    },
    {
        "id": "email_taken",
        "kw": ["email band", "email mavjud", "почта занята", "email уже", "уже существует", "already exists", "email taken", "email is taken"],
        "uz": "📧 «Email band» — demak siz <b>saytda allaqachon ro'yxatdan o'tgansiz</b>. Qayta ro'yxatdan o'tmang: /start → «✅ Ha, saytda ro'yxatdan o'tganman» → emailingizni yozing → parol yoki emailga kelgan kod bilan tasdiqlang. Hisobingiz botga ulanadi.",
        "ru": "📧 «Email занят» значит, что вы <b>уже зарегистрированы на сайте</b>. Не регистрируйтесь заново: /start → «✅ Да, я зарегистрирован на сайте» → ваш email → подтвердите паролем или кодом из письма. Аккаунт привяжется к боту.",
        "en": "📧 «Email taken» means you <b>already have a website account</b>. Don't sign up again: /start → «✅ Yes, I have a website account» → your email → confirm with your password or the emailed code. Your account gets linked to the bot.",
    },
    {
        "id": "app",
        "kw": ["ilova", "prilojen", "приложен", "mini app", "miniapp", "app", "ilovani", "ochilmayapti"],
        "uz": "📱 <b>Ilova</b> (Mini App) — botning ichida: chat pastidagi chap tomondagi <b>«Ilova»</b> tugmasini bosing (yoki /app).\nU yerda: volontyor pasporti, tadbirlar, QR-kod, muhrlar, reyting, profilni tahrirlash.\nOchilmasa — Telegram'ni yangilang.",
        "ru": "📱 <b>Приложение</b> (Mini App) — прямо в боте: кнопка <b>«Ilova»</b> слева внизу чата (или /app).\nТам: паспорт волонтёра, мероприятия, QR-код, печати, рейтинг, редактирование профиля.\nНе открывается — обновите Telegram.",
        "en": "📱 <b>The app</b> (Mini App) lives inside the bot: tap <b>«Ilova»</b> at the bottom left of the chat (or /app).\nInside: volunteer passport, events, QR code, stamps, leaderboard, profile editing.\nWon't open? Update Telegram.",
    },
    {
        "id": "region",
        "kw": ["hudud", "viloyat", "регион", "область", "region", "hududni o'zgartir", "сменить регион"],
        "uz": "📍 <b>Hudud</b> — tadbirlar shu bo'yicha ko'rsatiladi. O'zgartirish: ilova → <b>Profil → «Tahrirlash»</b> → Hudud.\nFaqat o'z hududingiz tadbirlariga yozila olasiz (Toshkent shahri va viloyati — bitta).",
        "ru": "📍 <b>Регион</b> — по нему показываются мероприятия. Изменить: приложение → <b>Профиль → «Редактировать»</b> → Регион.\nЗаписываться можно только на мероприятия своего региона (Ташкент-город и область — одно целое).",
        "en": "📍 <b>Region</b> — events are shown by it. Change it: app → <b>Profile → «Edit»</b> → Region.\nYou can only join events in your region (Tashkent city and region count as one).",
    },
    {
        "id": "no_events",
        "kw": ["tadbir yo'q", "tadbirlar yo'q", "tadbir ko'rinmayapti", "нет мероприят", "не вижу мероприят", "no events", "can't see events"],
        "uz": "🗓 Tadbirlar <b>hududingiz bo'yicha</b> ko'rsatiladi. Ko'rinmasa:\n1) Profilda hududingiz to'g'ri ekanini tekshiring (ilova → Profil)\n2) Hozircha hududingizda yangi tadbir yo'q bo'lishi mumkin — e'lonlarni kanalimizda kuzating.",
        "ru": "🗓 Мероприятия показываются <b>по вашему региону</b>. Если не видно:\n1) Проверьте регион в профиле (приложение → Профиль)\n2) Возможно, в вашем регионе пока нет новых мероприятий — следите за анонсами в канале.",
        "en": "🗓 Events are shown <b>for your region</b>. If you see none:\n1) Check your region in the profile (app → Profile)\n2) There may be no new events in your region yet — watch our channel for announcements.",
    },
    {
        "id": "group",
        "kw": ["guruh", "группа", "группу", "group", "chat link", "havola"],
        "uz": "👥 <b>Tadbir guruhi</b> havolasi tadbirga yozilganingizda botdan keladi (ilovada — tadbir kartasida «Guruhga qo'shilish»). E'lonlar va sertifikatlar o'sha guruhda bo'ladi.",
        "ru": "👥 Ссылку на <b>группу мероприятия</b> бот присылает при записи (в приложении — кнопка «Вступить в группу» в карточке мероприятия). Анонсы и сертификаты — в этой группе.",
        "en": "👥 The <b>event group</b> link comes from the bot when you sign up (in the app — «Join the group» on the event card). Announcements and certificates are posted there.",
    },
    {
        "id": "bot_vs_event",
        "kw": ["farqi", "farq nima", "разница", "в чём разница", "difference", "ro'yxatdan o'tdim lekin", "зарегистрировался но"],
        "uz": "❗ <b>Botda ro'yxatdan o'tish</b> — bir marta (siz Yashil Qo'llar volontyorisiz).\n<b>Tadbirga yozilish</b> — har bir tadbirga alohida: 🌱 Tadbirlar → Kelgusi → «✅ Ro'yxatdan o'tish».",
        "ru": "❗ <b>Регистрация в боте</b> — один раз (вы стали волонтёром Yashil Qo'llar).\n<b>Запись на мероприятие</b> — на каждое отдельно: 🌱 Мероприятия → Предстоящие → «✅ Записаться».",
        "en": "❗ <b>Signing up in the bot</b> happens once (you're a Yashil Qo'llar volunteer).\n<b>Joining an event</b> is separate for each event: 🌱 Events → Upcoming → «✅ Sign up».",
    },
    {
        "id": "contact",
        "kw": ["koordinator", "координатор", "coordinator", "admin", "админ", "bog'lan", "связат", "contact", "kimga yozay", "кому написать", "yordam", "помощь", "help me"],
        "uz": "👥 <b>Kimga yozish:</b> hududingiz koordinatorlari — ilova → Reyting → <b>«Jamoa»</b> (u yerda ism va profil). Tadbir bo'yicha savollar — tadbir guruhida.",
        "ru": "👥 <b>Кому написать:</b> координаторы вашего региона — приложение → Рейтинг → <b>«Команда»</b> (там имена и профили). Вопросы по мероприятию — в его группе.",
        "en": "👥 <b>Who to contact:</b> your region's coordinators — app → Top → <b>«Team»</b> (names and profiles). Event questions — in the event group.",
    },
    {
        "id": "language",
        "kw": ["tilni", "til o'zgartir", "язык", "сменить язык", "language", "rus tili", "на русском"],
        "uz": "🌐 Til: menyudagi <b>«🌐 Til · Язык · Language»</b> tugmasi yoki /lang. Ilova ham shu tilga o'tadi.",
        "ru": "🌐 Язык: кнопка <b>«🌐 Til · Язык · Language»</b> в меню или /lang. Приложение тоже переключится.",
        "en": "🌐 Language: the <b>«🌐 Til · Язык · Language»</b> button or /lang. The app switches too.",
    },
    {
        "id": "site",
        "kw": ["sayt", "сайт", "website", "yashilqollar.uz", "site"],
        "uz": "🌐 Rasmiy sayt: <b>yashilqollar.uz</b> — loyiha, hududlar xaritasi, blog, jamoa. Saytga Telegram, Google yoki email orqali kiring — hisob bot bilan bir xil.",
        "ru": "🌐 Официальный сайт: <b>yashilqollar.uz</b> — о проекте, карта регионов, блог, команда. Вход через Telegram, Google или email — аккаунт тот же, что в боте.",
        "en": "🌐 Official website: <b>yashilqollar.uz</b> — the project, regional map, blog, team. Log in with Telegram, Google or email — same account as the bot.",
    },
    {
        "id": "shop",
        "kw": ["do'kon", "dokon", "магазин", "shop", "sovg'a", "подар", "gift", "futbolka", "футболк"],
        "uz": "🛍 <b>Eko-do'kon</b> — tez kunda! Ballaringizni futbolka, kepka, termos va boshqa sovg'alarga almashtirasiz. Hozir ilovada ko'rib, yoqqanini «♡ Xohlayman» qilib qo'ying.",
        "ru": "🛍 <b>Эко-магазин</b> — скоро! Баллы можно будет обменять на футболку, кепку, термос и другие подарки. Уже сейчас посмотрите в приложении и отметьте «♡ Хочу».",
        "en": "🛍 <b>Eco shop</b> — coming soon! Swap your points for a T-shirt, cap, thermos and more. Browse it in the app now and tap «♡ I want it».",
    },
    {
        "id": "cant_come",
        "kw": ["kela olmayman", "kelolmayman", "bora olmayman", "не смогу прийти", "не приду", "can't come", "cannot come", "bekor qil", "отменить запись"],
        "uz": "🙏 Kela olmasangiz — iltimos, <b>tadbir guruhida</b> yoki hududingiz koordinatoriga oldindan xabar bering, joyingizni boshqa volontyorga beramiz.",
        "ru": "🙏 Если не сможете прийти — пожалуйста, заранее напишите в <b>группе мероприятия</b> или координатору региона, чтобы место отдали другому волонтёру.",
        "en": "🙏 Can't make it? Please let us know in the <b>event group</b> or tell your regional coordinator in advance so your spot goes to someone else.",
    },
    {
        "id": "about",
        "kw": ["yashil qo'llar nima", "loyiha haqida", "что такое yashil", "о проекте", "about the project", "what is yashil"],
        "uz": "🌿 <b>Yashil Qo'llar</b> — O'zbekiston bo'ylab ekologik volontyorlik loyihasi: daraxt ekish, plogging, subbotniklar va eko-tadbirlar. Batafsil: menyudagi «🌟 Biz haqimizda» va yashilqollar.uz.",
        "ru": "🌿 <b>Yashil Qo'llar</b> — экологический волонтёрский проект по всему Узбекистану: посадка деревьев, плоггинг, субботники и эко-мероприятия. Подробнее: «🌟 О нас» в меню и yashilqollar.uz.",
        "en": "🌿 <b>Yashil Qo'llar</b> is an eco-volunteering project across Uzbekistan: tree planting, plogging, clean-ups and eco events. More: «🌟 About us» in the menu and yashilqollar.uz.",
    },
]

_PREP = [(e, [(k, normalize(k).split()) for k in e["kw"]]) for e in FAQ]


def match(question: str):
    """Лучшая запись FAQ или None, если уверенности нет."""
    toks = words(question)
    if not toks:
        return None
    best, best_score = None, 0.0
    for e, kws in _PREP:
        score = 0.0
        for _raw, parts in kws:
            if all(_hit(p, toks) for p in parts):
                score += 2.0 if len(parts) > 1 else 1.0
        if score > best_score:
            best, best_score = e, score
    # короткий вопрос («sertifikat?») — хватает одного слова; длинный — нужно больше совпадений
    need = 1.0 if len(toks) <= 4 else 2.0
    return best if best_score >= need else None


def answer(entry: dict, lang: str) -> str:
    return entry.get(lang) or entry["uz"]


def knowledge_text() -> str:
    """Весь FAQ одним текстом — справочник для ИИ."""
    out = []
    for e in FAQ:
        out.append(f"### {e['id']}\nUZ: {e['uz']}\nRU: {e['ru']}")
    return "\n\n".join(out)
