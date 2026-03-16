from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

import database as db
from keyboards import get_profile_keyboard, get_platform_keyboard, get_top_players_keyboard
from utils import (
    format_player_stats, format_player_name, format_top_players,
    format_rules, format_party_info, format_history_entry
)
from config import EMOJI, PLATFORMS

router = Router()


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