from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import database as db
from keyboards import get_profile_keyboard, get_platform_keyboard, get_top_players_keyboard
from utils import (
    format_player_stats, format_player_name, format_top_players,
    format_rules, format_party_info, format_history_entry
)
from config import EMOJI, PLATFORMS

router = Router()


class ProfileStates(StatesGroup):
    waiting_for_nickname = State()
    waiting_for_game_id = State()
    waiting_for_search_query = State()


@router.message(F.text.contains("Профиль"))
async def show_profile(message: Message):
    """Показать профиль пользователя"""
    user = await db.get_user(message.from_user.id)
    if not user:
        await message.answer(
            f"{EMOJI['warning']} Сначала зарегистрируйтесь командой /start"
        )
        return
    
    platform_emoji = "🖥️" if user['platform'] == 'pc' else "📱"
    name = format_player_name(user)
    
    # Игровой ник и ID
    game_nickname = user.get('game_nickname') or 'Не указан'
    game_id = user.get('game_id') or 'Не указан'
    
    await message.answer(
        f"{EMOJI['user']} *ПРОФИЛЬ*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{EMOJI['crown']} Игрок: {name}\n"
        f"🎮 Игровой ник: *{game_nickname}*\n"
        f"🆔 Игровой ID: `{game_id}`\n"
        f"{platform_emoji} Платформа: *{PLATFORMS.get(user['platform'], user['platform'])}*\n"
        f"{format_player_stats(user)}",
        reply_markup=get_profile_keyboard(message.from_user.id),
        parse_mode="Markdown"
    )


@router.callback_query(F.data.startswith("profile:history:"))
async def show_match_history(callback: CallbackQuery):
    """Показать историю матчей"""
    user_id = int(callback.data.split(":")[2])
    
    history = await db.get_user_match_history(user_id, limit=10)
    
    if not history:
        await callback.message.answer(
            f"{EMOJI['info']} *История матчей*\n\n"
            f"У вас пока нет завершённых матчей.",
            parse_mode="Markdown"
        )
        await callback.answer()
        return
    
    text = f"{EMOJI['chart']} *ИСТОРИЯ МАТЧЕЙ*\n━━━━━━━━━━━━━━━━━━━━\n"
    
    for match in history:
        text += format_history_entry(match, match['team'])
    
    await callback.message.answer(text, parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data.startswith("profile:nickname:"))
async def change_nickname_prompt(callback: CallbackQuery, state: FSMContext):
    """Запросить новый игровой ник"""
    user_id = int(callback.data.split(":")[2])
    
    if callback.from_user.id != user_id:
        await callback.answer("Вы не можете изменить чужой профиль!", show_alert=True)
        return
    
    await state.set_state(ProfileStates.waiting_for_nickname)
    
    await callback.message.answer(
        f"🎮 *Изменение игрового ника*\n\n"
        f"Отправьте ваш новый игровой ник:\n\n"
        f"{EMOJI['info']} Это имя будет отображаться в матчах и лобби.",
        parse_mode="Markdown"
    )
    await callback.answer()


@router.message(ProfileStates.waiting_for_nickname)
async def process_new_nickname(message: Message, state: FSMContext):
    """Обработать новый ник"""
    new_nickname = message.text.strip()
    
    if len(new_nickname) < 2:
        await message.answer(
            f"{EMOJI['warning']} Ник слишком короткий! Минимум 2 символа.",
            parse_mode="Markdown"
        )
        return
    
    if len(new_nickname) > 32:
        await message.answer(
            f"{EMOJI['warning']} Ник слишком длинный! Максимум 32 символа.",
            parse_mode="Markdown"
        )
        return
    
    await db.update_user_game_nickname(message.from_user.id, new_nickname)
    await state.clear()
    
    await message.answer(
        f"{EMOJI['check']} *Ник успешно изменён!*\n\n"
        f"Ваш новый игровой ник: *{new_nickname}*",
        parse_mode="Markdown"
    )


