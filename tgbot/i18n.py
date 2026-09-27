"""
Переводы бота: узбекский (по умолчанию), русский, английский.

    from tgbot.i18n import t, variants
    t("btn_profile")                 # на языке текущего юзера (ставит I18nMiddleware)
    t("attended_notify", lang="ru", project=..., balance=...)   # явно — для уведомлений другим людям
    variants("btn_profile")          # все 3 варианта текста — для фильтров кнопок

Добавляешь новый текст — добавь все три языка. Если какого-то языка нет,
t() вернёт узбекский вариант.
"""
from contextvars import ContextVar

LANGS = ("uz", "ru", "en")
DEFAULT_LANG = "uz"
LANG_NAMES = {"uz": "🇺🇿 O'zbekcha", "ru": "🇷🇺 Русский", "en": "🇬🇧 English"}

# Одна кнопка на все языки — чтобы её можно было найти, даже если
# случайно выбрал непонятный язык.
LANG_BUTTON = "🌐 Til · Язык · Language"

current_lang: ContextVar[str] = ContextVar("current_lang", default=DEFAULT_LANG)


def t(key: str, lang: str = None, **kwargs):
    lang = lang or current_lang.get()
    entry = TEXTS[key]
    value = entry.get(lang) or entry[DEFAULT_LANG]
    if kwargs and isinstance(value, str):
        return value.format(**kwargs)
    return value


def variants(key: str) -> list:
    return list(dict.fromkeys(TEXTS[key][lang] for lang in LANGS))


def lang_from_telegram(language_code: str | None) -> str:
    code = (language_code or "").lower()[:2]
    return code if code in LANGS else DEFAULT_LANG


# ─────────────────────────── справочники ───────────────────────────

REGIONS = {
    "karakalpakstan": ("Qoraqalpogʻiston Respublikasi", "Республика Каракалпакстан", "Republic of Karakalpakstan"),
    "andijon": ("Andijon viloyati", "Андижанская область", "Andijan Region"),
    "bukhara": ("Buxoro viloyati", "Бухарская область", "Bukhara Region"),
    "fargona": ("Fargʻona viloyati", "Ферганская область", "Fergana Region"),
    "jizzakh": ("Jizzax viloyati", "Джизакская область", "Jizzakh Region"),
    "khorezm": ("Xorazm viloyati", "Хорезмская область", "Khorezm Region"),
    "namangan": ("Namangan viloyati", "Наманганская область", "Namangan Region"),
    "navoi": ("Navoiy viloyati", "Навоийская область", "Navoi Region"),
    "qashqadaryo": ("Qashqadaryo viloyati", "Кашкадарьинская область", "Kashkadarya Region"),
    "samarkand": ("Samarqand viloyati", "Самаркандская область", "Samarkand Region"),
    "sirdaryo": ("Sirdaryo viloyati", "Сырдарьинская область", "Syrdarya Region"),
    "surkhandaryo": ("Surxondaryo viloyati", "Сурхандарьинская область", "Surkhandarya Region"),
    "tashkent_v": ("Toshkent viloyati", "Ташкентская область", "Tashkent Region"),
    "tashkent_s": ("Toshkent shahri", "город Ташкент", "Tashkent City"),
}

ROLES = {
    "volunteer": ("Volontyor", "Волонтёр", "Volunteer"),
    "coordinator": ("Koordinator", "Координатор", "Coordinator"),
    "main_coordinator": ("Bosh koordinator", "Главный координатор", "Main Coordinator"),
    "head_coordinator": ("Koordinatorlar rahbari", "Руководитель координаторов", "Head of Coordinators"),
    "mobilograph": ("Mobilograf", "Мобилограф", "Mobilographer"),
    "it": ("IT mutaxassis", "IT-специалист", "IT Specialist"),
    "organizer": ("Tashkilotchi", "Организатор", "Organizer"),
    "Founder": ("Asoschi", "Основатель", "Founder"),
}

STATUSES = {
    "approved": ("📝 Yozilgan", "📝 Записан", "📝 Registered"),
    "attended": ("✅ Kelgan", "✅ Пришёл", "✅ Attended"),
    "rejected": ("❌ Rad etilgan", "❌ Отклонён", "❌ Rejected"),
    "pending": ("⏳ Kutilmoqda", "⏳ Ожидает", "⏳ Pending"),
}

PROVIDERS = {
    "telegram": ("Telegram bot", "Telegram-бот", "Telegram bot"),
    "email": ("Sayt (email)", "Сайт (email)", "Website (email)"),
    "google": ("Google", "Google", "Google"),
}


def _pick(table: dict, code, lang):
    row = table.get(code)
    if not row:
        return code or "—"
    return row[LANGS.index(lang or current_lang.get())]


def region_label(code, lang=None):
    return _pick(REGIONS, code, lang) if code else t("not_set", lang)


def role_label(code, lang=None):
    return _pick(ROLES, code, lang)


def status_label(code, lang=None):
    return _pick(STATUSES, code, lang)


def provider_label(code, lang=None):
    return _pick(PROVIDERS, code, lang)


def region_from_text(text: str):
    """Код региона по тексту кнопки на ЛЮБОМ из языков."""
    text = (text or "").strip()
    for code, labels in REGIONS.items():
        if text in labels:
            return code
    return None


def rank_label(balance: int, lang=None):
    if balance < 150:
        return t("rank_1", lang)
    if balance < 300:
        return t("rank_2", lang)
    return t("rank_3", lang)


# ─────────────────────────── тексты ───────────────────────────

