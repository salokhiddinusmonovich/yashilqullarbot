async def show_team_members_by_focus(message: types.Message):
    # Убираем стикеры из маппинга, чтобы в базу уходил чистый текст
    focus_map = {
        "🌟 Project Lead": "founder",
        "💻 Digital Lead": "digital",
        "📸 Media Lead": "media",
        "📋 Organization": "organization"
    }
    
    selected_focus = focus_map.get(message.text)
    
    members = await sync_to_async(lambda: list(
        TeamMemberYashilQullar.objects.filter(focus=selected_focus)
    ))()

    if not members:
        await message.answer("Hozircha bu bo‘limda a’zolar mavjud emas.")
        return

    for member in members:
        # 1. Имя жирным
        # 2. Роль чистым текстом (берем из кнопки, убирая эмодзи)
        role_name = message.text.split(maxsplit=1)[-1] # Убирает первый эмодзи
        
        caption = f"<b>{member.fullname}</b>\n"
        caption += f"{role_name}\n\n"
        
        # Навыки/Описание без лишних символов
        if member.skills:
            caption += f"{member.skills}\n\n"

        # Контакт
        if member.telegram_username:
            username = member.telegram_username.replace('@', '')
            caption += f"Telegram: @{username}"

        if member.photo:
            try:
                photo_file = InputFile(member.photo.path)
                await message.answer_photo(
                    photo=photo_file,
                    caption=caption,
                    parse_mode="HTML"
                )
            except Exception as e:
                print(f"Photo error: {e}")
                await message.answer(caption, parse_mode="HTML")
        else:
            await message.answer(caption, parse_mode="HTML")