@router.callback_query(F.data.startswith("profile:gameid:"))
async def change_game_id_prompt(callback: CallbackQuery, state: FSMContext):
    """Запросить новый игровой ID"""
    user_id = int(callback.data.split(":")[2])
    
    if callback.from_user.id != user_id:
        await callback.answer("Вы не можете изменить чужой профиль!", show_alert=True)
        return
    
    await state.set_state(ProfileStates.waiting_for_game_id)
    
    await callback.message.answer(
        f"🆔 *Изменение игрового ID*\n\n"
        f"Отправьте ваш новый игровой ID:\n\n"
        f"{EMOJI['info']} Это ID используется для приглашения в игру (например: #ABC123).",
        parse_mode="Markdown"
    )
    await callback.answer()


@router.message(ProfileStates.waiting_for_game_id)
async def process_new_game_id(message: Message, state: FSMContext):
    """Обработать новый игровой ID"""
    new_game_id = message.text.strip()
    
    if len(new_game_id) < 2:
        await message.answer(
            f"{EMOJI['warning']} ID слишком короткий! Минимум 2 символа.",
            parse_mode="Markdown"
        )
        return
    
    if len(new_game_id) > 32:
        await message.answer(
            f"{EMOJI['warning']} ID слишком длинный! Максимум 32 символа.",
            parse_mode="Markdown"
        )
        return
    
    await db.update_user_game_id(message.from_user.id, new_game_id)
    await state.clear()
    
    await message.answer(
        f"{EMOJI['check']} *Игровой ID успешно изменён!*\n\n"
        f"Ваш новый игровой ID: `{new_game_id}`",
        parse_mode="Markdown"
    )


@router.callback_query(F.data.startswith("profile:platform:"))
async def change_platform_prompt(callback: CallbackQuery):
    """Показать выбор платформы"""
    await callback.message.edit_text(
        f"{EMOJI['gear']} *Смена платформы*\n\n"
        f"Выберите вашу платформу:",
        reply_markup=get_platform_keyboard(),
        parse_mode="Markdown"
    )


@router.callback_query(F.data.startswith("platform:"))
async def change_platform(callback: CallbackQuery):
    """Изменить платформу"""
    platform = callback.data.split(":")[1]
    
    await db.update_user_platform(callback.from_user.id, platform)
    
    await callback.message.edit_text(
        f"{EMOJI['check']} Платформа изменена на *{PLATFORMS.get(platform, platform)}*",
        parse_mode="Markdown"
    )
    await callback.answer("Платформа обновлена!")


@router.message(F.text.contains("Топ игроков"))
async def show_top_menu(message: Message):
    """Показать меню топа игроков"""
    await message.answer(
        f"{EMOJI['trophy']} *ТОП ИГРОКОВ*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Выберите категорию:",
        reply_markup=get_top_players_keyboard(),
        parse_mode="Markdown"
    )


@router.callback_query(F.data.startswith("top:"))
async def show_top_players(callback: CallbackQuery):
    """Показать топ игроков"""
    category = callback.data.split(":")[1]
    
    if category == "all":
        players = await db.get_top_players(limit=10)
        title = "ТОП ИГРОКОВ (ВСЕ)"
    elif category == "pc":
        players = await db.get_top_players(limit=10, platform="pc")
        title = "ТОП ИГРОКОВ (ПК)"
    elif category == "mobile":
        players = await db.get_top_players(limit=10, platform="mobile")
        title = "ТОП ИГРОКОВ (ТЕЛЕФОН)"
    else:
        players = await db.get_top_players(limit=10)
        title = "ТОП ИГРОКОВ"
    
    text = format_top_players(players, title)
    
    await callback.message.edit_text(
        text,
        reply_markup=get_top_players_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.message(F.text.contains("Правила"))
async def show_rules(message: Message):
    """Показать правила"""
    await message.answer(
        format_rules(),
        parse_mode="Markdown"
    )


@router.message(F.text.contains("Пати"))
async def show_party_menu(message: Message):
    """Показать меню пати"""
    from keyboards import get_party_keyboard
    
    user = await db.get_user(message.from_user.id)
    if not user:
        await message.answer(
            f"{EMOJI['warning']} Сначала зарегистрируйтесь командой /start"
        )
        return
    
    party_id = await db.get_user_party(message.from_user.id)
    
    if party_id:
        party = await db.get_party(party_id)
        members = await db.get_party_members(party_id)
        
        leader = await db.get_user(party['leader_id'])
        leader_name = format_player_name(leader) if leader else "Неизвестно"
        
        is_leader = party['leader_id'] == message.from_user.id
        
        await message.answer(
            format_party_info(party, members, leader_name),
            reply_markup=get_party_keyboard(party_id, is_leader),
            parse_mode="Markdown"
        )
    else:
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=f"{EMOJI['party']} Создать пати",
                callback_data="party:create"
            )]
        ])
        
        await message.answer(
            f"{EMOJI['party']} *ПАТИ*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Вы не состоите в пати.\n\n"
            f"Создайте пати, чтобы играть с друзьями!\n"
            f"Игроки в пати всегда попадают в одну команду.",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )


@router.callback_query(F.data == "party:create")
async def create_party(callback: CallbackQuery):
    """Создать пати"""
    user = await db.get_user(callback.from_user.id)
    if not user:
        await callback.answer("Сначала зарегистрируйтесь!", show_alert=True)
        return
    
    existing_party = await db.get_user_party(callback.from_user.id)
    if existing_party:
        await callback.answer("Вы уже в пати!", show_alert=True)
        return
    
    party_id = await db.create_party(callback.from_user.id)
    
    party = await db.get_party(party_id)
    members = await db.get_party_members(party_id)
    leader_name = format_player_name(user)
    
    from keyboards import get_party_keyboard
    
    await callback.message.edit_text(
        f"{EMOJI['check']} *Пати создано!*\n\n" +
        format_party_info(party, members, leader_name),
        reply_markup=get_party_keyboard(party_id, is_leader=True),
        parse_mode="Markdown"
    )
    await callback.answer("Пати создано!")


@router.callback_query(F.data.startswith("party:invite:"))
async def invite_to_party(callback: CallbackQuery):
    """Показать ссылку для приглашения в пати"""
    party_id = int(callback.data.split(":")[2])
    
    bot_info = await callback.bot.get_me()
    invite_link = f"https://t.me/{bot_info.username}?start=party_{party_id}"
    
    await callback.message.answer(
        f"{EMOJI['link']} *Пригласите друзей в пати!*\n\n"
        f"Отправьте эту ссылку друзьям:\n"
        f"`{invite_link}`\n\n"
        f"{EMOJI['info']} Максимум 5 человек в пати.",
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("party:leave:"))
async def leave_party(callback: CallbackQuery):
    """Покинуть пати"""
    party_id = int(callback.data.split(":")[2])
    
    await db.leave_party(party_id, callback.from_user.id)
    
    await callback.message.edit_text(
        f"{EMOJI['check']} Вы покинули пати.",
        parse_mode="Markdown"
    )
    await callback.answer("Вы вышли из пати")


@router.callback_query(F.data.startswith("party:disband:"))
async def disband_party(callback: CallbackQuery):
    """Распустить пати"""
    party_id = int(callback.data.split(":")[2])
    
    party = await db.get_party(party_id)
    if not party:
        await callback.answer("Пати не найдено!", show_alert=True)
        return
    
    if party['leader_id'] != callback.from_user.id:
        await callback.answer("Только лидер может распустить пати!", show_alert=True)
        return
    
    await db.delete_party(party_id)
    
    await callback.message.edit_text(
        f"{EMOJI['check']} Пати распущено.",
        parse_mode="Markdown"
    )
    await callback.answer("Пати удалено")


@router.callback_query(F.data.startswith("party:accept:"))
async def accept_party_invite(callback: CallbackQuery):
    """Принять приглашение в пати"""
    party_id = int(callback.data.split(":")[2])
    
    user = await db.get_user(callback.from_user.id)
    if not user:
        await callback.answer("Сначала зарегистрируйтесь!", show_alert=True)
        return
    
    existing_party = await db.get_user_party(callback.from_user.id)
    if existing_party:
        await callback.answer("Вы уже в пати!", show_alert=True)
        return
    
    members = await db.get_party_members(party_id)
    if len(members) >= 5:
        await callback.answer("Пати заполнено!", show_alert=True)
        return
    
    success = await db.join_party(party_id, callback.from_user.id)
    if not success:
        await callback.answer("Не удалось присоединиться!", show_alert=True)
        return
    
    party = await db.get_party(party_id)
    members = await db.get_party_members(party_id)
    leader = await db.get_user(party['leader_id'])
    leader_name = format_player_name(leader) if leader else "Неизвестно"
    
    from keyboards import get_party_keyboard
    
    await callback.message.edit_text(
        f"{EMOJI['check']} *Вы присоединились к пати!*\n\n" +
        format_party_info(party, members, leader_name),
        reply_markup=get_party_keyboard(party_id, is_leader=False),
        parse_mode="Markdown"
    )
    await callback.answer("Успешно!")