TEXTS = {
    # ── кнопки главного меню ──
    "btn_about": {"uz": "🌟 Biz haqimizda", "ru": "🌟 О нас", "en": "🌟 About us"},
    "btn_join": {"uz": "🚀 Loyihaga qo‘shilish", "ru": "🚀 Присоединиться", "en": "🚀 Join the team"},
    "btn_qr": {"uz": "🌿 Mening QR-kodim", "ru": "🌿 Мой QR-код", "en": "🌿 My QR code"},
    "btn_guide": {"uz": "❓ Qo'llanma", "ru": "❓ Инструкция", "en": "❓ How it works"},
    "btn_profile": {"uz": "👤 Mening profilim", "ru": "👤 Мой профиль", "en": "👤 My profile"},
    "btn_events": {"uz": "🌱 Tadbirlar", "ru": "🌱 Мероприятия", "en": "🌱 Events"},
    "btn_admin": {"uz": "🛠 Admin panel", "ru": "🛠 Админ-панель", "en": "🛠 Admin panel"},
    "btn_back": {"uz": "⬅️ Orqaga", "ru": "⬅️ Назад", "en": "⬅️ Back"},
    "btn_register": {"uz": "📝 Ro‘yxatdan o‘tish", "ru": "📝 Регистрация", "en": "📝 Sign up"},
    "btn_phone": {"uz": "📱 Raqamni yuborish", "ru": "📱 Отправить номер", "en": "📱 Share my number"},
    "btn_partners": {"uz": "🤝 Hamkorlarimiz", "ru": "🤝 Наши партнёры", "en": "🤝 Our partners"},
    "btn_upcoming": {"uz": "📅 Kelgusi tadbirlar", "ru": "📅 Предстоящие", "en": "📅 Upcoming events"},
    "btn_past": {"uz": "📜 O'tgan tadbirlar", "ru": "📜 Прошедшие", "en": "📜 Past events"},
    "btn_event_register": {"uz": "✅ Ro'yxatdan o'tish", "ru": "✅ Записаться", "en": "✅ Register"},
    "btn_view_profile": {"uz": "📄 Profilni ko'rish", "ru": "📄 Посмотреть профиль", "en": "📄 View profile"},
    "btn_change_photo": {"uz": "📸 Rasmni yangilash", "ru": "📸 Обновить фото", "en": "📸 Update photo"},
    "btn_change_name": {"uz": "✍️ Ismni o'zgartirish", "ru": "✍️ Изменить имя", "en": "✍️ Change name"},
    "btn_change_region": {"uz": "📍 Hududni o'zgartirish", "ru": "📍 Изменить регион", "en": "📍 Change region"},
    "btn_no_experience": {"uz": "Tajribaga ega emasman", "ru": "Опыта нет", "en": "I have no experience"},
    "btn_shop": {"uz": "🛍️ Eko-Shop", "ru": "🛍️ Эко-магазин", "en": "🛍️ Eco Shop"},
    "btn_skip": {"uz": "⏭ O'tkazib yuborish", "ru": "⏭ Пропустить", "en": "⏭ Skip"},

    "btn_open_app": {"uz": "📱 Ilovani ochish", "ru": "📱 Открыть приложение", "en": "📱 Open the app"},
    "btn_open_event_app": {"uz": "📱 Ilovada ko'rish", "ru": "📱 Открыть в приложении", "en": "📱 View in the app"},
    "app_intro": {
        "uz": "📱 <b>Yashil Qo'llar ilovasi</b>\n\nTadbirlar rasmlari bilan, bir bosishda yozilish, QR-kod, reyting va profil — hammasi bir joyda.",
        "ru": "📱 <b>Приложение Yashil Qo'llar</b>\n\nМероприятия с фото, запись в одно касание, QR-код, рейтинг и профиль — всё в одном месте.",
        "en": "📱 <b>Yashil Qo'llar app</b>\n\nEvents with photos, one-tap registration, your QR code, leaderboard and profile — all in one place.",
    },

    # ── общее ──
    "lang_choose": {
        "uz": "🌐 Tilni tanlang · Выберите язык · Choose your language",
        "ru": "🌐 Tilni tanlang · Выберите язык · Choose your language",
        "en": "🌐 Tilni tanlang · Выберите язык · Choose your language",
    },
    "lang_saved": {"uz": "✅ Til: O'zbekcha", "ru": "✅ Язык: Русский", "en": "✅ Language: English"},
    "main_menu": {"uz": "🏠 Asosiy menyu", "ru": "🏠 Главное меню", "en": "🏠 Main menu"},
    "back_to_main": {
        "uz": "⬅️ Asosiy menyuga qaytdingiz",
        "ru": "⬅️ Вы вернулись в главное меню",
        "en": "⬅️ Back to the main menu",
    },
    "error_retry": {
        "uz": "Xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.",
        "ru": "Произошла ошибка. Пожалуйста, попробуйте ещё раз.",
        "en": "Something went wrong. Please try again.",
    },
    "not_registered": {
        "uz": "Siz hali ro'yxatdan o'tmagansiz. /start ni bosing ❗",
        "ru": "Вы ещё не зарегистрированы. Нажмите /start ❗",
        "en": "You're not registered yet. Press /start ❗",
    },
    "use_buttons": {
        "uz": "Iltimos, pastdagi tugmalardan birini tanlang 👇",
        "ru": "Пожалуйста, выберите вариант кнопкой ниже 👇",
        "en": "Please choose one of the buttons below 👇",
    },
    "send_photo": {
        "uz": "Iltimos, rasm yuboring! 📸",
        "ru": "Пожалуйста, отправьте фото! 📸",
        "en": "Please send a photo! 📸",
    },
    "phone_use_button": {
        "uz": "Iltimos, pastdagi tugma orqali telefon raqamingizni yuboring 👇",
        "ru": "Пожалуйста, отправьте номер кнопкой ниже 👇",
        "en": "Please share your number using the button below 👇",
    },
    "ask_phone": {
        "uz": "📱 Telefon raqamingizni yuboring — pastdagi tugmani bosing 👇",
        "ru": "📱 Отправьте номер телефона — нажмите кнопку ниже 👇",
        "en": "📱 Share your phone number — tap the button below 👇",
    },
    "ask_region": {
        "uz": "📍 Qaysi hududdansiz? Tadbirlar hudud bo'yicha ko'rsatiladi 👇",
        "ru": "📍 Из какого вы региона? Мероприятия показываются по региону 👇",
        "en": "📍 Which region are you from? Events are shown by region 👇",
    },
    "not_set": {"uz": "⚠️ Kiritilmagan", "ru": "⚠️ Не указан", "en": "⚠️ Not set"},
    "no_access": {"uz": "⛔️ Ruxsat yo'q", "ru": "⛔️ Нет доступа", "en": "⛔️ No access"},
    "rank_1": {"uz": "🌱 Nihol", "ru": "🌱 Росток", "en": "🌱 Sprout"},
    "rank_2": {"uz": "🌳 Daraxt", "ru": "🌳 Дерево", "en": "🌳 Tree"},
    "rank_3": {"uz": "🛡 Tabiat himoyachisi", "ru": "🛡 Защитник природы", "en": "🛡 Nature Guardian"},

    # ── /start ──
    "welcome_back": {
        "uz": "👋 Salom, <b>{name}</b>! @YashilQollar oilasiga xush kelibsiz.",
        "ru": "👋 Привет, <b>{name}</b>! Добро пожаловать в семью @YashilQollar.",
        "en": "👋 Hi, <b>{name}</b>! Welcome to the @YashilQollar family.",
    },
    "login_confirmed": {
        "uz": "✅ <b>Kirish tasdiqlandi!</b>\n\nSayt ochiq turgan oynaga qayting — siz allaqachon hisobingizdasiz.",
        "ru": "✅ <b>Вход подтверждён!</b>\n\nВернитесь на вкладку с сайтом — вы уже в аккаунте.",
        "en": "✅ <b>Login confirmed!</b>\n\nGo back to the website tab — you're already signed in.",
    },
    "login_expired": {
        "uz": "⚠️ Kirish havolasi eskirgan yoki allaqachon ishlatilgan.\nSaytga qaytib, qaytadan kirib ko'ring.",
        "ru": "⚠️ Ссылка для входа устарела или уже использована.\nВернитесь на сайт и попробуйте войти ещё раз.",
        "en": "⚠️ This login link has expired or was already used.\nGo back to the website and try again.",
    },
    "qr_bad_format": {"uz": "❌ QR-kod noto'g'ri.", "ru": "❌ Неверный QR-код.", "en": "❌ Invalid QR code."},

    # ── привязка аккаунта с сайта ──
    "ask_has_site_account": {
        "uz": "👋 Assalomu alaykum!\n\nBizning saytimizda (yashilqollar.uz) allaqachon ro'yxatdan o'tganmisiz?",
        "ru": "👋 Здравствуйте!\n\nВы уже зарегистрированы на нашем сайте (yashilqollar.uz)?",
        "en": "👋 Hello!\n\nDo you already have an account on our website (yashilqollar.uz)?",
    },
    "btn_has_site": {
        "uz": "✅ Ha, saytda ro'yxatdan o'tganman",
        "ru": "✅ Да, я зарегистрирован на сайте",
        "en": "✅ Yes, I have a website account",
    },
    "btn_first_time": {"uz": "🆕 Yo'q, birinchi marta", "ru": "🆕 Нет, я здесь впервые", "en": "🆕 No, I'm new here"},
    "new_user_welcome": {
        "uz": "👋 Salom, <b>{name}</b>! @YashilQollar oilasiga xush kelibsiz.\n\nRo'yxatdan o'tish uchun pastdagi tugmani bosing 👇",
        "ru": "👋 Привет, <b>{name}</b>! Добро пожаловать в семью @YashilQollar.\n\nЧтобы зарегистрироваться, нажмите кнопку ниже 👇",
        "en": "👋 Hi, <b>{name}</b>! Welcome to the @YashilQollar family.\n\nTap the button below to sign up 👇",
    },
    "ask_site_email": {
        "uz": "Saytda ro'yxatdan o'tgan email manzilingizni yozing 👇",
        "ru": "Напишите email, с которым вы зарегистрированы на сайте 👇",
        "en": "Type the email you used on the website 👇",
    },
    "email_not_found": {
        "uz": "❌ Bunday email bilan hisob topilmadi.\n\nEmailni tekshirib qayta yozing yoki yangi ro'yxatdan o'ting 👇",
        "ru": "❌ Аккаунт с таким email не найден.\n\nПроверьте email и напишите снова или зарегистрируйтесь заново 👇",
        "en": "❌ No account found with this email.\n\nCheck it and type again, or sign up as a new user 👇",
    },
    "btn_new_signup": {"uz": "🆕 Yangi ro'yxatdan o'tish", "ru": "🆕 Зарегистрироваться заново", "en": "🆕 Sign up as new"},
    "already_linked_self": {
        "uz": "✅ Bu hisob allaqachon sizning Telegramingizga bog'langan.",
        "ru": "✅ Этот аккаунт уже привязан к вашему Telegram.",
        "en": "✅ This account is already linked to your Telegram.",
    },
    "linked_other_tg": {
        "uz": "⚠️ Bu email boshqa Telegram akkauntga bog'langan.\nAgar bu sizning hisobingiz bo'lsa, admin bilan bog'laning.",
        "ru": "⚠️ Этот email привязан к другому Telegram-аккаунту.\nЕсли это ваш аккаунт — напишите администратору.",
        "en": "⚠️ This email is linked to another Telegram account.\nIf it's yours, please contact an admin.",
    },
    "account_found": {
        "uz": "🔎 Saytda hisob topildi: <b>{name}</b> ({email})\n\n"
              "Qayta ro'yxatdan o'tish shart emas — shu hisobni Telegramga bog'laymiz. "
              "Bu sizning hisobingiz ekanini tasdiqlang 👇",
        "ru": "🔎 Найден аккаунт на сайте: <b>{name}</b> ({email})\n\n"
              "Заново регистрироваться не нужно — просто привяжем этот аккаунт к Telegram. "
              "Подтвердите, что это ваш аккаунт 👇",
        "en": "🔎 Found your website account: <b>{name}</b> ({email})\n\n"
              "No need to sign up again — we'll link this account to Telegram. "
              "Confirm it's yours 👇",
    },
    "btn_login_password": {"uz": "🔑 Parol bilan kirish", "ru": "🔑 Войти по паролю", "en": "🔑 Log in with password"},
    "btn_email_code": {
        "uz": "📧 Emailga kod yuborish (parolni unutdim)",
        "ru": "📧 Код на email (забыл пароль)",
        "en": "📧 Email me a code (forgot password)",
    },
    "btn_admin_confirm": {"uz": "🙋 Admin orqali tasdiqlash", "ru": "🙋 Подтвердить через админа", "en": "🙋 Confirm via admin"},
    "btn_other_email": {"uz": "✏️ Boshqa email kiritish", "ru": "✏️ Ввести другой email", "en": "✏️ Use another email"},
    "session_expired": {
        "uz": "Sessiya tugadi. /start ni bosing.",
        "ru": "Сессия истекла. Нажмите /start.",
        "en": "Session expired. Press /start.",
    },
    "ask_password": {
        "uz": "🔑 Saytdagi parolingizni yozing 👇",
        "ru": "🔑 Введите пароль от сайта 👇",
        "en": "🔑 Type your website password 👇",
    },
    "btn_forgot_password": {
        "uz": "📧 Parolni unutdim — emailga kod",
        "ru": "📧 Забыл пароль — код на email",
        "en": "📧 Forgot password — email me a code",
    },
    "admin_request_sent": {
        "uz": "🙋 So'rovingiz adminlarga yuborildi. Tasdiqlashlari bilan sizga xabar keladi.",
        "ru": "🙋 Запрос отправлен администраторам. Как только подтвердят — придёт сообщение.",
        "en": "🙋 Your request was sent to the admins. You'll get a message once they confirm.",
    },
    "ask_email_again": {"uz": "Email manzilingizni yozing 👇", "ru": "Напишите ваш email 👇", "en": "Type your email 👇"},
    "wrong_password": {
        "uz": "❌ Parol noto'g'ri. Qayta yozing yoki boshqa usulni tanlang 👇",
        "ru": "❌ Неверный пароль. Попробуйте снова или выберите другой способ 👇",
        "en": "❌ Wrong password. Try again or choose another way 👇",
    },
    "code_email_subject": {
        "uz": "Yashil Qo'llar — tasdiqlash kodi",
        "ru": "Yashil Qo'llar — код подтверждения",
        "en": "Yashil Qo'llar — verification code",
    },
    "code_email_body": {
        "uz": "Sizning tasdiqlash kodingiz: {code}\n\nKodni @YashilQollar botiga yuboring. Kod 10 daqiqa amal qiladi.\n"
              "Agar siz so'ramagan bo'lsangiz — bu xatni e'tiborsiz qoldiring.",
        "ru": "Ваш код подтверждения: {code}\n\nОтправьте его боту @YashilQollar. Код действует 10 минут.\n"
              "Если вы его не запрашивали — просто проигнорируйте это письмо.",
        "en": "Your verification code: {code}\n\nSend it to the @YashilQollar bot. The code is valid for 10 minutes.\n"
              "If you didn't request it, just ignore this email.",
    },
    "code_wait": {
        "uz": "⏳ Kod yaqinda yuborildi. Qayta yuborish uchun {sec} soniya kuting.",
        "ru": "⏳ Код уже отправлен. Повторно можно через {sec} сек.",
        "en": "⏳ A code was just sent. You can resend in {sec} s.",
    },
    "email_send_failed": {
        "uz": "⚠️ Emailga xat yuborib bo'lmadi. Admin orqali tasdiqlashingiz mumkin 👇",
        "ru": "⚠️ Не удалось отправить письмо. Можно подтвердить через админа 👇",
        "en": "⚠️ Couldn't send the email. You can confirm via an admin instead 👇",
    },
    "code_sent": {
        "uz": "📧 <b>{email}</b> manziliga 6 xonali kod yubordik.\nKodni shu yerga yozing 👇\n\n<i>Xat kelmasa — «Spam» papkasini tekshiring.</i>",
        "ru": "📧 Мы отправили 6-значный код на <b>{email}</b>.\nНапишите его сюда 👇\n\n<i>Не пришло? Проверьте папку «Спам».</i>",
        "en": "📧 We sent a 6-digit code to <b>{email}</b>.\nType it here 👇\n\n<i>Nothing arrived? Check your Spam folder.</i>",
    },
    "btn_resend": {"uz": "🔁 Qayta yuborish", "ru": "🔁 Отправить ещё раз", "en": "🔁 Resend"},
    "code_expired": {
        "uz": "⌛ Kod eskirgan. «🔁 Qayta yuborish» tugmasini bosing.",
        "ru": "⌛ Код истёк. Нажмите «🔁 Отправить ещё раз».",
        "en": "⌛ The code has expired. Tap «🔁 Resend».",
    },
    "code_too_many": {
        "uz": "❌ Juda ko'p noto'g'ri urinish. «🔁 Qayta yuborish» bilan yangi kod oling.",
        "ru": "❌ Слишком много неверных попыток. Запросите новый код кнопкой «🔁 Отправить ещё раз».",
        "en": "❌ Too many wrong attempts. Get a new code with «🔁 Resend».",
    },
    "code_wrong": {
        "uz": "❌ Kod noto'g'ri. Qolgan urinishlar: {left}",
        "ru": "❌ Неверный код. Осталось попыток: {left}",
        "en": "❌ Wrong code. Attempts left: {left}",
    },
    "adm_link_request": {
        "uz": "🙋 <b>Hisobni bog'lash so'rovi</b>\n\nTelegram: {tg} ({uname}, <code>{tg_id}</code>)\n"
              "Saytdagi hisob: <b>{email}</b>\n\nBu shu odamning hisobi ekaniga ishonchingiz komilmi?",
        "ru": "🙋 <b>Запрос на привязку аккаунта</b>\n\nTelegram: {tg} ({uname}, <code>{tg_id}</code>)\n"
              "Аккаунт на сайте: <b>{email}</b>\n\nВы уверены, что это аккаунт этого человека?",
        "en": "🙋 <b>Account link request</b>\n\nTelegram: {tg} ({uname}, <code>{tg_id}</code>)\n"
              "Website account: <b>{email}</b>\n\nAre you sure this account belongs to this person?",
    },
    "no_username": {"uz": "username yo'q", "ru": "без username", "en": "no username"},
    "btn_link_yes": {"uz": "✅ Bog'lash", "ru": "✅ Привязать", "en": "✅ Link"},
    "btn_link_no": {"uz": "❌ Rad etish", "ru": "❌ Отклонить", "en": "❌ Decline"},
    "adm_link_declined_mark": {"uz": "❌ <b>Rad etildi</b>", "ru": "❌ <b>Отклонено</b>", "en": "❌ <b>Declined</b>"},
    "link_declined_user": {
        "uz": "❌ Hisobni bog'lash so'rovi rad etildi. Admin bilan bog'laning.",
        "ru": "❌ Запрос на привязку отклонён. Свяжитесь с администратором.",
        "en": "❌ Your link request was declined. Please contact an admin.",
    },
    "adm_link_done_mark": {
        "uz": "✅ <b>Bog'landi</b> ({admin})",
        "ru": "✅ <b>Привязано</b> ({admin})",
        "en": "✅ <b>Linked</b> ({admin})",
    },
    "linked_short": {"uz": "Bog'landi", "ru": "Привязано", "en": "Linked"},
    "link_approved_user": {
        "uz": "✅ Admin tasdiqladi! Hisobingiz ({email}) Telegramga bog'landi.\nDavom etish uchun /start ni bosing.",
        "ru": "✅ Админ подтвердил! Ваш аккаунт ({email}) привязан к Telegram.\nНажмите /start, чтобы продолжить.",
        "en": "✅ An admin approved it! Your account ({email}) is now linked to Telegram.\nPress /start to continue.",
    },
    "err_account_not_found": {"uz": "❌ Hisob topilmadi.", "ru": "❌ Аккаунт не найден.", "en": "❌ Account not found."},
    "err_account_other_tg": {
        "uz": "⚠️ Bu hisob allaqachon boshqa Telegram akkauntga bog'langan.",
        "ru": "⚠️ Этот аккаунт уже привязан к другому Telegram.",
        "en": "⚠️ This account is already linked to another Telegram account.",
    },
    "err_tg_other_account": {
        "uz": "⚠️ Bu Telegram akkaunt boshqa hisobga bog'langan. Admin bilan bog'laning.",
        "ru": "⚠️ Этот Telegram уже привязан к другому аккаунту. Свяжитесь с админом.",
        "en": "⚠️ This Telegram account is linked to a different profile. Please contact an admin.",
    },
    "link_success": {
        "uz": "✅ Xush kelibsiz, <b>{name}</b>! Hisobingiz Telegram bilan bog'landi.",
        "ru": "✅ Добро пожаловать, <b>{name}</b>! Аккаунт привязан к Telegram.",
        "en": "✅ Welcome, <b>{name}</b>! Your account is now linked to Telegram.",
    },
    "profile_ready": {"uz": "🎉 Profilingiz tayyor!", "ru": "🎉 Профиль готов!", "en": "🎉 Your profile is ready!"},

    # ── регистрация ──
    "reg_ask_name": {
        "uz": "<b>1/8</b> · ✍️ Ism va familiyangizni kiriting",
        "ru": "<b>1/8</b> · ✍️ Введите имя и фамилию",
        "en": "<b>1/8</b> · ✍️ Enter your first and last name",
    },
    "reg_ask_age": {
        "uz": "<b>2/8</b> · 🎂 Yoshingizni kiriting 👇",
        "ru": "<b>2/8</b> · 🎂 Сколько вам лет? 👇",
        "en": "<b>2/8</b> · 🎂 How old are you? 👇",
    },
    "reg_bad_age": {
        "uz": "Iltimos, yoshingizni 5 dan 120 gacha bo‘lgan raqam bilan kiriting.",
        "ru": "Пожалуйста, введите возраст числом от 5 до 120.",
        "en": "Please enter your age as a number from 5 to 120.",
    },
    "reg_ask_email": {
        "uz": "<b>3/8</b> · 📧 Email manzilingizni kiriting 👇",
        "ru": "<b>3/8</b> · 📧 Введите ваш email 👇",
        "en": "<b>3/8</b> · 📧 Enter your email 👇",
    },
    "reg_bad_email": {
        "uz": "Iltimos, to‘g‘ri email kiriting (mas: user@gmail.com)",
        "ru": "Пожалуйста, введите корректный email (например: user@gmail.com)",
        "en": "Please enter a valid email (e.g. user@gmail.com)",
    },
    "reg_ask_region": {
        "uz": "<b>4/8</b> · 📍 Qaysi hududdansiz? Pastdagi tugmalardan tanlang 👇",
        "ru": "<b>4/8</b> · 📍 Из какого вы региона? Выберите кнопкой ниже 👇",
        "en": "<b>4/8</b> · 📍 Which region are you from? Pick one below 👇",
    },
    "reg_ask_education": {
        "uz": "<b>5/8</b> · 🎓 O‘qish joyingizni kiriting 👇",
        "ru": "<b>5/8</b> · 🎓 Где вы учитесь? 👇",
        "en": "<b>5/8</b> · 🎓 Where do you study? 👇",
    },
    "reg_ask_experience": {
        "uz": "<b>6/8</b> · <b>Volontyorlik tajribangiz haqida batafsil ma'lumot bering:</b>\n\n"
              "Qaysi tashkilotlarda bo'lgansiz va nima ishlar qilgansiz? Bu biz uchun juda muhim! 👇",
        "ru": "<b>6/8</b> · <b>Расскажите о вашем волонтёрском опыте:</b>\n\n"
              "В каких организациях были и чем занимались? Для нас это очень важно! 👇",
        "en": "<b>6/8</b> · <b>Tell us about your volunteering experience:</b>\n\n"
              "Which organizations were you in and what did you do? This matters a lot to us! 👇",
    },
    "reg_ask_photo": {
        "uz": "<b>7/8</b> · 📸 Profil rasmingizni yuklang",
        "ru": "<b>7/8</b> · 📸 Загрузите фото для профиля",
        "en": "<b>7/8</b> · 📸 Upload a profile photo",
    },
    "reg_ask_phone": {
        "uz": "<b>8/8</b> · 📱 Telefon raqamingizni yuboring — pastdagi tugmani bosing 👇",
        "ru": "<b>8/8</b> · 📱 Отправьте номер телефона — нажмите кнопку ниже 👇",
        "en": "<b>8/8</b> · 📱 Share your phone number — tap the button below 👇",
    },
    "reg_other_phone": {
        "uz": "⚠️ Bu boshqa odamning raqami ko'rinadi. Iltimos, faqat pastdagi tugma orqali O'ZINGIZNING raqamingizni yuboring 👇",
        "ru": "⚠️ Похоже, это чужой номер. Отправьте СВОЙ номер кнопкой ниже 👇",
        "en": "⚠️ That looks like someone else's number. Please share YOUR own number with the button below 👇",
    },
    "reg_email_taken": {
        "uz": "⚠️ Bu email band. Iltimos, boshqa email kiriting 👇",
        "ru": "⚠️ Этот email уже занят. Введите другой 👇",
        "en": "⚠️ This email is taken. Please enter another one 👇",
    },
    "reg_already": {
        "uz": "Siz allaqachon ro'yxatdan o'tgansiz ✅",
        "ru": "Вы уже зарегистрированы ✅",
        "en": "You're already registered ✅",
    },
    "reg_done": {
        "uz": "✅ Ro'yxatdan o'tish muvaffaqiyatli yakunlandi!",
        "ru": "✅ Регистрация успешно завершена!",
        "en": "✅ Registration complete!",
    },

    # ── инструкция ──
    "guide_volunteer": {
        "uz": "📖 <b>Botdan qanday foydalaniladi?</b>\n\n"
              "Tadbirda qatnashish va sertifikat olish uchun 3 qadam:\n\n"
              "1️⃣ <b>🌱 Tadbirlar → 📅 Kelgusi tadbirlar</b> — tadbirni tanlang va "
              "<b>«✅ Ro'yxatdan o'tish»</b> tugmasini bosing.\n"
              "❗ Botda ro'yxatdan o'tish — bu tadbirga yozilish degani EMAS. "
              "Har bir tadbirga alohida yozilish kerak!\n\n"
              "2️⃣ Tadbir kuni <b>🌿 Mening QR-kodim</b> ni oching va koordinatorga ko'rsating.\n\n"
              "3️⃣ Koordinator skaner qilgach, sizga <b>+10 ball</b> tushadi va kelganingiz tasdiqlanadi. ✅\n\n"
              "🎓 <b>Sertifikat</b> tadbirdan keyingi kuni ertalab botga o'zi keladi (PDF). Barchasi — /sertifikat yoki ilovada Profil → «Sertifikatlarim».\n"
              "❗ Faqat QR-kodi skaner qilinganlar sertifikat oladi.\n\n"
              "👤 <b>Mening profilim</b> — ism, rasm, hudud, balans.\n"
              "📍 Tadbirlar hududingiz bo'yicha ko'rsatiladi — hududingiz to'g'ri ekanini tekshiring.\n"
              "🌐 Tilni <b>«🌐 Til · Язык · Language»</b> tugmasi orqali o'zgartirish mumkin.",
        "ru": "📖 <b>Как пользоваться ботом?</b>\n\n"
              "Чтобы участвовать в мероприятии и получить сертификат — 3 шага:\n\n"
              "1️⃣ <b>🌱 Мероприятия → 📅 Предстоящие</b> — выберите мероприятие и нажмите "
              "<b>«✅ Записаться»</b>.\n"
              "❗ Регистрация в боте — это НЕ запись на мероприятие. "
              "На каждое мероприятие нужно записываться отдельно!\n\n"
              "2️⃣ В день мероприятия откройте <b>🌿 Мой QR-код</b> и покажите координатору.\n\n"
              "3️⃣ После сканирования вам начислят <b>+10 баллов</b>, и участие будет подтверждено. ✅\n\n"
              "🎓 <b>Сертификат</b> приходит в бот сам на следующее утро после мероприятия (PDF). Все — /sertifikat или в приложении Профиль → «Мои сертификаты».\n"
              "❗ Сертификат получают только те, чей QR-код отсканирован.\n\n"
              "👤 <b>Мой профиль</b> — имя, фото, регион, баланс.\n"
              "📍 Мероприятия показываются по вашему региону — проверьте, что он указан верно.\n"
              "🌐 Язык можно сменить кнопкой <b>«🌐 Til · Язык · Language»</b>.",
        "en": "📖 <b>How does the bot work?</b>\n\n"
              "3 steps to join an event and get a certificate:\n\n"
              "1️⃣ <b>🌱 Events → 📅 Upcoming events</b> — pick an event and tap "
              "<b>«✅ Register»</b>.\n"
              "❗ Signing up in the bot is NOT the same as registering for an event. "
              "You must register for each event separately!\n\n"
              "2️⃣ On the event day open <b>🌿 My QR code</b> and show it to the coordinator.\n\n"
              "3️⃣ Once scanned, you get <b>+10 points</b> and your attendance is confirmed. ✅\n\n"
              "🎓 Your <b>certificate</b> arrives in the bot automatically the morning after the event (PDF). All of them — /sertifikat or in the app Profile → «My certificates».\n"
              "❗ Only people whose QR code was scanned get a certificate.\n\n"
              "👤 <b>My profile</b> — name, photo, region, balance.\n"
              "📍 Events are shown by your region — make sure it's correct.\n"
              "🌐 Change the language with the <b>«🌐 Til · Язык · Language»</b> button.",
    },
    "guide_coordinator": {
        "uz": "\n\n🧑‍💼 <b>Koordinatorlar uchun:</b>\n"
              "• Volontyorning QR-kodini telefon kamerasi bilan skaner qiling — havola botni "
              "ochadi va kelgani avtomatik tasdiqlanadi.\n"
              "• Agar volontyor tadbirga yozilmagan bo'lsa — bot uni <b>o'zi qo'shadi</b> "
              "va kelgan deb belgilaydi. Saytga kirish shart emas.\n"
              "• Qatnashchilar ro'yxati va Excel — /admin (faqat adminlar uchun).",
        "ru": "\n\n🧑‍💼 <b>Для координаторов:</b>\n"
              "• Отсканируйте QR-код волонтёра камерой телефона — ссылка откроет бота, "
              "и участие подтвердится автоматически.\n"
              "• Если волонтёр не записался на мероприятие — бот <b>сам добавит</b> его "
              "и отметит пришедшим. Заходить на сайт не нужно.\n"
              "• Списки участников и Excel — /admin (только для админов).",
        "en": "\n\n🧑‍💼 <b>For coordinators:</b>\n"
              "• Scan the volunteer's QR code with your phone camera — the link opens the bot "
              "and attendance is confirmed automatically.\n"
              "• If the volunteer didn't register for the event, the bot <b>adds them itself</b> "
              "and marks them as attended. No need to open the website.\n"
              "• Participant lists and Excel — /admin (admins only).",
    },

    # ── о нас / контакты / магазин ──
    "about_text": {
        "uz": "🌿 <b>Yashil Qo'llar</b> — barqaror kelajak sari!\n\n"
              "Maqsadimiz — yoshlar orasida ekologik madaniyatni rivojlantirish. "
              "Safimizda <b>{count}</b> faol ko'ngillilar bor! 💪",
        "ru": "🌿 <b>Yashil Qo'llar</b> — к устойчивому будущему!\n\n"
              "Наша цель — развивать экологическую культуру среди молодёжи. "
              "В наших рядах <b>{count}</b> активных волонтёров! 💪",
        "en": "🌿 <b>Yashil Qo'llar</b> — towards a sustainable future!\n\n"
              "Our goal is to grow an eco-culture among young people. "
              "We have <b>{count}</b> active volunteers! 💪",
    },
    "partners_empty": {"uz": "Hozircha hamkorlar ro'yxati bo'sh.", "ru": "Список партнёров пока пуст.", "en": "No partners yet."},
    "partners_title": {"uz": "🤝 <b>Hamkorlarimiz:</b>", "ru": "🤝 <b>Наши партнёры:</b>", "en": "🤝 <b>Our partners:</b>"},
    "join_text": {
        "uz": "🌱 <b>Barqaror kelajak uchun!</b>\n\n✨ Taklif yoki savollaringiz bormi?\n"
              "👥 Jamoamizga qo‘shilishni xohlaysizmi?\n📩 Unda <b>@yqadmin</b> ga yozing\n\n"
              "🤝 Hamkorlik bo‘yicha:\n📩 <b>@abdulboriyw</b> ga murojaat qiling",
        "ru": "🌱 <b>Ради устойчивого будущего!</b>\n\n✨ Есть предложения или вопросы?\n"
              "👥 Хотите в нашу команду?\n📩 Пишите <b>@yqadmin</b>\n\n"
              "🤝 По вопросам партнёрства:\n📩 <b>@abdulboriyw</b>",
        "en": "🌱 <b>For a sustainable future!</b>\n\n✨ Have ideas or questions?\n"
              "👥 Want to join our team?\n📩 Write to <b>@yqadmin</b>\n\n"
              "🤝 For partnerships:\n📩 <b>@abdulboriyw</b>",
    },
    "shop_soon": {"uz": "<b>🙃 Sahifa tayyorlanmoqda</b>", "ru": "<b>🙃 Раздел в разработке</b>", "en": "<b>🙃 Coming soon</b>"},

    # ── мероприятия ──
    "events_title": {
        "uz": "🌱 <b>Tadbirlar</b>\n\n📅 <b>Kelgusi</b> — yozilish mumkin bo'lgan tadbirlar\n📜 <b>O'tgan</b> — arxiv",
        "ru": "🌱 <b>Мероприятия</b>\n\n📅 <b>Предстоящие</b> — на них можно записаться\n📜 <b>Прошедшие</b> — архив",
        "en": "🌱 <b>Events</b>\n\n📅 <b>Upcoming</b> — events you can register for\n📜 <b>Past</b> — archive",
    },
    "events_none": {
        "uz": "😊 Sizning hududingizda hozircha yangi tadbirlar yo'q.\nKuzatib boring, tez orada e'lon qilinadi!",
        "ru": "😊 В вашем регионе пока нет новых мероприятий.\nСледите за новостями — скоро объявим!",
        "en": "😊 No upcoming events in your region yet.\nStay tuned — we'll announce soon!",
    },
    "events_no_region": {
        "uz": "📍 Tadbirlar hudud bo'yicha ko'rsatiladi, lekin sizda hudud tanlanmagan.\n"
              "<b>👤 Mening profilim → 📍 Hududni o'zgartirish</b>",
        "ru": "📍 Мероприятия показываются по региону, а у вас он не выбран.\n"
              "<b>👤 Мой профиль → 📍 Изменить регион</b>",
        "en": "📍 Events are shown by region, but you haven't picked one.\n"
              "<b>👤 My profile → 📍 Change region</b>",
    },
    "event_seats": {"uz": "👥 <b>Joylar:</b> {count}/{max}", "ru": "👥 <b>Места:</b> {count}/{max}", "en": "👥 <b>Spots:</b> {count}/{max}"},
    "event_already": {
        "uz": "✅ <b>Siz bu tadbirga allaqachon yozilgansiz.</b>",
        "ru": "✅ <b>Вы уже записаны на это мероприятие.</b>",
        "en": "✅ <b>You're already registered for this event.</b>",
    },
    "event_full": {
        "uz": "❌ <b>Afsuski, joylar tugadi.</b> Keyingi tadbirlarni kuzatib boring! 🌱",
        "ru": "❌ <b>К сожалению, мест больше нет.</b> Следите за следующими мероприятиями! 🌱",
        "en": "❌ <b>Sorry, no spots left.</b> Watch for upcoming events! 🌱",
    },
    "event_subscribe_first": {
        "uz": "⚠️ <b>Ro'yxatdan o'tish uchun avval kanalimizga a'zo bo'ling!</b>\nKanalga a'zo bo'lib, qayta bosing.",
        "ru": "⚠️ <b>Чтобы записаться, сначала подпишитесь на наш канал!</b>\nПосле подписки нажмите ещё раз.",
        "en": "⚠️ <b>Please join our channel first to register!</b>\nAfter joining, tap again.",
    },
    "btn_join_channel": {"uz": "📢 Kanalga a'zo bo'lish", "ru": "📢 Подписаться на канал", "en": "📢 Join the channel"},
    "event_already_applied": {
        "uz": "Siz allaqachon yozilgansiz. 👍",
        "ru": "Вы уже записаны. 👍",
        "en": "You're already registered. 👍",
    },
    "event_gone": {
        "uz": "Bu tadbir endi mavjud emas.",
        "ru": "Это мероприятие больше недоступно.",
        "en": "This event is no longer available.",
    },
    "event_other_region": {
        "uz": "📍 Bu tadbir boshqa hudud uchun. Faqat o'z hududingizdagi tadbirlarga yozilish mumkin.",
        "ru": "📍 Это мероприятие другого региона. Записываться можно только в своём регионе.",
        "en": "📍 This event is for another region. You can only register for events in your own region.",
    },
    "event_no_seats": {"uz": "❌ Kechirasiz, joylar qolmagan.", "ru": "❌ Извините, мест не осталось.", "en": "❌ Sorry, no spots left."},
    "event_accepted": {
        "uz": "✅ <b>«{title}» tadbiriga yozildingiz!</b>\n\n"
              "📌 Tadbir kuni <b>🌿 Mening QR-kodim</b> ni koordinatorga ko'rsating.",
        "ru": "✅ <b>Вы записаны на «{title}»!</b>\n\n"
              "📌 В день мероприятия покажите координатору <b>🌿 Мой QR-код</b>.",
        "en": "✅ <b>You're registered for «{title}»!</b>\n\n"
              "📌 On the event day show <b>🌿 My QR code</b> to the coordinator.",
    },
    "event_accepted_chat": {
        "uz": "\n\n👥 Tadbir guruhiga qo'shiling: {link}\n🎓 Sertifikatlar tadbirdan keyin shu guruhga tashlanadi.",
        "ru": "\n\n👥 Вступите в группу мероприятия: {link}\n🎓 Сертификаты публикуются в этой группе после мероприятия.",
        "en": "\n\n👥 Join the event group: {link}\n🎓 Certificates are posted in this group after the event.",
    },
    "past_empty": {
        "uz": "📜 O'tgan tadbirlar arxivi hozircha bo'sh.",
        "ru": "📜 Архив прошедших мероприятий пока пуст.",
        "en": "📜 No past events yet.",
    },

    # ── отзывы ──
    "fb_ask": {
        "uz": "🙏 <b>{title}</b> tadbiri haqida fikringizni bilishni xohlaymiz!\n\nTadbirni 1 dan 5 gacha baholang:",
        "ru": "🙏 Нам важно ваше мнение о мероприятии <b>{title}</b>!\n\nОцените его от 1 до 5:",
        "en": "🙏 We'd love your feedback on <b>{title}</b>!\n\nRate it from 1 to 5:",
    },
    "fb_ask_comment": {
        "uz": "Rahmat! Siz {rating}⭐ qo'ydingiz.\n\nEndi, iltimos, batafsil yozing:\n"
              "• Nima yoqmadi yoki nima yaxshi bo'lmadi?\n• Nimani yaxshilash kerak deb o'ylaysiz?\n\n"
              "Javobingizni bitta xabar sifatida yuboring 👇\n\nYozgingiz kelmasa — pastdagi tugmani bosing.",
        "ru": "Спасибо! Вы поставили {rating}⭐.\n\nНапишите, пожалуйста, подробнее:\n"
              "• Что не понравилось или прошло не так?\n• Что стоит улучшить?\n\n"
              "Отправьте ответ одним сообщением 👇\n\nНе хотите писать — нажмите кнопку ниже.",
        "en": "Thanks! You gave {rating}⭐.\n\nPlease tell us more:\n"
              "• What didn't you like or what went wrong?\n• What should we improve?\n\n"
              "Send your answer as one message 👇\n\nDon't want to write? Tap the button below.",
    },
    "fb_thanks_nocomment": {
        "uz": "✅ Bahoingiz uchun rahmat! (izohsiz saqlandi)\n\nIltimos, kerakli tugmani yana bir marta bosing 👇",
        "ru": "✅ Спасибо за оценку! (сохранено без комментария)\n\nНажмите нужную кнопку ещё раз 👇",
        "en": "✅ Thanks for rating! (saved without a comment)\n\nPlease tap the button you wanted once more 👇",
    },
    "fb_thanks": {
        "uz": "✅ Rahmat! Fikringiz uchun tashakkur, bu bizga yaxshilanishga yordam beradi. 🌿",
        "ru": "✅ Спасибо за отзыв! Это помогает нам становиться лучше. 🌿",
        "en": "✅ Thank you! Your feedback helps us get better. 🌿",
    },
    "fb_thanks_short": {"uz": "✅ Bahoingiz uchun rahmat! 🌿", "ru": "✅ Спасибо за оценку! 🌿", "en": "✅ Thanks for rating! 🌿"},
    "fb_no_comment": {"uz": "(izohsiz)", "ru": "(без комментария)", "en": "(no comment)"},
    "adm_new_feedback": {
        "uz": "📩 <b>Yangi fikr-mulohaza!</b>\n\n👤 <b>Kim:</b> {name} ({uname})\n🚀 <b>Tadbir:</b> {project}\n{stars} <b>({rating}/5)</b>\n\n💬 <i>{comment}</i>",
        "ru": "📩 <b>Новый отзыв!</b>\n\n👤 <b>Кто:</b> {name} ({uname})\n🚀 <b>Мероприятие:</b> {project}\n{stars} <b>({rating}/5)</b>\n\n💬 <i>{comment}</i>",
        "en": "📩 <b>New feedback!</b>\n\n👤 <b>Who:</b> {name} ({uname})\n🚀 <b>Event:</b> {project}\n{stars} <b>({rating}/5)</b>\n\n💬 <i>{comment}</i>",
    },

    # ── профиль ──
    "profile_menu_title": {
        "uz": "👤 <b>Shaxsiy kabinet</b>\n\nKerakli bo'limni tanlang:",
        "ru": "👤 <b>Личный кабинет</b>\n\nВыберите раздел:",
        "en": "👤 <b>My account</b>\n\nChoose a section:",
    },
    "profile_card": {
        "uz": "🌟 <b>SIZNING PROFILINGIZ</b>\n━━━━━━━━━━━━━━\n🎭 <b>Rol:</b> {role}\n🏆 <b>Daraja:</b> {rank}\n"
              "💰 <b>Balans:</b> {balance} eko-ball\n📅 <b>Tadbirlar:</b> {events} ta\n━━━━━━━━━━━━━━\n"
              "👤 <b>Ism:</b> {name}\n📞 <b>Tel:</b> {phone}\n📍 <b>Hudud:</b> {region}\n\n",
        "ru": "🌟 <b>ВАШ ПРОФИЛЬ</b>\n━━━━━━━━━━━━━━\n🎭 <b>Роль:</b> {role}\n🏆 <b>Уровень:</b> {rank}\n"
              "💰 <b>Баланс:</b> {balance} эко-баллов\n📅 <b>Мероприятий:</b> {events}\n━━━━━━━━━━━━━━\n"
              "👤 <b>Имя:</b> {name}\n📞 <b>Тел:</b> {phone}\n📍 <b>Регион:</b> {region}\n\n",
        "en": "🌟 <b>YOUR PROFILE</b>\n━━━━━━━━━━━━━━\n🎭 <b>Role:</b> {role}\n🏆 <b>Level:</b> {rank}\n"
              "💰 <b>Balance:</b> {balance} eco-points\n📅 <b>Events:</b> {events}\n━━━━━━━━━━━━━━\n"
              "👤 <b>Name:</b> {name}\n📞 <b>Phone:</b> {phone}\n📍 <b>Region:</b> {region}\n\n",
    },
    "profile_region_warning": {
        "uz": "❗ <b>DIQQAT:</b> Siz hududingizni tanlamagansiz! Tadbirlarni ko'rish uchun "
              "<b>«📍 Hududni o'zgartirish»</b> tugmasini bosing.\n\n",
        "ru": "❗ <b>ВНИМАНИЕ:</b> вы не выбрали регион! Чтобы видеть мероприятия, нажмите "
              "<b>«📍 Изменить регион»</b>.\n\n",
        "en": "❗ <b>NOTE:</b> you haven't picked a region! To see events, tap "
              "<b>«📍 Change region»</b>.\n\n",
    },
    "profile_events": {
        "uz": "📜 <b>Ishtirok etgan tadbirlaringiz:</b>\n{list}\n\n🍀 <i>Yashil Qo'llar — birgalikda kuchmiz!</i>",
        "ru": "📜 <b>Мероприятия, где вы участвовали:</b>\n{list}\n\n🍀 <i>Yashil Qo'llar — вместе мы сила!</i>",
        "en": "📜 <b>Events you attended:</b>\n{list}\n\n🍀 <i>Yashil Qo'llar — together we're stronger!</i>",
    },
    "profile_no_events": {
        "uz": "Hali tadbirlarda qatnashmadingiz 🌿",
        "ru": "Вы ещё не участвовали в мероприятиях 🌿",
        "en": "You haven't attended any events yet 🌿",
    },
    "ask_new_name": {
        "uz": "✍️ <b>Yangi ism va familiyangizni kiriting:</b>",
        "ru": "✍️ <b>Введите новое имя и фамилию:</b>",
        "en": "✍️ <b>Enter your new first and last name:</b>",
    },
    "name_saved": {"uz": "✅ <b>Ism o'zgartirildi:</b> {name}", "ru": "✅ <b>Имя изменено:</b> {name}", "en": "✅ <b>Name updated:</b> {name}"},
    "ask_new_photo": {
        "uz": "📸 <b>Profilingiz uchun yangi rasm yuboring:</b>",
        "ru": "📸 <b>Отправьте новое фото для профиля:</b>",
        "en": "📸 <b>Send a new profile photo:</b>",
    },
    "photo_saved": {"uz": "✅ <b>Profil rasmi yangilandi!</b>", "ru": "✅ <b>Фото профиля обновлено!</b>", "en": "✅ <b>Profile photo updated!</b>"},
    "ask_new_region": {
        "uz": "📍 <b>Yangi hududingizni tanlang:</b>",
        "ru": "📍 <b>Выберите новый регион:</b>",
        "en": "📍 <b>Choose your new region:</b>",
    },
    "region_saved": {"uz": "✅ <b>Hudud saqlandi:</b> {region}", "ru": "✅ <b>Регион сохранён:</b> {region}", "en": "✅ <b>Region saved:</b> {region}"},

    # ── QR ──
    "qr_caption": {
        "uz": "🌿 <b>Sizning shaxsiy eko-kodingiz!</b>\n\nTadbirga kelganingizda koordinatorga ko'rsating.",
        "ru": "🌿 <b>Ваш личный эко-код!</b>\n\nПокажите его координатору, когда придёте на мероприятие.",
        "en": "🌿 <b>Your personal eco code!</b>\n\nShow it to the coordinator when you arrive at the event.",
    },
    "qr_no_rights": {
        "uz": "❌ Sizda skanerlash huquqi yo'q! Bu imkoniyat faqat ishchi guruh uchun.",
        "ru": "❌ У вас нет права сканировать! Это только для команды организаторов.",
        "en": "❌ You don't have permission to scan! This is for the team only.",
    },
    "qr_user_not_found": {"uz": "❌ Foydalanuvchi topilmadi!", "ru": "❌ Пользователь не найден!", "en": "❌ User not found!"},
    "qr_no_project": {
        "uz": "❌ {region}: faol tadbir topilmadi!",
        "ru": "❌ {region}: активных мероприятий нет!",
        "en": "❌ {region}: no active events!",
    },
    "qr_already": {
        "uz": "⚠️ <b>{name}</b> «{project}» tadbirida allaqachon tasdiqlangan!",
        "ru": "⚠️ <b>{name}</b> уже отмечен на «{project}»!",
        "en": "⚠️ <b>{name}</b> is already checked in for «{project}»!",
    },
    "qr_success": {
        "uz": "✅ <b>Tayyor!</b>\n{name} kelgani tasdiqlandi.\n📅 <b>Tadbir:</b> {project}{note}\n"
              "💰 <b>Yangi balans:</b> {balance} ball\n👤 <b>Skaner qildi:</b> {scanner} ({role})",
        "ru": "✅ <b>Готово!</b>\nУчастие <b>{name}</b> подтверждено.\n📅 <b>Мероприятие:</b> {project}{note}\n"
              "💰 <b>Новый баланс:</b> {balance} баллов\n👤 <b>Сканировал:</b> {scanner} ({role})",
        "en": "✅ <b>Done!</b>\n<b>{name}</b> is checked in.\n📅 <b>Event:</b> {project}{note}\n"
              "💰 <b>New balance:</b> {balance} points\n👤 <b>Scanned by:</b> {scanner} ({role})",
    },
    "qr_auto_added": {
        "uz": "\n➕ <i>Tadbirga yozilmagan edi — avtomatik qo'shildi.</i>",
        "ru": "\n➕ <i>Не был записан на мероприятие — добавлен автоматически.</i>",
        "en": "\n➕ <i>Wasn't registered for the event — added automatically.</i>",
    },
    "attended_moved": {
        "uz": "✏️ <b>Tuzatish:</b> siz <b>«{project}»</b> tadbirida qatnashgansiz — skanerda xato bilan boshqa tadbir tanlangan edi. Ballaringiz joyida: <b>{balance} ball</b>.",
        "ru": "✏️ <b>Исправление:</b> вы участвовали в <b>«{project}»</b> — при сканировании по ошибке было выбрано другое мероприятие. Баллы на месте: <b>{balance}</b>.",
        "en": "✏️ <b>Correction:</b> you took part in <b>«{project}»</b> — a different event was selected by mistake when scanning. Your points are safe: <b>{balance}</b>.",
    },
    "attended_notify": {
        "uz": "🌟 <b>«{project}» tadbirida ishtirok etganingiz tasdiqlandi!</b>\n\n"
              "Sizga 10 ball berildi. Hozirgi balansingiz: <b>{balance} ball</b>.\n"
              "🎓 Sertifikatingiz tadbirdan keyin tadbir guruhiga tashlanadi.\n\nRahmat, tabiat himoyachisi! 🌿",
        "ru": "🌟 <b>Ваше участие в «{project}» подтверждено!</b>\n\n"
              "Вам начислено 10 баллов. Текущий баланс: <b>{balance} баллов</b>.\n"
              "🎓 Сертификат опубликуем в группе мероприятия после его окончания.\n\nСпасибо, защитник природы! 🌿",
        "en": "🌟 <b>Your attendance at «{project}» is confirmed!</b>\n\n"
              "You got 10 points. Current balance: <b>{balance} points</b>.\n"
              "🎓 Your certificate will be posted in the event group after the event.\n\nThank you, nature guardian! 🌿",
    },

    # ── уведомления из админки сайта ──
    "role_promo": {
        "uz": "🎉 <b>Tabriklaymiz!</b>\n\nSizga <b>{role}</b> maqomi berildi! 🧭\n\n"
              "📖 Skaner qilish va boshqa imkoniyatlar — /help\n\nYashil Qo'llar jamoasi siz bilan faxrlanadi! 🌿",
        "ru": "🎉 <b>Поздравляем!</b>\n\nВам присвоен статус <b>{role}</b>! 🧭\n\n"
              "📖 Как сканировать и что ещё можно — /help\n\nКоманда Yashil Qo'llar гордится вами! 🌿",
        "en": "🎉 <b>Congratulations!</b>\n\nYou've been given the <b>{role}</b> role! 🧭\n\n"
              "📖 How to scan and what else you can do — /help\n\nThe Yashil Qo'llar team is proud of you! 🌿",
    },
    "new_event_invite": {
        "uz": "👋 Salom, {name}!\n\n<b>{title}</b> tadbiri rejalashtirilgan! ✨\n\n"
              "1️⃣ «🌱 Tadbirlar» bo'limiga kiring.\n2️⃣ «📅 Kelgusi tadbirlar» tugmasini bosing.\n"
              "3️⃣ Tadbir ostidagi «✅ Ro'yxatdan o'tish» tugmasini bosing.\n\nSizni kutib qolamiz! 🌿",
        "ru": "👋 Привет, {name}!\n\nЗапланировано мероприятие <b>{title}</b>! ✨\n\n"
              "1️⃣ Откройте «🌱 Мероприятия».\n2️⃣ Нажмите «📅 Предстоящие».\n"
              "3️⃣ Под мероприятием нажмите «✅ Записаться».\n\nЖдём вас! 🌿",
        "en": "👋 Hi, {name}!\n\nA new event is planned: <b>{title}</b>! ✨\n\n"
              "1️⃣ Open «🌱 Events».\n2️⃣ Tap «📅 Upcoming events».\n"
              "3️⃣ Tap «✅ Register» under the event.\n\nSee you there! 🌿",
    },
    "remind_region": {
        "uz": "👋 <b>Salom!</b>\n\n⚠️ Siz @YashilQollar botida hali o'z hududingizni to'g'ri tanlamagansiz.\n"
              "Tadbirlarni ko'rish uchun hududni tugmalar orqali ko'rsatish <b>shart</b>! ❗\n\n"
              "⚙️ <b>Nima qilish kerak:</b>\n<b>«👤 Mening profilim»</b> ➡️ <b>«📍 Hududni o'zgartirish»</b> "
              "tugmasini bosing va hududingizni <b>tugmalar orqali</b> tanlang. 🌿",
        "ru": "👋 <b>Привет!</b>\n\n⚠️ В боте @YashilQollar у вас не выбран корректный регион.\n"
              "Чтобы видеть мероприятия, регион <b>обязательно</b> нужно выбрать кнопкой! ❗\n\n"
              "⚙️ <b>Что сделать:</b>\n<b>«👤 Мой профиль»</b> ➡️ <b>«📍 Изменить регион»</b> "
              "и выберите регион <b>кнопкой</b>. 🌿",
        "en": "👋 <b>Hi!</b>\n\n⚠️ You haven't picked a valid region in the @YashilQollar bot yet.\n"
              "To see events you <b>must</b> choose your region with the buttons! ❗\n\n"
              "⚙️ <b>What to do:</b>\n<b>«👤 My profile»</b> ➡️ <b>«📍 Change region»</b> "
              "and pick your region <b>using the buttons</b>. 🌿",
    },

    # ── админ-панель в боте ──
    "adm_menu": {
        "uz": "🛠 <b>Admin panel</b>\n\n"
              "📊 <b>Statistika</b> — bugungi raqamlar\n"
              "📅 <b>Tadbirlar</b> — qatnashchilar, Excel, odam qo'shish, xabar yuborish\n"
              "🔎 <b>Qidirish</b> — odamni topish, rol yoki adminlik berish\n"
              "📋 <b>Kelganlar hisoboti</b> — kim keldi: kun/hafta/oy, hudud bo'yicha, Excel\n"
              "🎙 <b>Buyruq</b> — yozing yoki aytib yuboring: «bugun toshkent excel»\n"
              "📥 <b>Excel</b> — barcha foydalanuvchilar ro'yxati\n"
              "📢 <b>Rassilka</b> — hammaga xabar yuborish yo'riqnomasi\n\n"
              "👇 Bo'limni tanlang",
        "ru": "🛠 <b>Админ-панель</b>\n\n"
              "📊 <b>Статистика</b> — цифры за сегодня\n"
              "📅 <b>Мероприятия</b> — участники, Excel, добавить человека, написать участникам\n"
              "🔎 <b>Поиск</b> — найти человека, выдать роль или админку\n"
              "📋 <b>Отчёт: кто пришёл</b> — за день/неделю/месяц, по региону, Excel\n"
              "🎙 <b>Команда</b> — напишите или продиктуйте: «сегодня ташкент excel»\n"
              "📥 <b>Excel</b> — список всех пользователей\n"
              "📢 <b>Рассылка</b> — как отправить сообщение всем\n\n"
              "👇 Выберите раздел",
        "en": "🛠 <b>Admin panel</b>\n\n"
              "📊 <b>Statistics</b> — today's numbers\n"
              "📅 <b>Events</b> — participants, Excel, add a person, message participants\n"
              "🔎 <b>Search</b> — find a person, give a role or admin rights\n"
              "📋 <b>Attendance report</b> — who came: day/week/month, by region, Excel\n"
              "🎙 <b>Command</b> — type or dictate: «today tashkent excel»\n"
              "📥 <b>Excel</b> — list of all users\n"
              "📢 <b>Broadcast</b> — how to message everyone\n\n"
              "👇 Choose a section",
    },
    "adm_btn_report": {"uz": "📋 Kelganlar hisoboti", "ru": "📋 Отчёт: кто пришёл", "en": "📋 Attendance report"},
    "rep_pick_period": {"uz": "📋 <b>Kelganlar hisoboti</b>\n\n1/2 · Qaysi davr?", "ru": "📋 <b>Отчёт: кто пришёл</b>\n\n1/2 · За какой период?",
                        "en": "📋 <b>Attendance report</b>\n\n1/2 · Which period?"},
    "rep_pick_region": {"uz": "📋 <b>Kelganlar hisoboti</b> · {period}\n\n2/2 · Qaysi hudud? (tadbir o'tgan hudud)",
                        "ru": "📋 <b>Отчёт: кто пришёл</b> · {period}\n\n2/2 · Какой регион? (где прошло мероприятие)",
                        "en": "📋 <b>Attendance report</b> · {period}\n\n2/2 · Which region? (where the event took place)"},
    "rep_p_today": {"uz": "📅 Bugun", "ru": "📅 Сегодня", "en": "📅 Today"},
    "rep_p_yesterday": {"uz": "⏪ Kecha", "ru": "⏪ Вчера", "en": "⏪ Yesterday"},
    "rep_p_week": {"uz": "🗓 Oxirgi 7 kun", "ru": "🗓 Последние 7 дней", "en": "🗓 Last 7 days"},
    "rep_p_month": {"uz": "📆 Shu oy", "ru": "📆 Этот месяц", "en": "📆 This month"},
    "rep_p_all": {"uz": "♾ Butun vaqt", "ru": "♾ За всё время", "en": "♾ All time"},
    "rep_all_regions": {"uz": "🌍 Barcha hududlar", "ru": "🌍 Все регионы", "en": "🌍 All regions"},
    "rep_tashkent": {"uz": "Toshkent (shahar + viloyat)", "ru": "Ташкент (город + область)", "en": "Tashkent (city + region)"},
    "rep_caption": {
        "uz": "📋 <b>Kelganlar</b>: {n} ta qatnashuv · {people} kishi · {events} ta tadbir\n📅 {period}\n📍 {region}\n\n{lines}",
        "ru": "📋 <b>Пришли</b>: {n} отметок · {people} чел. · {events} мероприятий\n📅 {period}\n📍 {region}\n\n{lines}",
        "en": "📋 <b>Attended</b>: {n} check-ins · {people} people · {events} events\n📅 {period}\n📍 {region}\n\n{lines}",
    },
    "rep_empty": {"uz": "🤷 Bu davrda va hududda hech kim belgilanmagan.\n📅 {period} · 📍 {region}",
                  "ru": "🤷 За этот период в этом регионе никто не отмечен.\n📅 {period} · 📍 {region}",
                  "en": "🤷 Nobody was checked in for this period and region.\n📅 {period} · 📍 {region}"},
    "rep_btn_text": {"uz": "💬 Ro'yxatni chatda ko'rsatish", "ru": "💬 Показать список в чате", "en": "💬 Show the list in chat"},
    "rep_btn_again": {"uz": "🔁 Boshqa hisobot", "ru": "🔁 Другой отчёт", "en": "🔁 Another report"},
    "rep_list_title": {"uz": "📋 <b>Kelganlar</b> · {period} · {region} — {n}", "ru": "📋 <b>Пришли</b> · {period} · {region} — {n}",
                       "en": "📋 <b>Attended</b> · {period} · {region} — {n}"},
    "rep_sheet_people": {"uz": "Kelganlar", "ru": "Пришли", "en": "Attended"},
    "rep_sheet_events": {"uz": "Tadbirlar", "ru": "Мероприятия", "en": "Events"},
    "rep_total": {"uz": "JAMI", "ru": "ИТОГО", "en": "TOTAL"},
    "rep_people_headers": {
        "uz": ["№", "F.I.Sh", "Telefon", "Telegram", "Email", "Yosh", "O'qish joyi", "Volontyor hududi", "Tadbir", "Tadbir hududi", "Tadbir sanasi", "Ball"],
        "ru": ["№", "ФИО", "Телефон", "Telegram", "Email", "Возраст", "Место учёбы", "Регион волонтёра", "Мероприятие", "Регион мероприятия", "Дата", "Баллы"],
        "en": ["#", "Full name", "Phone", "Telegram", "Email", "Age", "Education", "Volunteer region", "Event", "Event region", "Date", "Points"],
    },
    "rep_event_headers": {
        "uz": ["№", "Tadbir", "Hudud", "Sana", "Yozilgan", "Kelgan", "%"],
        "ru": ["№", "Мероприятие", "Регион", "Дата", "Записались", "Пришли", "%"],
        "en": ["#", "Event", "Region", "Date", "Registered", "Attended", "%"],
    },
    "ask_btn": {"uz": "🤖 Savol berish", "ru": "🤖 Задать вопрос", "en": "🤖 Ask a question"},
    "ask_exit_btn": {"uz": "⬅️ Chiqish", "ru": "⬅️ Выйти", "en": "⬅️ Exit"},
    "ask_intro": {
        "uz": "🤖 <b>Savolingizni yozing yoki ovozli xabar yuboring</b> 🎤 — bot, sayt, ilova, tadbirlar, ballar, sertifikat haqida. O'zbekcha, ruscha — farqi yo'q.\n💡 Umuman olganda, botga istalgan paytda savol yozsangiz ham javob beraman.\nChiqish — «⬅️ Chiqish».",
        "ru": "🤖 <b>Напишите вопрос или отправьте голосовое</b> 🎤 — про бота, сайт, приложение, мероприятия, баллы, сертификаты. На узбекском или русском — неважно.\n💡 Вообще, можно просто написать боту вопрос в любой момент — я отвечу.\nВыйти — «⬅️ Выйти».",
        "en": "🤖 <b>Type a question or send a voice message</b> 🎤 — about the bot, website, app, events, points, certificates. Uzbek, Russian or English.\n💡 In fact, you can message the bot a question at any time — I'll answer.\nTo leave — «⬅️ Exit».",
    },
    "ask_bye": {"uz": "👌 Yana savol bo'lsa — «❓ Qo'llanma» → «🤖 Savol berish» yoki /ask.",
                "ru": "👌 Будут вопросы — «❓ Инструкция» → «🤖 Задать вопрос» или /ask.",
                "en": "👌 More questions? «❓ How it works» → «🤖 Ask a question» or /ask."},
    "ask_fallback": {"uz": "🙏 Bu savolga javob topolmadim. Hududingiz koordinatorlariga yozing: ilova → Reyting → «Jamoa».",
                     "ru": "🙏 Не нашёл ответа на этот вопрос. Напишите координаторам вашего региона: приложение → Рейтинг → «Команда».",
                     "en": "🙏 I couldn't find an answer. Please message your region's coordinators: app → Top → «Team»."},
    "ask_limit": {"uz": "⏳ Bugungi savollar limiti tugadi ({n} ta). Ertaga yana so'rang yoki koordinatorga yozing: ilova → Reyting → «Jamoa».",
                  "ru": "⏳ Лимит вопросов на сегодня исчерпан ({n}). Спросите завтра или напишите координатору: приложение → Рейтинг → «Команда».",
                  "en": "⏳ Today's question limit is used up ({n}). Ask again tomorrow or message a coordinator: app → Top → «Team»."},
    "ask_ai_note": {"uz": "\n\n<i>🤖 Sun'iy intellekt javobi — xato bo'lishi mumkin.</i>", "ru": "\n\n<i>🤖 Ответ ИИ — может содержать ошибки.</i>",
                    "en": "\n\n<i>🤖 AI answer — may contain mistakes.</i>"},
    "voice_tip": {"uz": "🎤 Ovozli xabarni tinglay olmayman. Klaviaturadagi 🎙 mikrofonni bosib aytib yozing — telefon uni o'zi matnga aylantiradi.",
                  "ru": "🎤 Голосовые сообщения я не слушаю. Нажмите 🎙 на клавиатуре и продиктуйте — телефон сам превратит речь в текст.",
                  "en": "🎤 I can't listen to voice messages. Tap 🎙 on your keyboard and dictate — your phone turns it into text."},
    "adm_btn_cmd": {"uz": "🎙 Buyruq (matn yoki ovoz)", "ru": "🎙 Команда (текст или голос)", "en": "🎙 Command (text or voice)"},
    "cmd_help": {
        "uz": "🎙 <b>Buyruq rejimi</b> — yozing yoki <b>ovozli xabar</b> yuboring (o'zbekcha/ruscha):\n\n"
              "• <code>bugun toshkent excel</code> — kim keldi, Excel\n• <code>kecha samarqand kelganlar</code>\n"
              "• <code>hafta statistika</code> — yangi odamlar, kelganlar, tadbirlar\n• <code>farg'ona koordinatorlari</code>\n"
              "• <code>kelgusi tadbirlar</code>\n• <code>top Aziza</code> yoki <code>top +99890…</code>\n\n"
              "Faqat ko'rish va hisobotlar. Rol berish, xabar yuborish — tugmalar orqali.{ai}\nChiqish — «⬅️ Menyu».",
        "ru": "🎙 <b>Режим команд</b> — напишите или отправьте <b>голосовое</b> (узбекский/русский):\n\n"
              "• <code>сегодня ташкент excel</code> — кто пришёл, Excel\n• <code>вчера самарканд пришли</code>\n"
              "• <code>статистика за неделю</code> — новые, пришедшие, мероприятия\n• <code>координаторы фергана</code>\n"
              "• <code>ближайшие мероприятия</code>\n• <code>найди Азиза</code> или <code>найди +99890…</code>\n\n"
              "Только просмотр и отчёты. Роли и рассылки — кнопками.{ai}\nВыйти — «⬅️ Меню».",
        "en": "🎙 <b>Command mode</b> — type or send a <b>voice message</b> (Uzbek/Russian):\n\n"
              "• <code>today tashkent excel</code> — who came, Excel\n• <code>yesterday samarkand attended</code>\n"
              "• <code>stats this week</code> — new users, attendance, events\n• <code>coordinators fergana</code>\n"
              "• <code>upcoming events</code>\n• <code>find Aziza</code> or <code>find +99890…</code>\n\n"
              "Read-only: reports and lookups. Roles and broadcasts — via buttons.{ai}\nLeave — «⬅️ Menu».",
    },
    "cmd_ai_on": {"uz": "\n🤖 Boshqacha aytsangiz ham tushunaman (bepul AI).", "ru": "\n🤖 Понимаю и свободные формулировки (бесплатный ИИ).",
                  "en": "\n🤖 Free-form phrasing works too (free AI)."},
    "cmd_doing": {"uz": "⏳ Tayyorlayapman: {what}", "ru": "⏳ Готовлю: {what}", "en": "⏳ Preparing: {what}"},
    "cmd_unknown": {"uz": "🤷 Tushunmadim. Masalan: <code>bugun toshkent excel</code>, <code>hafta statistika</code>, <code>samarqand koordinatorlari</code>, <code>kelgusi tadbirlar</code>, <code>top Aziza</code>.",
                    "ru": "🤷 Не понял. Например: <code>сегодня ташкент excel</code>, <code>статистика за неделю</code>, <code>координаторы самарканд</code>, <code>ближайшие мероприятия</code>, <code>найди Азиза</code>.",
                    "en": "🤷 Didn't get that. E.g.: <code>today tashkent excel</code>, <code>stats this week</code>, <code>coordinators samarkand</code>, <code>upcoming events</code>, <code>find Aziza</code>."},
    "cmd_stats": {
        "uz": "📊 <b>Statistika</b> · {period} · {region}\n\n🆕 Yangi foydalanuvchilar: <b>{new}</b>\n✅ Kelganlar (qatnashuv): <b>{att}</b> · {people} kishi\n📅 Tadbirlar: <b>{events}</b>\n👥 Jami foydalanuvchilar: {total}",
        "ru": "📊 <b>Статистика</b> · {period} · {region}\n\n🆕 Новых пользователей: <b>{new}</b>\n✅ Пришли (отметок): <b>{att}</b> · {people} чел.\n📅 Мероприятий: <b>{events}</b>\n👥 Всего пользователей: {total}",
        "en": "📊 <b>Stats</b> · {period} · {region}\n\n🆕 New users: <b>{new}</b>\n✅ Attended (check-ins): <b>{att}</b> · {people} people\n📅 Events: <b>{events}</b>\n👥 Total users: {total}",
    },
    "cmd_coord_title": {"uz": "👥 <b>Jamoa</b> · {region} — {n}", "ru": "👥 <b>Команда</b> · {region} — {n}", "en": "👥 <b>Team</b> · {region} — {n}"},
    "cmd_events_title": {"uz": "📅 <b>Kelgusi tadbirlar</b> (30 kun) · {region} — {n}", "ru": "📅 <b>Ближайшие мероприятия</b> (30 дней) · {region} — {n}",
                         "en": "📅 <b>Upcoming events</b> (30 days) · {region} — {n}"},
    "cmd_none": {"uz": "🤷 Hech narsa topilmadi.", "ru": "🤷 Ничего не найдено.", "en": "🤷 Nothing found."},
    "cmd_find_none": {"uz": "🤷 «{q}» topilmadi.", "ru": "🤷 «{q}» не найден.", "en": "🤷 «{q}» not found."},
    "cmd_found": {"uz": "🔎 Topildi: {n}", "ru": "🔎 Найдено: {n}", "en": "🔎 Found: {n}"},
    "btn_invite": {"uz": "👥 Do'stni taklif qilish", "ru": "👥 Пригласить друга", "en": "👥 Invite a friend"},
    "invite_text": {
        "uz": "👥 <b>Do'stlaringizni taklif qiling!</b>\n\nDo'stingiz shu havola orqali ro'yxatdan o'tib, <b>birinchi tadbirga kelganda</b> sizga <b>+{bonus} ball</b> beriladi.\n\n🔗 Sizning havolangiz:\n{link}\n\n📊 Taklif qilganlar: <b>{invited}</b> · kelganlar: <b>{joined}</b> · bonus: <b>+{earned}</b>",
        "ru": "👥 <b>Приглашайте друзей!</b>\n\nКогда друг зарегистрируется по этой ссылке и <b>придёт на первое мероприятие</b>, вы получите <b>+{bonus} баллов</b>.\n\n🔗 Ваша ссылка:\n{link}\n\n📊 Приглашено: <b>{invited}</b> · пришли: <b>{joined}</b> · бонус: <b>+{earned}</b>",
        "en": "👥 <b>Invite your friends!</b>\n\nWhen a friend signs up with this link and <b>comes to their first event</b>, you get <b>+{bonus} points</b>.\n\n🔗 Your link:\n{link}\n\n📊 Invited: <b>{invited}</b> · came: <b>{joined}</b> · bonus: <b>+{earned}</b>",
    },
    "invite_btn_share": {"uz": "📤 Do'stga yuborish", "ru": "📤 Отправить другу", "en": "📤 Send to a friend"},
    "invite_share_text": {"uz": "Yashil Qo'llar volontyorlariga qo'shil! 🌿 Birga daraxt ekamiz va shaharni tozalaymiz.",
                          "ru": "Присоединяйся к волонтёрам Yashil Qo'llar! 🌿 Вместе сажаем деревья и убираем город.",
                          "en": "Join Yashil Qo'llar volunteers! 🌿 Let's plant trees and clean up the city together."},
    "ref_bonus": {"uz": "🎉 Siz taklif qilgan <b>{name}</b> birinchi tadbiriga keldi! Sizga <b>+{bonus} ball</b>. Balans: <b>{balance}</b>.",
                  "ru": "🎉 Приглашённый вами <b>{name}</b> пришёл на первое мероприятие! Вам <b>+{bonus} баллов</b>. Баланс: <b>{balance}</b>.",
                  "en": "🎉 <b>{name}</b>, whom you invited, came to their first event! <b>+{bonus} points</b> for you. Balance: <b>{balance}</b>."},
    "rem_day": {"uz": "⏰ <b>Ertaga tadbir!</b>\n\n🌱 <b>{title}</b>\n🗓 {date}, {time}\n📍 {place}\n\n📌 QR-kodingizni tayyorlab qo'ying. Kela olmasangiz — pastdagi tugmani bosing, joyingizni boshqa volontyorga beramiz.",
                "ru": "⏰ <b>Завтра мероприятие!</b>\n\n🌱 <b>{title}</b>\n🗓 {date}, {time}\n📍 {place}\n\n📌 Приготовьте QR-код. Если не сможете прийти — нажмите кнопку ниже, место отдадим другому волонтёру.",
                "en": "⏰ <b>Event tomorrow!</b>\n\n🌱 <b>{title}</b>\n🗓 {date}, {time}\n📍 {place}\n\n📌 Have your QR code ready. Can't make it? Tap the button below and we'll give your spot to someone else."},
    "rem_2h": {"uz": "⏳ <b>2 soatdan keyin boshlanadi!</b>\n\n🌱 <b>{title}</b>\n🕐 {time} · 📍 {place}\n\nQR-kodni koordinatorga ko'rsatishni unutmang. Ko'rishguncha! 🌿",
               "ru": "⏳ <b>Начало через 2 часа!</b>\n\n🌱 <b>{title}</b>\n🕐 {time} · 📍 {place}\n\nНе забудьте показать QR-код координатору. До встречи! 🌿",
               "en": "⏳ <b>Starts in 2 hours!</b>\n\n🌱 <b>{title}</b>\n🕐 {time} · 📍 {place}\n\nDon't forget to show your QR code to the coordinator. See you! 🌿"},
    "rem_group": {"uz": "\n👥 Guruh: {link}", "ru": "\n👥 Группа: {link}", "en": "\n👥 Group: {link}"},
    "rem_btn_qr": {"uz": "🌿 QR-kod", "ru": "🌿 QR-код", "en": "🌿 QR code"},
    "rem_btn_no": {"uz": "❌ Kelolmayman", "ru": "❌ Не смогу", "en": "❌ Can't come"},
    "rem_cancelled": {"uz": "👌 Tushunarli, «{title}» dagi joyingiz bo'shatildi. Keyingi safar kutamiz! 🌿",
                      "ru": "👌 Понятно, ваше место на «{title}» освобождено. Ждём в следующий раз! 🌿",
                      "en": "👌 Got it, your spot at «{title}» is freed. See you next time! 🌿"},
    "rem_cant_cancel": {"uz": "✅ Siz bu tadbirga allaqachon kelgansiz.", "ru": "✅ Вы уже отмечены на этом мероприятии.", "en": "✅ You're already checked in for this event."},
    "rem_not_found": {"uz": "Bu tadbirga yozilmagansiz.", "ru": "Вы не записаны на это мероприятие.", "en": "You're not signed up for this event."},
    "adm_btn_noshow": {"uz": "🚫 Kelmaganlar / kelolmayman", "ru": "🚫 Не пришли / отказались", "en": "🚫 No-shows / cancelled"},
    "adm_noshow_title": {"uz": "🚫 <b>{title}</b>", "ru": "🚫 <b>{title}</b>", "en": "🚫 <b>{title}</b>"},
    "adm_noshow_head": {"uz": "Yozilgan, lekin kelmagan: <b>{n}</b>", "ru": "Записались, но не пришли: <b>{n}</b>", "en": "Signed up but didn't come: <b>{n}</b>"},
    "adm_noshow_future": {"uz": "Tadbir hali o'tmagan. Hozir yozilganlar (kelishi kutilmoqda): <b>{n}</b>", "ru": "Мероприятие ещё не прошло. Сейчас записаны (ждём): <b>{n}</b>",
                          "en": "The event hasn't happened yet. Currently signed up: <b>{n}</b>"},
    "adm_cancel_head": {"uz": "❌ Eslatmada «Kelolmayman» deganlar: <b>{n}</b>", "ru": "❌ Нажали «Не смогу» в напоминании: <b>{n}</b>", "en": "❌ Tapped «Can't come» in a reminder: <b>{n}</b>"},
    "adm_btn_shopw": {"uz": "🛍 Do'kon: kim nima xohlaydi", "ru": "🛍 Магазин: что хотят", "en": "🛍 Shop: what people want"},
    "adm_shopw_title": {"uz": "🛍 <b>Eko-do'kon — «Xohlayman»</b>", "ru": "🛍 <b>Эко-магазин — «Хочу»</b>", "en": "🛍 <b>Eco shop — «I want it»</b>"},
    "adm_shopw_note": {"uz": "Shu raqamlarga qarab qaysi sovg'alarni birinchi tayyorlashni hal qiling.", "ru": "По этим цифрам решайте, какие подарки готовить первыми.",
                       "en": "Use these numbers to decide which gifts to prepare first."},
    "shop_stickers": {"uz": "🌿 Stikerlar", "ru": "🌿 Стикеры", "en": "🌿 Stickers"},
    "shop_pin": {"uz": "📍 Znachok", "ru": "📍 Значок", "en": "📍 Pin"},
    "shop_bracelet": {"uz": "📿 Bilaguzuk", "ru": "📿 Браслет", "en": "📿 Bracelet"},
    "shop_notebook": {"uz": "📓 Eko-bloknot", "ru": "📓 Эко-блокнот", "en": "📓 Notebook"},
    "shop_bag": {"uz": "👜 Eko-sumka", "ru": "👜 Эко-сумка", "en": "👜 Tote bag"},
    "shop_cap": {"uz": "🧢 Kepka", "ru": "🧢 Кепка", "en": "🧢 Cap"},
    "shop_tree": {"uz": "🌳 Nomingizdan ko'chat", "ru": "🌳 Дерево от имени", "en": "🌳 Tree in your name"},
    "shop_tshirt": {"uz": "👕 Futbolka", "ru": "👕 Футболка", "en": "👕 T-shirt"},
    "shop_thermos": {"uz": "🥤 Termos", "ru": "🥤 Термос", "en": "🥤 Thermos"},
    "shop_hoodie": {"uz": "🧥 Xudi", "ru": "🧥 Худи", "en": "🧥 Hoodie"},
    "rep_sheet_noshow": {"uz": "Kelmaganlar", "ru": "Не пришли", "en": "No-shows"},
    "cert_caption": {"uz": "🎓 <b>«{title}»</b> tadbirida qatnashganingiz uchun sertifikat!\n№ {number}\n\nRahmat, tabiat himoyachisi! 🌿 Barcha sertifikatlaringiz: /sertifikat",
                     "ru": "🎓 Сертификат за участие в <b>«{title}»</b>!\n№ {number}\n\nСпасибо, защитник природы! 🌿 Все ваши сертификаты: /sertifikat",
                     "en": "🎓 Your certificate for taking part in <b>«{title}»</b>!\n№ {number}\n\nThank you, nature defender! 🌿 All your certificates: /sertifikat"},
    "cert_list": {"uz": "🎓 <b>Sertifikatlaringiz</b> — {n} ta. Kerakligini bosing, bot PDF yuboradi:", "ru": "🎓 <b>Ваши сертификаты</b> — {n}. Нажмите нужный — бот пришлёт PDF:",
                  "en": "🎓 <b>Your certificates</b> — {n}. Tap one and the bot sends the PDF:"},
    "cert_none": {"uz": "🎓 Hozircha sertifikat yo'q. Sertifikat tadbirda QR-kodingiz skaner qilingandan keyin paydo bo'ladi.",
                  "ru": "🎓 Сертификатов пока нет. Сертификат появляется, когда на мероприятии отсканировали ваш QR-код.",
                  "en": "🎓 No certificates yet. A certificate appears once your QR code is scanned at an event."},
    "cert_past": {"uz": "🎓 <b>Yangilik!</b> Endi sertifikatlaringiz doim qo'lingizda. O'tgan tadbirlar uchun sertifikatlaringiz tayyor: <b>{n} ta</b>.\n\n📥 Olish: /sertifikat yoki ilovada Profil → «Sertifikatlarim».",
                  "ru": "🎓 <b>Новое!</b> Теперь ваши сертификаты всегда под рукой. Сертификаты за прошлые мероприятия готовы: <b>{n}</b>.\n\n📥 Получить: /sertifikat или в приложении Профиль → «Мои сертификаты».",
                  "en": "🎓 <b>New!</b> Your certificates are now always at hand. Certificates for past events are ready: <b>{n}</b>.\n\n📥 Get them: /sertifikat or in the app Profile → «My certificates»."},
    "voice_long": {"uz": "🎤 Ovozli xabar juda uzun. 2 daqiqagacha qilib, qisqaroq so'rang.", "ru": "🎤 Голосовое слишком длинное. Запишите покороче — до 2 минут.",
                   "en": "🎤 The voice message is too long. Please keep it under 2 minutes."},
    "ai_error": {"uz": "⚠️ Sun'iy intellekt hozir javob bera olmadi. Qayta yuboring yoki savolni matn bilan yozing. (Admin: /ai — sababini ko'rsatadi.)",
                 "ru": "⚠️ ИИ сейчас не смог ответить. Отправьте ещё раз или напишите вопрос текстом. (Админам: /ai — покажет причину.)",
                 "en": "⚠️ The AI couldn't answer right now. Send it again or type your question. (Admins: /ai shows why.)"},
    "ai_menu": {"uz": "🤖 Aniq javobni topa olmadim. Mavzuni tanlang — tayyor javob bor 👇\nYoki savolni boshqacha yozing.",
                "ru": "🤖 Не нашёл точного ответа. Выберите тему — там готовый ответ 👇\nИли сформулируйте вопрос по-другому.",
                "en": "🤖 I couldn't find an exact answer. Pick a topic — there's a ready answer 👇\nOr rephrase your question."},
    "voice_menu": {"uz": "🎤 Ovozli xabarni hozir ocholmadim. Mavzuni tanlang 👇 yoki savolni matn bilan yozing.",
                   "ru": "🎤 Сейчас не удалось разобрать голосовое. Выберите тему 👇 или напишите вопрос текстом.",
                   "en": "🎤 I couldn't process the voice message right now. Pick a topic 👇 or type your question."},
    "faqbtn_register_bot": {"uz": "📝 Ro'yxatdan o'tish", "ru": "📝 Регистрация", "en": "📝 Sign up"},
    "faqbtn_join_event": {"uz": "🌱 Tadbirga yozilish", "ru": "🌱 Записаться", "en": "🌱 Join an event"},
    "faqbtn_qr": {"uz": "🌿 QR-kod", "ru": "🌿 QR-код", "en": "🌿 QR code"},
    "faqbtn_certificate": {"uz": "🎓 Sertifikat", "ru": "🎓 Сертификат", "en": "🎓 Certificate"},
    "faqbtn_points": {"uz": "⭐ Ballar", "ru": "⭐ Баллы", "en": "⭐ Points"},
    "faqbtn_password": {"uz": "🔑 Parol / sayt", "ru": "🔑 Пароль / сайт", "en": "🔑 Password / site"},
    "faqbtn_app": {"uz": "📱 Ilova", "ru": "📱 Приложение", "en": "📱 App"},
    "faqbtn_contact": {"uz": "👥 Kimga yozish", "ru": "👥 Кому написать", "en": "👥 Who to contact"},
    "small_talk": {"uz": "👋 Salom! Men Yashil Qo'llar yordamchisiman. Savolingizni yozing yoki ovozli xabar yuboring 🎤 — masalan: «tadbirga qanday yozilaman?», «sertifikatim qayerda?»",
                   "ru": "👋 Привет! Я помощник Yashil Qo'llar. Напишите вопрос или отправьте голосовое 🎤 — например: «как записаться на мероприятие?», «где мой сертификат?»",
                   "en": "👋 Hi! I'm the Yashil Qo'llar assistant. Type a question or send a voice message 🎤 — e.g. «how do I join an event?», «where is my certificate?»"},
    "ai_busy_day": {"uz": "⏳ Bugungi bepul AI limiti tugadi — taxminan soat {time} da tiklanadi. Hozircha savolni matn bilan yozing: tayyor javoblardan topishga harakat qilaman.",
                    "ru": "⏳ Бесплатный лимит ИИ на сегодня закончился — восстановится примерно в {time}. Пока напишите вопрос текстом: постараюсь найти готовый ответ.",
                    "en": "⏳ Today's free AI limit is used up — it resets around {time}. For now, type your question: I'll try the ready answers."},
    "ai_busy": {"uz": "⏳ Sun'iy intellekt hozir band (bepul limit). 1 daqiqadan keyin qayta yuboring yoki savolni matn bilan yozing.",
                "ru": "⏳ ИИ сейчас занят (бесплатный лимит). Отправьте ещё раз через минуту или напишите вопрос текстом.",
                "en": "⏳ The AI is busy right now (free limit). Send it again in a minute or type your question."},
    "adm_btn_stats": {"uz": "📊 Statistika", "ru": "📊 Статистика", "en": "📊 Statistics"},
    "adm_btn_events": {"uz": "📅 Tadbirlar", "ru": "📅 Мероприятия", "en": "📅 Events"},
    "adm_btn_find": {"uz": "🔎 Qidirish", "ru": "🔎 Поиск", "en": "🔎 Search"},
    "adm_btn_users_xlsx": {"uz": "📥 Excel (hamma)", "ru": "📥 Excel (все)", "en": "📥 Excel (all users)"},
    "adm_btn_bc": {"uz": "📢 Rassilka", "ru": "📢 Рассылка", "en": "📢 Broadcast"},
    "adm_btn_menu": {"uz": "⬅️ Menyu", "ru": "⬅️ Меню", "en": "⬅️ Menu"},
    "adm_btn_excel": {"uz": "📥 Excel", "ru": "📥 Excel", "en": "📥 Excel"},
    "adm_btn_attended": {"uz": "✅ Kelganlar", "ru": "✅ Пришедшие", "en": "✅ Attended"},
    "adm_btn_add": {"uz": "➕ Odam qo'shish", "ru": "➕ Добавить человека", "en": "➕ Add a person"},
    "adm_btn_msg": {"uz": "✉️ Xabar yuborish", "ru": "✉️ Написать участникам", "en": "✉️ Message participants"},
    "adm_btn_events_back": {"uz": "⬅️ Tadbirlar", "ru": "⬅️ Мероприятия", "en": "⬅️ Events"},
    "adm_btn_done": {"uz": "✔️ Tugatish", "ru": "✔️ Готово", "en": "✔️ Done"},
    "adm_btn_cancel": {"uz": "❌ Bekor qilish", "ru": "❌ Отмена", "en": "❌ Cancel"},
    "adm_btn_back_event": {"uz": "⬅️ Tadbirga qaytish", "ru": "⬅️ К мероприятию", "en": "⬅️ Back to event"},
    "adm_btn_add_to_event": {"uz": "📅 Tadbirga qo'shish", "ru": "📅 Добавить в мероприятие", "en": "📅 Add to event"},
    "adm_btn_role": {"uz": "🎭 Rolni o'zgartirish", "ru": "🎭 Сменить роль", "en": "🎭 Change role"},
    "adm_btn_make_admin": {"uz": "👑 Admin qilish", "ru": "👑 Сделать админом", "en": "👑 Make admin"},
    "adm_btn_remove_admin": {"uz": "👑 Adminlikni olish", "ru": "👑 Снять админку", "en": "👑 Remove admin"},
    "adm_no_events": {"uz": "Tadbirlar yo'q.", "ru": "Мероприятий нет.", "en": "No events."},
    "adm_events_title": {
        "uz": "📅 <b>Tadbirlar</b> (oxirgi 15)\n🟢 faol · ⚪️ yopilgan\nRaqamlar: <b>kelgan / yozilgan</b>\n\n👇 Tadbirni tanlang",
        "ru": "📅 <b>Мероприятия</b> (последние 15)\n🟢 активно · ⚪️ закрыто\nЦифры: <b>пришли / записались</b>\n\n👇 Выберите мероприятие",
        "en": "📅 <b>Events</b> (latest 15)\n🟢 active · ⚪️ closed\nNumbers: <b>attended / registered</b>\n\n👇 Pick an event",
    },
    "adm_event_card": {
        "uz": "📅 <b>{title}</b>\n🗓 {date} · {region}\n📍 {place}\n{active}\n\n"
              "📝 Yozilgan: <b>{reg}</b> / {max}\n✅ Kelgan: <b>{att}</b>\n\n"
              "<i>📥 Excel — qatnashchilar ro'yxati (kelganlar birinchi, sertifikat uchun)\n"
              "➕ Odam qo'shish — yozilmagan, lekin kelgan odamni qo'shish\n"
              "✉️ Xabar — shu tadbir qatnashchilarining hammasiga</i>",
        "ru": "📅 <b>{title}</b>\n🗓 {date} · {region}\n📍 {place}\n{active}\n\n"
              "📝 Записались: <b>{reg}</b> / {max}\n✅ Пришли: <b>{att}</b>\n\n"
              "<i>📥 Excel — список участников (пришедшие первыми, для сертификатов)\n"
              "➕ Добавить — если человек пришёл, но не записался\n"
              "✉️ Написать — сообщение всем участникам этого мероприятия</i>",
        "en": "📅 <b>{title}</b>\n🗓 {date} · {region}\n📍 {place}\n{active}\n\n"
              "📝 Registered: <b>{reg}</b> / {max}\n✅ Attended: <b>{att}</b>\n\n"
              "<i>📥 Excel — participant list (attended first, for certificates)\n"
              "➕ Add — someone came but didn't register\n"
              "✉️ Message — send to everyone in this event</i>",
    },
    "adm_active": {"uz": "🟢 Faol", "ru": "🟢 Активно", "en": "🟢 Active"},
    "adm_inactive": {"uz": "⚪️ Faol emas", "ru": "⚪️ Неактивно", "en": "⚪️ Inactive"},
    "adm_event_not_found": {"uz": "Tadbir topilmadi.", "ru": "Мероприятие не найдено.", "en": "Event not found."},
    "adm_no_attended": {"uz": "Hali hech kim tasdiqlanmagan.", "ru": "Пока никто не отмечен.", "en": "Nobody checked in yet."},
    "adm_attended_title": {
        "uz": "✅ <b>{title}</b> — kelganlar ({n}):",
        "ru": "✅ <b>{title}</b> — пришли ({n}):",
        "en": "✅ <b>{title}</b> — attended ({n}):",
    },
    "adm_preparing": {"uz": "Tayyorlanmoqda…", "ru": "Готовлю…", "en": "Preparing…"},
    "adm_no_participants": {"uz": "Qatnashchilar yo'q.", "ru": "Участников нет.", "en": "No participants."},
    "adm_excel_caption": {
        "uz": "📥 {title}\n✅ Kelgan: {att} · 📝 Jami: {total}",
        "ru": "📥 {title}\n✅ Пришли: {att} · 📝 Всего: {total}",
        "en": "📥 {title}\n✅ Attended: {att} · 📝 Total: {total}",
    },
    "adm_users_caption": {"uz": "👥 Jami: {n}", "ru": "👥 Всего: {n}", "en": "👥 Total: {n}"},
    "xl_sheet_participants": {"uz": "Qatnashchilar", "ru": "Участники", "en": "Participants"},
    "xl_sheet_users": {"uz": "Foydalanuvchilar", "ru": "Пользователи", "en": "Users"},
    "xl_event_headers": {
        "uz": ["№", "F.I.Sh", "Telefon", "Email", "Telegram", "Hudud", "Yosh", "O'qish joyi", "Status", "Yozilgan vaqt"],
        "ru": ["№", "ФИО", "Телефон", "Email", "Telegram", "Регион", "Возраст", "Место учёбы", "Статус", "Дата записи"],
        "en": ["#", "Full name", "Phone", "Email", "Telegram", "Region", "Age", "Education", "Status", "Registered at"],
    },
    "xl_user_headers": {
        "uz": ["ID", "F.I.Sh", "Telefon", "Email", "Telegram", "TG ID", "Hudud", "Yosh", "Rol", "Ball",
               "Qatnashgan tadbirlar", "Qayerdan", "Sana"],
        "ru": ["ID", "ФИО", "Телефон", "Email", "Telegram", "TG ID", "Регион", "Возраст", "Роль", "Баллы",
               "Посещено мероприятий", "Откуда", "Дата"],
        "en": ["ID", "Full name", "Phone", "Email", "Telegram", "TG ID", "Region", "Age", "Role", "Points",
               "Events attended", "Source", "Date"],
    },
    "adm_add_prompt": {
        "uz": "➕ Kimni qo'shamiz? Yozing:\n• <code>@username</code>\n• telefon raqam\n• ism familiya\n• email\n• Telegram ID\n\n"
              "Bir nechta odamni ketma-ket qo'shish mumkin.\n"
              "<i>Bugungi yoki o'tgan tadbirga qo'shilgan odam darhol «kelgan» deb belgilanadi (+10 ball).</i>",
        "ru": "➕ Кого добавить? Напишите:\n• <code>@username</code>\n• телефон\n• имя и фамилию\n• email\n• Telegram ID\n\n"
              "Можно добавлять несколько человек подряд.\n"
              "<i>Если мероприятие сегодня или уже прошло — человек сразу отмечается пришедшим (+10 баллов).</i>",
        "en": "➕ Who should we add? Type:\n• <code>@username</code>\n• phone number\n• full name\n• email\n• Telegram ID\n\n"
              "You can add several people one after another.\n"
              "<i>If the event is today or already passed, the person is marked as attended right away (+10 points).</i>",
    },
    "adm_not_found": {
        "uz": "❌ Topilmadi. Boshqacha yozib ko'ring (masalan @username yoki telefon).",
        "ru": "❌ Не найдено. Попробуйте иначе (например @username или телефон).",
        "en": "❌ Not found. Try another way (e.g. @username or phone).",
    },
    "adm_add_more": {
        "uz": "\n\nYana kimnidir qo'shasizmi? Yozing yoki «✔️ Tugatish».",
        "ru": "\n\nДобавить ещё кого-то? Напишите или нажмите «✔️ Готово».",
        "en": "\n\nAdd someone else? Type or tap «✔️ Done».",
    },
    "adm_many_found": {
        "uz": "Bir nechta odam topildi ({n}). Keraklisini tanlang 👇",
        "ru": "Найдено несколько человек ({n}). Выберите нужного 👇",
        "en": "Found several people ({n}). Pick the right one 👇",
    },
    "adm_added_attended": {
        "uz": "➕ <b>{name}</b> qo'shildi va kelgan deb belgilandi ✅",
        "ru": "➕ <b>{name}</b> добавлен и отмечен пришедшим ✅",
        "en": "➕ <b>{name}</b> added and marked as attended ✅",
    },
    "adm_added_registered": {
        "uz": "➕ <b>{name}</b> tadbirga yozildi 📝",
        "ru": "➕ <b>{name}</b> записан на мероприятие 📝",
        "en": "➕ <b>{name}</b> registered for the event 📝",
    },
    "adm_marked_attended": {
        "uz": "✅ <b>{name}</b> kelgan deb belgilandi",
        "ru": "✅ <b>{name}</b> отмечен пришедшим",
        "en": "✅ <b>{name}</b> marked as attended",
    },
    "adm_already_in": {
        "uz": "ℹ️ <b>{name}</b> allaqachon ro'yxatda ({status})",
        "ru": "ℹ️ <b>{name}</b> уже в списке ({status})",
        "en": "ℹ️ <b>{name}</b> is already on the list ({status})",
    },
    "adm_msg_prompt": {
        "uz": "✉️ Tadbir qatnashchilariga yuboriladigan xabarni yozing (matn, rasm, video — nima bo'lsa).",
        "ru": "✉️ Напишите сообщение для участников мероприятия (текст, фото, видео — что угодно).",
        "en": "✉️ Send the message for the event participants (text, photo, video — anything).",
    },
    "adm_sending": {"uz": "🚀 Yuborilmoqda: {n} kishi…", "ru": "🚀 Отправляю: {n} чел.…", "en": "🚀 Sending to {n} people…"},
    "adm_sent": {
        "uz": "✅ Yuborildi: {sent} · 🚫 bloklagan: {blocked}",
        "ru": "✅ Доставлено: {sent} · 🚫 заблокировали бота: {blocked}",
        "en": "✅ Delivered: {sent} · 🚫 blocked the bot: {blocked}",
    },
    "adm_find_prompt": {
        "uz": "🔎 Kimni qidiramiz? <code>@username</code>, telefon, ism, email yoki Telegram ID yozing.",
        "ru": "🔎 Кого ищем? Напишите <code>@username</code>, телефон, имя, email или Telegram ID.",
        "en": "🔎 Who are we looking for? Type <code>@username</code>, phone, name, email or Telegram ID.",
    },
    "adm_find_not_found": {
        "uz": "❌ Topilmadi. Boshqacha yozib ko'ring.",
        "ru": "❌ Не найдено. Попробуйте написать иначе.",
        "en": "❌ Not found. Try typing it differently.",
    },
    "adm_found_n": {"uz": "Topildi: {n}", "ru": "Найдено: {n}", "en": "Found: {n}"},
    "adm_user_card": {
        "uz": "👤 <b>{name}</b>{crown}\n🎭 Rol: {role}\n📱 {phone} · ✉️ {email}\n💬 {uname} · ID: <code>{tg}</code>\n"
              "📍 {region} · 🎂 {age}\n💰 {balance} ball · 📝 {total} tadbir · ✅ {att} kelgan\n🔐 {provider} · {date} · 🌐 {ulang}",
        "ru": "👤 <b>{name}</b>{crown}\n🎭 Роль: {role}\n📱 {phone} · ✉️ {email}\n💬 {uname} · ID: <code>{tg}</code>\n"
              "📍 {region} · 🎂 {age}\n💰 {balance} баллов · 📝 {total} записей · ✅ {att} пришёл\n🔐 {provider} · {date} · 🌐 {ulang}",
        "en": "👤 <b>{name}</b>{crown}\n🎭 Role: {role}\n📱 {phone} · ✉️ {email}\n💬 {uname} · ID: <code>{tg}</code>\n"
              "📍 {region} · 🎂 {age}\n💰 {balance} points · 📝 {total} events · ✅ {att} attended\n🔐 {provider} · {date} · 🌐 {ulang}",
    },
    "adm_last_events": {"uz": "<b>Oxirgi tadbirlar:</b>", "ru": "<b>Последние мероприятия:</b>", "en": "<b>Recent events:</b>"},
    "adm_choose_role": {
        "uz": "🎭 Yangi rolni tanlang:\n<i>Volontyordan boshqa har qanday rol QR skaner qila oladi. "
              "Rol berilganda odamga tabrik xabari boradi.</i>",
        "ru": "🎭 Выберите новую роль:\n<i>Любая роль, кроме «Волонтёр», может сканировать QR. "
              "Человеку придёт поздравление.</i>",
        "en": "🎭 Choose the new role:\n<i>Any role except Volunteer can scan QR codes. "
              "The person gets a congratulation message.</i>",
    },
    "adm_saved": {"uz": "Saqlandi ✅", "ru": "Сохранено ✅", "en": "Saved ✅"},
    "adm_cant_self": {
        "uz": "O'zingizdan adminlikni ola olmaysiz",
        "ru": "Нельзя снять админку с самого себя",
        "en": "You can't remove your own admin rights",
    },
    "adm_choose_event": {
        "uz": "📅 Qaysi tadbirga qo'shamiz?\n<i>Bugungi yoki o'tgan tadbir bo'lsa — darhol «kelgan» deb belgilanadi.</i>",
        "ru": "📅 В какое мероприятие добавить?\n<i>Если оно сегодня или уже прошло — человек сразу отмечается пришедшим.</i>",
        "en": "📅 Which event should we add them to?\n<i>If it's today or already passed, they're marked as attended right away.</i>",
    },
    "adm_bc_help": {
        "uz": "📢 <b>Rassilka</b>\n\nKerakli xabarni (matn/rasm/video) yozing, keyin unga <b>reply</b> qilib buyruq yuboring:\n\n"
              "<code>/send</code> — hammaga\n<code>/regionsend samarkand</code> — bitta hududga\n"
              "<code>/targetsend @nick1 @nick2</code> — aniq odamlarga\n<code>/adminsend</code> — faqat adminlarga\n"
              "<code>/remindregion</code> — hududi noto'g'ri bo'lganlarga eslatma\n<code>/check @nick</code> — kanalga obunani tekshirish\n\n"
              "Hudud kodlari: <code>{regions}</code>\n\n"
              "Bitta tadbir qatnashchilariga xabar — 📅 Tadbirlar → tadbir → ✉️",
        "ru": "📢 <b>Рассылка</b>\n\nНапишите сообщение (текст/фото/видео), затем ответьте на него (<b>reply</b>) командой:\n\n"
              "<code>/send</code> — всем\n<code>/regionsend samarkand</code> — одному региону\n"
              "<code>/targetsend @nick1 @nick2</code> — конкретным людям\n<code>/adminsend</code> — только админам\n"
              "<code>/remindregion</code> — напомнить тем, у кого неверный регион\n<code>/check @nick</code> — проверить подписку на канал\n\n"
              "Коды регионов: <code>{regions}</code>\n\n"
              "Сообщение участникам одного мероприятия — 📅 Мероприятия → мероприятие → ✉️",
        "en": "📢 <b>Broadcast</b>\n\nWrite the message (text/photo/video), then <b>reply</b> to it with a command:\n\n"
              "<code>/send</code> — everyone\n<code>/regionsend samarkand</code> — one region\n"
              "<code>/targetsend @nick1 @nick2</code> — specific people\n<code>/adminsend</code> — admins only\n"
              "<code>/remindregion</code> — remind people with a wrong region\n<code>/check @nick</code> — check channel subscription\n\n"
              "Region codes: <code>{regions}</code>\n\n"
              "Message one event's participants — 📅 Events → event → ✉️",
    },

    # ── команды рассылки (admin.py) ──
    "bc_reply_needed": {
        "uz": "ℹ️ Yuboriladigan xabarga <b>reply</b> qilib <code>{cmd}</code> yozing.",
        "ru": "ℹ️ Ответьте (<b>reply</b>) командой <code>{cmd}</code> на сообщение, которое нужно разослать.",
        "en": "ℹ️ <b>Reply</b> with <code>{cmd}</code> to the message you want to send.",
    },
    "bc_args_needed": {
        "uz": "⚠️ Buyruqdan keyin kimga yuborishni yozing. Masalan:\n<code>{example}</code>",
        "ru": "⚠️ Укажите после команды, кому отправить. Например:\n<code>{example}</code>",
        "en": "⚠️ Add who to send to after the command. Example:\n<code>{example}</code>",
    },
    "bc_empty": {"uz": "❌ Hech kim topilmadi.", "ru": "❌ Никого не найдено.", "en": "❌ Nobody found."},
    "bc_bad_region": {
        "uz": "❌ Bunday hudud kodi yo'q. Mavjud kodlar:\n<code>{regions}</code>",
        "ru": "❌ Нет такого кода региона. Доступные коды:\n<code>{regions}</code>",
        "en": "❌ Unknown region code. Available codes:\n<code>{regions}</code>",
    },
    "bc_started": {"uz": "🚀 <b>Rassilka boshlandi!</b>\nQabul qiluvchilar: {n}", "ru": "🚀 <b>Рассылка запущена!</b>\nПолучателей: {n}", "en": "🚀 <b>Broadcast started!</b>\nRecipients: {n}"},
    "bc_done": {
        "uz": "✅ <b>Rassilka tugadi!</b>\n\n📥 Yetkazildi: {sent}\n🚫 Bloklagan: {blocked}\n⚠️ Xatolar: {errors}",
        "ru": "✅ <b>Рассылка завершена!</b>\n\n📥 Доставлено: {sent}\n🚫 Заблокировали: {blocked}\n⚠️ Ошибок: {errors}",
        "en": "✅ <b>Broadcast finished!</b>\n\n📥 Delivered: {sent}\n🚫 Blocked: {blocked}\n⚠️ Errors: {errors}",
    },
    "bc_region_ok": {
        "uz": "✅ Hammada hudud to'g'ri ko'rsatilgan! Eslatma kerak emas.",
        "ru": "✅ У всех указан корректный регион! Рассылка не нужна.",
        "en": "✅ Everyone has a valid region! No reminder needed.",
    },
    "bc_region_list": {
        "uz": "📋 <b>Hududi noto'g'ri bo'lganlar ({n}):</b>",
        "ru": "📋 <b>Пользователи с неверным регионом ({n}):</b>",
        "en": "📋 <b>Users with an invalid region ({n}):</b>",
    },
    "chk_not_found": {"uz": "❌ <b>{q}</b> bazada topilmadi.", "ru": "❌ <b>{q}</b> не найден в базе.", "en": "❌ <b>{q}</b> not found."},
    "chk_result": {
        "uz": "👤 <b>Foydalanuvchi:</b> {name}\n🆔 <b>ID:</b> <code>{id}</code>\n📊 <b>Natija:</b> {res}",
        "ru": "👤 <b>Пользователь:</b> {name}\n🆔 <b>ID:</b> <code>{id}</code>\n📊 <b>Результат:</b> {res}",
        "en": "👤 <b>User:</b> {name}\n🆔 <b>ID:</b> <code>{id}</code>\n📊 <b>Result:</b> {res}",
    },
    "chk_member": {"uz": "✅ Obuna bo'lgan", "ru": "✅ Подписан", "en": "✅ Subscribed"},
    "chk_left": {"uz": "❌ Kanaldan chiqqan", "ru": "❌ Вышел из канала", "en": "❌ Left the channel"},
    "chk_kicked": {"uz": "🚫 Bloklangan", "ru": "🚫 Забанен", "en": "🚫 Banned"},
    "chk_admin": {"uz": "👨‍✈️ Kanal admini", "ru": "👨‍✈️ Админ канала", "en": "👨‍✈️ Channel admin"},
    "chk_error": {"uz": "⚠️ Tekshirishda xato: {e}", "ru": "⚠️ Ошибка проверки: {e}", "en": "⚠️ Check failed: {e}"},

    # ── ежедневный отчёт ──
    "rep_title": {"uz": "📊 <b>Kunlik hisobot — {date}</b>", "ru": "📊 <b>Отчёт за день — {date}</b>", "en": "📊 <b>Daily report — {date}</b>"},
    "rep_users": {
        "uz": "👥 <b>Foydalanuvchilar:</b> {total} (Telegram bilan: {tg})",
        "ru": "👥 <b>Пользователи:</b> {total} (с Telegram: {tg})",
        "en": "👥 <b>Users:</b> {total} (with Telegram: {tg})",
    },
    "rep_new": {"uz": "🆕 Bugun qo'shildi: <b>+{n}</b>", "ru": "🆕 Новых сегодня: <b>+{n}</b>", "en": "🆕 New today: <b>+{n}</b>"},
    "rep_week": {"uz": "📈 Oxirgi 7 kunda: +{n}", "ru": "📈 За 7 дней: +{n}", "en": "📈 Last 7 days: +{n}"},
    "rep_active": {"uz": "🟢 Bugun botdan foydalandi: <b>{n}</b>", "ru": "🟢 Пользовались ботом сегодня: <b>{n}</b>", "en": "🟢 Used the bot today: <b>{n}</b>"},
    "rep_blocked": {
        "uz": "🚫 Bugun botni bloklagan: <b>{b}</b> · qaytgan: {u} · jami bloklagan: {total}",
        "ru": "🚫 Заблокировали бота сегодня: <b>{b}</b> · вернулись: {u} · всего заблокировали: {total}",
        "en": "🚫 Blocked the bot today: <b>{b}</b> · came back: {u} · total blocked: {total}",
    },
    "rep_regs": {"uz": "📝 Bugun tadbirga yozilganlar: <b>{n}</b>", "ru": "📝 Записались на мероприятия сегодня: <b>{n}</b>", "en": "📝 Event registrations today: <b>{n}</b>"},
    "rep_attended": {"uz": "✅ Bugungi tadbirlarda tasdiqlangan: <b>{n}</b>", "ru": "✅ Отмечено на сегодняшних мероприятиях: <b>{n}</b>", "en": "✅ Checked in at today's events: <b>{n}</b>"},
    "rep_feedback": {"uz": "⭐ Yangi fikrlar: {n} (o'rtacha {avg})", "ru": "⭐ Новых отзывов: {n} (средняя {avg})", "en": "⭐ New feedback: {n} (avg {avg})"},
    "rep_upcoming": {"uz": "📅 <b>Yaqin 7 kundagi tadbirlar:</b>", "ru": "📅 <b>Мероприятия на 7 дней:</b>", "en": "📅 <b>Events in the next 7 days:</b>"},
    "rep_note": {
        "uz": "<i>«Bloklagan» hisobi shu funksiya qo'shilgan kundan boshlab yuritiladi.</i>",
        "ru": "<i>Блокировки считаются с момента запуска этой функции.</i>",
        "en": "<i>Blocks are counted since this feature was launched.</i>",
    },
    "src_bot": {"uz": "bot", "ru": "бот", "en": "bot"},
    "src_site": {"uz": "sayt", "ru": "сайт", "en": "website"},
}
