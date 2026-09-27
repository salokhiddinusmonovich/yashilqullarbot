"""
Переводы подписей в Django-админке (модели, колонки, действия, дашборд).

Системные надписи самой админки (Save, Delete, фильтры...) Django уже
переводит сам — у него есть uz/ru/en. Здесь — только наши собственные.
Работает без .po/.mo файлов: tr("key") — ленивая строка, которая берёт
язык из текущего запроса (переключатель языка в шапке админки).
"""
from django.utils.functional import lazy
from django.utils.translation import get_language

T = {
    # ── модели ──
    "app": ("Yashil Qo'llar", "Yashil Qo'llar", "Yashil Qo'llar"),
    "user": ("Foydalanuvchi", "Пользователь", "User"),
    "users": ("Foydalanuvchilar", "Пользователи", "Users"),
    "project": ("Tadbir", "Мероприятие", "Event"),
    "projects": ("Tadbirlar", "Мероприятия", "Events"),
    "participation": ("Qatnashchi", "Участник", "Participant"),
    "participations": ("Qatnashchilar", "Участники", "Participants"),
    "partner": ("Hamkor", "Партнёр", "Partner"),
    "partners": ("Hamkorlar", "Партнёры", "Partners"),
    "notification": ("Bildirishnoma", "Уведомление", "Notification"),
    "notifications": ("Bildirishnomalar", "Уведомления", "Notifications"),
    "feedback": ("Fikr-mulohaza", "Отзыв", "Feedback"),
    "feedbacks": ("Fikr-mulohazalar", "Отзывы", "Feedback"),
    "login_token": ("Kirish tokeni", "Токен входа", "Login token"),
    "login_tokens": ("Kirish tokenlari", "Токены входа", "Login tokens"),
    "project_image": ("Tadbir rasmi", "Фото мероприятия", "Event photo"),
    "project_images": ("Tadbir rasmlari (galereya)", "Фото мероприятия (галерея)", "Event photos (gallery)"),
    "article_image": ("Rasm", "Фото", "Photo"),
    "article_images": ("Rasmlar (galereya)", "Фото (галерея)", "Photos (gallery)"),

    # ── поля ──
    "f_created": ("Yaratilgan sana", "Дата создания", "Created"),
    "f_updated": ("Yangilangan sana", "Дата обновления", "Updated"),
    "f_tg_id": ("Telegram ID", "Telegram ID", "Telegram ID"),
    "f_fullname": ("F.I.Sh", "ФИО", "Full name"),
    "f_age": ("Yosh", "Возраст", "Age"),
    "f_phone": ("Telefon", "Телефон", "Phone"),
    "f_username": ("Telegram username", "Telegram username", "Telegram username"),
    "f_experience": ("Tajriba", "Опыт", "Experience"),
    "f_photo": ("Rasm", "Фото", "Photo"),
    "f_region": ("Hudud", "Регион", "Region"),
    "f_education": ("O'qish joyi", "Место учёбы", "Education"),
    "f_is_admin": ("Admin", "Админ", "Admin"),
    "f_balance": ("Eko-ball", "Эко-баллы", "Eco points"),
    "f_role": ("Rol", "Роль", "Role"),
    "f_password": ("Parol (xesh)", "Пароль (хэш)", "Password (hash)"),
    "f_auth_provider": ("Ro'yxatdan o'tgan joyi", "Способ регистрации", "Sign-up method"),
    "f_is_tester": ("Tester", "Тестировщик", "Tester"),
    "f_title": ("Nomi", "Название", "Title"),
    "f_description": ("Tavsif", "Описание", "Description"),
    "f_date": ("Sana va vaqt", "Дата и время", "Date & time"),
    "f_location": ("Manzil", "Место", "Location"),
    "f_is_active": ("Faol", "Активно", "Active"),
    "f_max": ("Maks. qatnashchilar", "Макс. участников", "Max participants"),
    "f_likes": ("Layklar", "Лайки", "Likes"),
    "f_chat_link": ("Guruh havolasi (sertifikatlar shu yerga)", "Ссылка на группу (сюда кидаем сертификаты)",
                    "Group link (certificates go here)"),
    "f_project_region": ("Qaysi hudud uchun", "Для какого региона", "Region"),
    "f_status": ("Status", "Статус", "Status"),
    "f_applied_at": ("Yozilgan vaqt", "Дата записи", "Registered at"),
    "f_rating": ("Baho (1-5)", "Оценка (1-5)", "Rating (1-5)"),
    "f_comment": ("Izoh", "Комментарий", "Comment"),
    "f_order": ("Tartib raqami", "Порядок", "Order"),
    "f_name": ("Nomi", "Название", "Name"),
    "f_logo": ("Logotip", "Логотип", "Logo"),
    "f_show_in_bot": ("Botda ko'rsatish", "Показывать в боте", "Show in bot"),

    # ── статусы участия ──
    "st_approved": ("📝 Yozilgan", "📝 Записан", "📝 Registered"),
    "st_attended": ("✅ Kelgan (+10 ball)", "✅ Пришёл (+10 баллов)", "✅ Attended (+10 pts)"),
    "st_rejected": ("❌ Rad etilgan", "❌ Отклонён", "❌ Rejected"),
    "st_pending": ("⏳ Kutilmoqda", "⏳ Ожидает", "⏳ Pending"),

    # ── колонки / действия / сообщения админки ──
    "col_face": ("Rasm", "Фото", "Photo"),
    "col_registered": ("Yozilgan", "Записались", "Registered"),
    "col_attended": ("Kelgan", "Пришли", "Attended"),
    "act_attended": ("🌟 Keldi (+10 ball + xabar)", "🌟 Пришёл на мероприятие (+10 баллов + уведомление)",
                     "🌟 Attended (+10 points + notify)"),
    "act_rejected": ("❌ Qatnashuvni bekor qilish (ballni olish)", "❌ Отменить участие (снять баллы)",
                     "❌ Cancel participation (remove points)"),
    "act_remind": ("🔔 Yangi foydalanuvchilarga taklif yuborish", "🔔 Пригласить тех, кто ещё не записан",
                   "🔔 Invite users who haven't registered yet"),
    "msg_attended": ("✅ Belgilandi: {n}. Xabarlar fonda yuborilmoqda.",
                     "✅ Отмечено: {n}. Уведомления отправляются в фоне.",
                     "✅ Marked: {n}. Notifications are being sent in the background."),
    "msg_already": ("Allaqachon belgilangan: {n}", "Уже были отмечены: {n}", "Already marked: {n}"),
    "act_move": ("🔀 Boshqa tadbirga ko'chirish (xato skaner)", "🔀 Перенести на другое мероприятие (ошибка при скане)",
                 "🔀 Move to another event (scan mistake)"),
    "move_target": ("Qaysi tadbirga:", "На какое мероприятие:", "Target event:"),
    "msg_pick_target": ("Avval pastdagi ro'yxatdan to'g'ri tadbirni tanlang.", "Сначала выберите правильное мероприятие в списке рядом с действием.",
                        "First pick the correct event in the list next to the action."),
    "msg_moved": ("🔀 Ko'chirildi: {n} → «{title}». Volontyorlarga tuzatish xabari yuborilmoqda.",
                  "🔀 Перенесено: {n} → «{title}». Волонтёрам отправляется сообщение об исправлении.",
                  "🔀 Moved: {n} → «{title}». Volunteers are being notified."),
    "rep_title": ("Kelganlar hisoboti", "Отчёт: кто пришёл", "Attendance report"),
    "rep_sub": ("Kim keldi — davr va hudud bo'yicha. Excel: 1-varaq odamlar, 2-varaq tadbirlar.",
                "Кто пришёл — за период и по региону. Excel: лист 1 — люди, лист 2 — мероприятия.",
                "Who came — by period and region. Excel: sheet 1 people, sheet 2 events."),
    "rep_period": ("Davr", "Период", "Period"),
    "rep_custom": ("📌 Sanalar", "📌 Свои даты", "📌 Custom dates"),
    "rep_from": ("dan", "с", "from"),
    "rep_to": ("gacha", "по", "to"),
    "rep_region": ("Hudud (tadbir o'tgan joy)", "Регион (где прошло мероприятие)", "Region (where the event took place)"),
    "rep_show": ("Ko'rsatish", "Показать", "Show"),
    "rep_download": ("📥 Excel yuklab olish", "📥 Скачать Excel", "📥 Download Excel"),
    "rep_checkins": ("Qatnashuvlar", "Отметок", "Check-ins"),
    "rep_people_n": ("Kishi", "Человек", "People"),
    "rep_events_n": ("Tadbirlar", "Мероприятий", "Events"),
    "rep_by_event": ("Tadbirlar bo'yicha", "По мероприятиям", "By event"),
    "rep_people": ("Kelganlar", "Пришли", "Attended"),
    "rep_none": ("Bu davrda va hududda hech kim belgilanmagan.", "За этот период в этом регионе никто не отмечен.",
                 "Nobody was checked in for this period and region."),
    "rep_more": ("… va yana {n} ta — to'liq ro'yxat Excel faylida.", "… и ещё {n} — полный список в Excel.",
                 "… and {n} more — full list in the Excel file."),
    "msg_rejected": ("❌ Bekor qilindi: {n}", "❌ Отменено: {n}", "❌ Cancelled: {n}"),
    "msg_remind": ("🔔 «{title}»: {n} kishiga taklif yuborilmoqda (fonda).",
                   "🔔 «{title}»: приглашение отправляется {n} людям (в фоне).",
                   "🔔 «{title}»: sending invites to {n} people (in the background)."),
    "msg_role_sent": ("{name}ga yangi rol haqida xabar yuborildi ✅", "{name}: уведомление о новой роли отправлено ✅",
                      "{name}: new role notification sent ✅"),
    "msg_role_failed": ("Xabar yuborishda xatolik: {e}", "Ошибка отправки уведомления: {e}", "Notification failed: {e}"),

    # ── дашборд ──
    "dash_hello": ("Xush kelibsiz", "Добро пожаловать", "Welcome"),
    "dash_sub": ("Yashil Qo'llar boshqaruv paneli", "Панель управления Yashil Qo'llar", "Yashil Qo'llar control panel"),
    "dash_users": ("Volontyorlar", "Волонтёры", "Volunteers"),
    "dash_new_today": ("Bugun yangi", "Новых сегодня", "New today"),
    "dash_new_week": ("7 kunda yangi", "Новых за 7 дней", "New in 7 days"),
    "dash_active_events": ("Faol tadbirlar", "Активные мероприятия", "Active events"),
    "dash_regs_today": ("Bugun yozilganlar", "Записей сегодня", "Registrations today"),
    "dash_attended_total": ("Jami qatnashuvlar", "Всего посещений", "Total check-ins"),
    "dash_upcoming": ("Kelgusi tadbirlar", "Ближайшие мероприятия", "Upcoming events"),
    "dash_no_upcoming": ("Kelgusi tadbirlar yo'q", "Ближайших мероприятий нет", "No upcoming events"),
    "dash_recent": ("So'nggi yozilishlar", "Последние записи", "Latest registrations"),
    "dash_quick": ("Tezkor harakatlar", "Быстрые действия", "Quick actions"),
    "dash_add_event": ("Tadbir qo'shish", "Добавить мероприятие", "Add event"),
    "dash_participants": ("Qatnashchilar", "Участники", "Participants"),
    "dash_users_link": ("Foydalanuvchilar", "Пользователи", "Users"),
    "dash_feedback": ("Fikrlar", "Отзывы", "Feedback"),
    "dash_regions": ("Hududlar bo'yicha", "По регионам", "By region"),
    "dash_all_sections": ("Barcha bo'limlar", "Все разделы", "All sections"),
    "dash_bot_tip": ("Maslahat: botda /admin — telefondan Excel, odam qo'shish va statistika.",
                     "Совет: в боте есть /admin — Excel, добавление людей и статистика прямо с телефона.",
                     "Tip: the bot has /admin — Excel, adding people and stats right from your phone."),
    "dash_no_group": ("Guruh havolasi yo'q!", "Нет ссылки на группу!", "No group link!"),
}

_IDX = {"uz": 0, "ru": 1, "en": 2}


def _tr(key: str, **kwargs) -> str:
    lang = (get_language() or "ru")[:2]
    row = T[key]
    value = row[_IDX.get(lang, 1)]
    return value.format(**kwargs) if kwargs else value


tr = lazy(_tr, str)


def trn(key: str, **kwargs) -> str:
    """Не ленивая версия — для сообщений message_user() с подстановками."""
    return _tr(key, **kwargs)