@router.callback_query(F.data.startswith("party:decline:"))
async def decline_party_invite(callback: CallbackQuery):
    """Отклонить приглашение в пати"""
    await callback.message.edit_text(
        f"{EMOJI['cross']} Приглашение отклонено.",
        parse_mode="Markdown"
    )
    await callback.answer()


# ============ ПОИСК ИГРОКОВ ============

@router.message(F.text.contains("Поиск игрока"))
async def search_player_prompt(message: Message, state: FSMContext):
    """Начать поиск игрока (только для админов)"""
    # Проверяем права админа/модератора
    is_admin = await db.is_user_admin(message.from_user.id)
    is_moderator = await db.is_user_moderator(message.from_user.id)
    
    if not is_admin and not is_moderator:
        await message.answer(
            f"{EMOJI['warning']} Эта функция доступна только для администраторов и модераторов."
        )
        return
    
    user = await db.get_user(message.from_user.id)
    if not user:
        await message.answer(
            f"{EMOJI['warning']} Сначала зарегистрируйтесь командой /start"
        )
        return
    
    await state.set_state(ProfileStates.waiting_for_search_query)
    
    await message.answer(
        f"🔍 *Поиск игрока*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Отправьте запрос для поиска:\n\n"
        f"• Игровой ник\n"
        f"• Telegram username (с @ или без)\n"
        f"• Telegram ID (число)\n"
        f"• Игровой ID\n\n"
        f"{EMOJI['info']} Для отмены отправьте /cancel",
        parse_mode="Markdown"
    )


@router.callback_query(F.data == "search:player")
async def search_player_callback(callback: CallbackQuery, state: FSMContext):
    """Начать поиск игрока через кнопку (только для админов)"""
    # Проверяем права админа/модератора
    is_admin = await db.is_user_admin(callback.from_user.id)
    is_moderator = await db.is_user_moderator(callback.from_user.id)
    
    if not is_admin and not is_moderator:
        await callback.answer("Эта функция доступна только для администраторов!", show_alert=True)
        return
    
    await state.set_state(ProfileStates.waiting_for_search_query)
    
    await callback.message.answer(
        f"🔍 *Поиск игрока*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Отправьте запрос для поиска:\n\n"
        f"• Игровой ник\n"
        f"• Telegram username (с @ или без)\n"
        f"• Telegram ID (число)\n"
        f"• Игровой ID\n\n"
        f"{EMOJI['info']} Для отмены отправьте /cancel",
        parse_mode="Markdown"
    )
    await callback.answer()


@router.message(ProfileStates.waiting_for_search_query, F.text == "/cancel")
async def cancel_search(message: Message, state: FSMContext):
    """Отменить поиск"""
    await state.clear()
    await message.answer(
        f"{EMOJI['cross']} Поиск отменён.",
        parse_mode="Markdown"
    )


@router.message(ProfileStates.waiting_for_search_query)
async def process_search_query(message: Message, state: FSMContext):
    """Обработать поисковый запрос"""
    query = message.text.strip()
    
    if len(query) < 2:
        await message.answer(
            f"{EMOJI['warning']} Запрос слишком короткий! Минимум 2 символа.",
            parse_mode="Markdown"
        )
        return
    
    await state.clear()
    
    # Ищем игроков
    results = await db.search_users(query, limit=10)
    
    if not results:
        await message.answer(
            f"🔍 *Поиск:* `{query}`\n\n"
            f"{EMOJI['info']} Игроки не найдены.\n\n"
            f"Попробуйте другой запрос.",
            reply_markup=get_search_again_keyboard(),
            parse_mode="Markdown"
        )
        return
    
    # Формируем результаты
    text = f"🔍 *Результаты поиска:* `{query}`\n"
    text += f"━━━━━━━━━━━━━━━━━━━━\n\n"
    text += f"Найдено: *{len(results)}* игроков\n\n"
    
    for i, user in enumerate(results, 1):
        name = format_player_name(user)
        game_nickname = user.get('game_nickname') or '—'
        game_id = user.get('game_id') or '—'
        rating = user.get('rating', 1000)
        platform = PLATFORMS.get(user.get('platform', 'pc'), user.get('platform', 'pc'))
        
        # Статус бана
        ban_status = " 🚫" if user.get('is_banned') else ""
        
        text += f"*{i}.* {name}{ban_status}\n"
        text += f"   🎮 Ник: `{game_nickname}`\n"
        text += f"   🆔 ID: `{game_id}`\n"
        text += f"   ⭐ Рейтинг: *{rating}*\n"
        text += f"   📱 Платформа: {platform}\n\n"
    
    await message.answer(
        text,
        reply_markup=get_search_results_keyboard(results),
        parse_mode="Markdown"
    )


@router.callback_query(F.data.startswith("player:view:"))
async def view_player_profile(callback: CallbackQuery):
    """Просмотреть профиль игрока"""
    user_id = int(callback.data.split(":")[2])
    
    user = await db.get_user(user_id)
    if not user:
        await callback.answer("Игрок не найден!", show_alert=True)
        return
    
    platform_emoji = "🖥️" if user['platform'] == 'pc' else "📱"
    name = format_player_name(user)
    
    # Игровой ник и ID
    game_nickname = user.get('game_nickname') or 'Не указан'
    game_id = user.get('game_id') or 'Не указан'
    
    # Статус
    status_parts = []
    if user.get('is_banned'):
        status_parts.append("🚫 Заблокирован")
    if user.get('is_admin'):
        status_parts.append("👑 Администратор")
    elif user.get('is_moderator'):
        status_parts.append("🛡️ Модератор")
    
    status_text = "\n".join(status_parts) if status_parts else ""
    if status_text:
        status_text = f"\n{status_text}\n"
    
    text = (
        f"{EMOJI['user']} *ПРОФИЛЬ ИГРОКА*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{EMOJI['crown']} Игрок: {name}\n"
        f"🆔 Telegram ID: `{user_id}`\n"
        f"🎮 Игровой ник: *{game_nickname}*\n"
        f"🆔 Игровой ID: `{game_id}`\n"
        f"{platform_emoji} Платформа: *{PLATFORMS.get(user['platform'], user['platform'])}*\n"
        f"{status_text}"
        f"{format_player_stats(user)}"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_player_profile_keyboard(user_id, callback.from_user.id),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data == "search:again")
async def search_again(callback: CallbackQuery, state: FSMContext):
    """Повторить поиск"""
    await state.set_state(ProfileStates.waiting_for_search_query)
    
    await callback.message.edit_text(
        f"🔍 *Поиск игрока*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Отправьте запрос для поиска:\n\n"
        f"• Игровой ник\n"
        f"• Telegram username (с @ или без)\n"
        f"• Telegram ID (число)\n"
        f"• Игровой ID\n\n"
        f"{EMOJI['info']} Для отмены отправьте /cancel",
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data == "search:back")
async def search_back_to_results(callback: CallbackQuery):
    """Вернуться к результатам поиска (закрыть профиль)"""
    await callback.message.delete()
    await callback.answer()


def get_search_again_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для повторного поиска"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🔍 Искать снова",
            callback_data="search:again"
        )]
    ])


def get_search_results_keyboard(results: list) -> InlineKeyboardMarkup:
    """Клавиатура с результатами поиска"""
    buttons = []
    
    for user in results[:5]:  # Максимум 5 кнопок
        name = format_player_name(user)
        buttons.append([
            InlineKeyboardButton(
                text=f"👤 {name}",
                callback_data=f"player:view:{user['user_id']}"
            )
        ])
    
    buttons.append([
        InlineKeyboardButton(
            text="🔍 Искать снова",
            callback_data="search:again"
        )
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_player_profile_keyboard(target_user_id: int, viewer_user_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для профиля игрока"""
    buttons = []
    
    # Кнопка истории матчей
    buttons.append([
        InlineKeyboardButton(
            text=f"{EMOJI['chart']} История матчей",
            callback_data=f"profile:history:{target_user_id}"
        )
    ])
    
    # Кнопка назад
    buttons.append([
        InlineKeyboardButton(
            text="🔙 Назад",
            callback_data="search:back"
        )
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)
