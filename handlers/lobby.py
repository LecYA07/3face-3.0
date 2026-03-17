from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import StateFilter
from typing import List, Dict, Any
import logging

import database as db
from keyboards import (
    get_lobby_keyboard, get_lobbies_list_keyboard, 
    get_maps_keyboard, get_platform_keyboard, get_game_format_keyboard
)
from utils import format_lobby_info, format_player_name, get_random_map
from config import EMOJI, PLATFORMS, GAME_FORMATS

router = Router()
logger = logging.getLogger(__name__)


class LobbyStates(StatesGroup):
    waiting_for_platform = State()
    in_lobby = State()


@router.message(F.text.contains("Лобби"), StateFilter(None, LobbyStates.in_lobby))
async def show_lobbies_menu(message: Message):
    """Показать меню лобби"""
    user = await db.get_user(message.from_user.id)
    if not user:
        await message.answer(
            f"{EMOJI['warning']} Сначала зарегистрируйтесь командой /start"
        )
        return
    
    # Проверяем, в лобби ли уже игрок
    active_lobby = await db.get_user_active_lobby(message.from_user.id)
    if active_lobby:
        lobby = await db.get_lobby(active_lobby)
        players = await db.get_lobby_players(active_lobby)
        
        creator = await db.get_user(lobby['creator_id'])
        creator_name = format_player_name(creator) if creator else "Неизвестно"
        
        game_format = lobby.get('game_format', '5x5')
        format_data = GAME_FORMATS.get(game_format, GAME_FORMATS['5x5'])
        lobby_size = format_data['lobby_size']
        
        is_creator = lobby['creator_id'] == message.from_user.id
        is_full = len(players) >= lobby_size
        
        await message.answer(
            format_lobby_info(lobby, players, creator_name),
            reply_markup=get_lobby_keyboard(active_lobby, is_creator, is_full),
            parse_mode="Markdown"
        )
        return
    
    # Показываем список лобби для платформы пользователя
    platform = user.get('platform', 'pc')
    lobbies = await db.get_active_lobbies(platform)
    
    # Добавляем количество игроков
    for lobby in lobbies:
        lobby['player_count'] = await db.get_lobby_player_count(lobby['lobby_id'])
    
    if lobbies:
        text = f"{EMOJI['users']} *Доступные лобби ({PLATFORMS.get(platform, platform)}):*\n\n"
        text += f"Выберите лобби для присоединения или создайте своё:"
        await message.answer(
            text,
            reply_markup=get_lobbies_list_keyboard(lobbies, platform),
            parse_mode="Markdown"
        )
    else:
        await message.answer(
            f"{EMOJI['info']} Нет доступных лобби для вашей платформы.\n\n"
            f"Создайте своё лобби!",
            reply_markup=get_lobbies_list_keyboard([], platform),
            parse_mode="Markdown"
        )


@router.callback_query(F.data == "lobby:select_format")
async def select_lobby_format(callback: CallbackQuery):
    """Показать выбор формата для создания лобби"""
    user = await db.get_user(callback.from_user.id)
    if not user:
        await callback.answer("Сначала зарегистрируйтесь!", show_alert=True)
        return
    
    if user.get('is_banned'):
        await callback.answer("Вы заблокированы!", show_alert=True)
        return
    
    active_lobby = await db.get_user_active_lobby(callback.from_user.id)
    if active_lobby:
        await callback.answer("Вы уже в лобби!", show_alert=True)
        return
    
    await callback.message.edit_text(
        f"{EMOJI['game']} *Создание лобби*\n\n"
        f"Выберите формат игры:",
        reply_markup=get_game_format_keyboard("lobby"),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("lobby:format:"))
async def create_lobby_with_format(callback: CallbackQuery):
    """Создать лобби с выбранным форматом"""
    game_format = callback.data.split(":")[2]
    
    if game_format not in GAME_FORMATS:
        await callback.answer("Неизвестный формат!", show_alert=True)
        return
    
    user = await db.get_user(callback.from_user.id)
    if not user:
        await callback.answer("Сначала зарегистрируйтесь!", show_alert=True)
        return
    
    if user.get('is_banned'):
        await callback.answer("Вы заблокированы!", show_alert=True)
        return
    
    active_lobby = await db.get_user_active_lobby(callback.from_user.id)
    if active_lobby:
        await callback.answer("Вы уже в лобби!", show_alert=True)
        return
    
    await _create_lobby(callback, user.get('platform', 'pc'), game_format)


@router.callback_query(F.data == "play:create_lobby")
async def create_lobby_start(callback: CallbackQuery, state: FSMContext):
    """Начать создание лобби - выбор платформы (для обратной совместимости)"""
    user = await db.get_user(callback.from_user.id)
    if not user:
        await callback.answer("Сначала зарегистрируйтесь!", show_alert=True)
        return
    
    if user.get('is_banned'):
        await callback.answer("Вы заблокированы!", show_alert=True)
        return
    
    # Проверяем, не в лобби ли уже
    active_lobby = await db.get_user_active_lobby(callback.from_user.id)
    if active_lobby:
        await callback.answer("Вы уже в лобби!", show_alert=True)
        return
    
    await callback.message.edit_text(
        f"{EMOJI['game']} *Создание лобби*\n\n"
        f"Выберите платформу для лобби:",
        reply_markup=get_platform_keyboard(),
        parse_mode="Markdown"
    )
    await state.set_state(LobbyStates.waiting_for_platform)


@router.callback_query(F.data.startswith("play:create_lobby:"))
async def create_lobby_with_platform(callback: CallbackQuery):
    """Создать лобби с указанной платформой"""
    platform = callback.data.split(":")[2]
    await _create_lobby(callback, platform)


@router.callback_query(LobbyStates.waiting_for_platform, F.data.startswith("platform:"))
async def create_lobby_select_platform(callback: CallbackQuery, state: FSMContext):
    """Создать лобби после выбора платформы"""
    platform = callback.data.split(":")[1]
    await state.clear()
    await _create_lobby(callback, platform)


async def _create_lobby(callback: CallbackQuery, platform: str, game_format: str = "5x5"):
    """Создать лобби"""
    user_id = callback.from_user.id
    
    format_data = GAME_FORMATS.get(game_format, GAME_FORMATS['5x5'])
    lobby_size = format_data['lobby_size']
    
    # Проверяем пати пользователя
    party_id = await db.get_user_party(user_id)
    
    # Если в пати, проверяем размер
    if party_id:
        party_members = await db.get_party_members(party_id)
        if len(party_members) > format_data['team_size']:
            await callback.answer(
                f"Ваша пати слишком большая для формата {format_data['name']}!",
                show_alert=True)
            return
    
    # Создаём лобби
    lobby_id = await db.create_lobby(user_id, platform, game_format=game_format)
    
    # Добавляем создателя в лобби
    await db.join_lobby(lobby_id, user_id, party_id)
    
    # Если пользователь в пати, добавляем всех участников пати
    if party_id:
        party_members = await db.get_party_members(party_id)
        for member in party_members:
            if member['user_id'] != user_id:
                await db.join_lobby(lobby_id, member['user_id'], party_id)
    
    lobby = await db.get_lobby(lobby_id)
    players = await db.get_lobby_players(lobby_id)
    
    user = await db.get_user(user_id)
    creator_name = format_player_name(user)
    
    await callback.message.edit_text(
        f"{EMOJI['check']} *Лобби создано!*\n\n" +
        format_lobby_info(lobby, players, creator_name),
        reply_markup=get_lobby_keyboard(lobby_id, is_creator=True, is_full=len(players) >= lobby_size),
        parse_mode="Markdown"
    )
    await callback.answer("Лобби успешно создано!")


@router.callback_query(F.data == "play:join_lobby")
async def show_available_lobbies(callback: CallbackQuery):
    """Показать доступные лобби"""
    user = await db.get_user(callback.from_user.id)
    if not user:
        await callback.answer("Сначала зарегистрируйтесь!", show_alert=True)
        return
    
    platform = user.get('platform', 'pc')
    lobbies = await db.get_active_lobbies(platform)
    
    for lobby in lobbies:
        lobby['player_count'] = await db.get_lobby_player_count(lobby['lobby_id'])
    
    if lobbies:
        await callback.message.edit_text(
            f"{EMOJI['users']} *Доступные лобби ({PLATFORMS.get(platform, platform)}):*",
            reply_markup=get_lobbies_list_keyboard(lobbies, platform),
            parse_mode="Markdown"
        )
    else:
        await callback.message.edit_text(
            f"{EMOJI['info']} Нет доступных лобби для вашей платформы.\n"
            f"Создайте своё!",
            reply_markup=get_lobbies_list_keyboard([], platform),
            parse_mode="Markdown"
        )


@router.callback_query(F.data.startswith("lobby:join:"))
async def join_lobby(callback: CallbackQuery):
    """Присоединиться к лобби"""
    lobby_id = int(callback.data.split(":")[2])
    user_id = callback.from_user.id
    
    user = await db.get_user(user_id)
    if not user:
        await callback.answer("Сначала зарегистрируйтесь!", show_alert=True)
        return
    
    if user.get('is_banned'):
        await callback.answer("Вы заблокированы!", show_alert=True)
        return
    
    lobby = await db.get_lobby(lobby_id)
    if not lobby:
        await callback.answer("Лобби не найдено!", show_alert=True)
        return
    
    if lobby['status'] != 'waiting':
        await callback.answer("Лобби уже началось или закрыто!", show_alert=True)
        return
    
    # Проверяем количество игроков с учётом формата
    game_format = lobby.get('game_format', '5x5')
    format_data = GAME_FORMATS.get(game_format, GAME_FORMATS['5x5'])
    lobby_size = format_data['lobby_size']
    
    player_count = await db.get_lobby_player_count(lobby_id)
    if player_count >= lobby_size:
        await callback.answer("Лобби заполнено!", show_alert=True)
        return
    
    # Проверяем пати
    party_id = await db.get_user_party(user_id)
    
    # Получаем текущих игроков ДО присоединения (для уведомления)
    existing_players = await db.get_lobby_players(lobby_id)
    existing_player_ids = [p['user_id'] for p in existing_players]
    
    # Пытаемся присоединиться
    success = await db.join_lobby(lobby_id, user_id, party_id)
    if not success:
        await callback.answer("Вы уже в этом лобби!", show_alert=True)
        return
    
    # Список новых присоединившихся игроков
    new_joined_ids = [user_id]
    
    # Если в пати, добавляем всех участников
    if party_id:
        party_members = await db.get_party_members(party_id)
        current_count = await db.get_lobby_player_count(lobby_id)
        
        for member in party_members:
            if member['user_id'] != user_id and current_count < lobby_size:
                joined = await db.join_lobby(lobby_id, member['user_id'], party_id)
                if joined:
                    current_count += 1
                    new_joined_ids.append(member['user_id'])
    
    # Обновляем информацию о лобби
    players = await db.get_lobby_players(lobby_id)
    creator = await db.get_user(lobby['creator_id'])
    creator_name = format_player_name(creator)
    
    is_creator = lobby['creator_id'] == user_id
    is_full = len(players) >= lobby_size
    
    # Отвечаем присоединившемуся игроку
    await callback.message.edit_text(
        f"{EMOJI['check']} *Вы присоединились к лобби!*\n\n" +
        format_lobby_info(lobby, players, creator_name),
        reply_markup=get_lobby_keyboard(lobby_id, is_creator, is_full),
        parse_mode="Markdown"
    )
    await callback.answer("Успешно!")
    
    # Уведомляем всех существующих участников лобби об обновлении
    await notify_lobby_players_update(
        callback.bot, 
        lobby_id, 
        lobby, 
        players, 
        creator_name, 
        existing_player_ids,
        new_joined_ids
    )


@router.callback_query(F.data.startswith("lobby:leave:"))
async def leave_lobby(callback: CallbackQuery):
    """Покинуть лобби"""
    lobby_id = int(callback.data.split(":")[2])
    user_id = callback.from_user.id
    
    await db.leave_lobby(lobby_id, user_id)
    
    await callback.message.edit_text(
        f"{EMOJI['check']} Вы покинули лобби.",
        parse_mode="Markdown"
    )
    await callback.answer("Вы вышли из лобби")


@router.callback_query(F.data.startswith("lobby:disband:"))
async def disband_lobby(callback: CallbackQuery):
    """Расформировать лобби"""
    lobby_id = int(callback.data.split(":")[2])
    user_id = callback.from_user.id
    
    lobby = await db.get_lobby(lobby_id)
    if not lobby:
        await callback.answer("Лобби не найдено!", show_alert=True)
        return
    
    if lobby['creator_id'] != user_id:
        await callback.answer("Только создатель может расформировать лобби!", show_alert=True)
        return
    
    await db.delete_lobby(lobby_id)
    
    await callback.message.edit_text(
        f"{EMOJI['check']} Лобби расформировано.",
        parse_mode="Markdown"
    )
    await callback.answer("Лобби удалено")


@router.callback_query(F.data.startswith("lobby:invite:"))
async def invite_to_lobby(callback: CallbackQuery):
    """Показать ссылку для приглашения в лобби"""
    lobby_id = int(callback.data.split(":")[2])
    
    bot_info = await callback.bot.get_me()
    invite_link = f"https://t.me/{bot_info.username}?start=lobby_{lobby_id}"
    
    await callback.message.answer(
        f"{EMOJI['link']} *Пригласите друзей в лобби!*\n\n"
        f"Отправьте эту ссылку друзьям:\n"
        f"`{invite_link}`\n\n"
        f"Или они могут найти лобби #{lobby_id} в списке доступных лобби.",
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("lobby:search_match:"))
async def start_lobby_search_match(callback: CallbackQuery):
    """Начать поиск матча для всех участников лобби"""
    lobby_id = int(callback.data.split(":")[2])
    user_id = callback.from_user.id
    
    lobby = await db.get_lobby(lobby_id)
    if not lobby:
        await callback.answer("Лобби не найдено!", show_alert=True)
        return
    
    # Только создатель может начать поиск
    if lobby['creator_id'] != user_id:
        await callback.answer("Только создатель лобби может начать поиск матча!", show_alert=True)
        return
    
    # Проверяем что лобби в статусе ожидания
    if lobby['status'] != 'waiting':
        await callback.answer("Лобби уже в игре или закрыто!", show_alert=True)
        return
    
    # Получаем игроков лобби
    players = await db.get_lobby_players(lobby_id)
    if not players:
        await callback.answer("В лобби нет игроков!", show_alert=True)
        return
    
    game_format = lobby.get('game_format', '5x5')
    format_data = GAME_FORMATS.get(game_format, GAME_FORMATS['5x5'])
    platform = lobby['platform']
    
    # Проверяем что никто не в очереди и не в pending матче (ready check)
    # Игроки могут быть в активных матчах - они могут искать следующий матч
    for player in players:
        if await db.is_in_queue(player['user_id']):
            player_name = format_player_name(player)
            await callback.answer(f"{player_name} уже в очереди поиска!", show_alert=True)
            return
        if await db.is_user_in_pending_match(player['user_id']):
            player_name = format_player_name(player)
            await callback.answer(f"{player_name} ожидает подтверждения матча!", show_alert=True)
            return
    
    # Удаляем лобби (освобождаем игроков)
    await db.delete_lobby(lobby_id)
    
    # Добавляем всех игроков в очередь поиска
    for player in players:
        user = await db.get_user(player['user_id'])
        if user and not user.get('is_banned'):
            party_id = await db.get_user_party(player['user_id'])
            await db.join_queue(player['user_id'], platform, user['rating'], party_id, game_format)
    
    # Уведомляем создателя
    queue_count = await db.get_queue_count(platform, game_format)
    
    from keyboards import get_queue_keyboard
    from utils import format_queue_status
    
    await callback.message.edit_text(
        f"{EMOJI['check']} *Поиск матча начат!*\n\n"
        f"{format_data['emoji']} Формат: *{format_data['name']}*\n"
        f"{EMOJI['users']} Игроков из лобби добавлено в поиск: *{len(players)}*\n\n"
        + format_queue_status(queue_count, platform, game_format),
        reply_markup=get_queue_keyboard(game_format),
        parse_mode="Markdown"
    )
    await callback.answer("Все игроки добавлены в очередь!")
    
    # Уведомляем остальных участников лобби о начале поиска
    for player in players:
        if player['user_id'] != user_id:
            try:
                await callback.bot.send_message(
                    player['user_id'],
                    f"{EMOJI['search']} *Начат поиск матча!*\n\n"
                    f"Создатель лобби запустил поиск матча.\n\n"
                    f"{format_data['emoji']} Формат: *{format_data['name']}*\n"
                    f"{EMOJI['users']} В очереди: *{queue_count}* игроков\n\n"
                    f"Ожидайте подбора соперников...",
                    reply_markup=get_queue_keyboard(game_format),
                    parse_mode="Markdown"
                )
            except Exception as e:
                logger.warning(f"Failed to notify player {player['user_id']} about search start: {e}")
    
    # Пытаемся создать матч если достаточно игроков
    from handlers.match import try_create_match_from_queue
    await try_create_match_from_queue(callback.bot, platform, game_format)


@router.callback_query(F.data.startswith("lobby:select_map:"))
async def select_map(callback: CallbackQuery):
    """Выбор карты для матча"""
    lobby_id = int(callback.data.split(":")[2])
    
    lobby = await db.get_lobby(lobby_id)
    if not lobby:
        await callback.answer("Лобби не найдено!", show_alert=True)
        return
    
    if lobby['creator_id'] != callback.from_user.id:
        await callback.answer("Только создатель может выбрать карту!", show_alert=True)
        return
    
    game_format = lobby.get('game_format', '5x5')
    format_data = GAME_FORMATS.get(game_format, GAME_FORMATS['5x5'])
    lobby_size = format_data['lobby_size']
    
    player_count = await db.get_lobby_player_count(lobby_id)
    if player_count < lobby_size:
        await callback.answer(f"Нужно {lobby_size} игроков! Сейчас: {player_count}", show_alert=True)
        return
    
    await callback.message.edit_text(
        f"{EMOJI['map']} *Выберите карту для матча:*",
        reply_markup=get_maps_keyboard(lobby_id),
        parse_mode="Markdown"
    )


@router.callback_query(F.data.startswith("map:select:"))
async def map_selected(callback: CallbackQuery):
    """Карта выбрана - начать матч"""
    parts = callback.data.split(":")
    lobby_id = int(parts[2])
    map_name = ":".join(parts[3:])  # На случай если в названии карты есть ":"
    
    await _start_match(callback, lobby_id, map_name)


@router.callback_query(F.data.startswith("map:random:"))
async def random_map_selected(callback: CallbackQuery):
    """Случайная карта выбрана"""
    lobby_id = int(callback.data.split(":")[2])
    map_name = get_random_map()
    
    await _start_match(callback, lobby_id, map_name)


async def _start_match(callback: CallbackQuery, lobby_id: int, map_name: str):
    """Начать матч с ready check"""
    from utils import balance_teams, assign_sides, calculate_team_rating
    from keyboards import get_ready_check_keyboard
    from config import READY_CHECK_TIMEOUT
    from handlers.match import ready_check_timers, ready_check_timeout_handler, handle_ready_check_failed
    import asyncio
    import logging
    
    logger = logging.getLogger(__name__)
    
    lobby = await db.get_lobby(lobby_id)
    if not lobby:
        await callback.answer("Лобби не найдено!", show_alert=True)
        return
    
    game_format = lobby.get('game_format', '5x5')
    format_data = GAME_FORMATS.get(game_format, GAME_FORMATS['5x5'])
    lobby_size = format_data['lobby_size']
    team_size = format_data['team_size']
    
    players = await db.get_lobby_players(lobby_id)
    if len(players) < lobby_size:
        await callback.answer(f"Недостаточно игроков! Нужно {lobby_size}.", show_alert=True)
        return
    
    # Проверяем что никто не в pending матче (ready check)
    # Игроки могут быть в активных матчах - они могут начать новый матч из лобби
    for player in players:
        if await db.is_user_in_pending_match(player['user_id']):
            await callback.answer("Один из игроков ожидает подтверждения матча!", show_alert=True)
            return
    
    # Балансируем команды с учётом формата
    team1, team2 = balance_teams(players, game_format)
    
    if len(team1) != team_size or len(team2) != team_size:
        await callback.answer("Ошибка балансировки команд!", show_alert=True)
        return
    
    # Назначаем стороны
    team1_side, team2_side = assign_sides()
    
    # Рассчитываем средние рейтинги
    team1_avg = calculate_team_rating(team1)
    team2_avg = calculate_team_rating(team2)
    
    # Создаём матч в статусе pending (ready check)
    match_id = await db.create_match_pending(
        lobby_id=lobby_id,
        platform=lobby['platform'],
        map_name=map_name,
        team1_start_side=team1_side,
        team2_start_side=team2_side,
        team1_avg_rating=team1_avg,
        team2_avg_rating=team2_avg,
        game_format=game_format
    )
    
    # Добавляем игроков в матч
    for player in team1:
        await db.add_match_player(match_id, player['user_id'], team=1, rating_before=player.get('rating', 1000))
    
    for player in team2:
        await db.add_match_player(match_id, player['user_id'], team=2, rating_before=player.get('rating', 1000))
    
    # Обновляем статус лобби
    await db.update_lobby_status(lobby_id, 'ready_check')
    
    # Отправляем ready check всем игрокам
    ready_text = (
        f"{EMOJI['fire']} *МАТЧ НАЙДЕН!*\n\n"
        f"{format_data['emoji']} Формат: *{format_data['name']}*\n"
        f"{EMOJI['map']} Карта: *{map_name}*\n"
        f"{EMOJI['users']} Игроков: *{lobby_size}*\n\n"
        f"{EMOJI['clock']} У вас есть *{READY_CHECK_TIMEOUT} секунд* чтобы подтвердить готовность!\n\n"
        f"Нажмите кнопку *«Готов»*, чтобы начать матч.")
    
    successful = 0
    for player in players:
        try:
            await db.create_ready_check(match_id, player['user_id'])
            msg = await callback.bot.send_message(
                player['user_id'], 
                ready_text, 
                reply_markup=get_ready_check_keyboard(match_id), 
                parse_mode="Markdown")
            await db.update_ready_check_message(match_id, player['user_id'], msg.message_id)
            successful += 1
        except Exception as e:
            logger.warning(f"Failed to notify {player['user_id']}: {e}")
    
    # Если не удалось уведомить всех, отменяем
    if successful < lobby_size:
        await handle_ready_check_failed(callback.bot, match_id, reason="notification_failed", game_format=game_format)
        await callback.answer("Не удалось уведомить всех игроков!", show_alert=True)
        return
    
    # Запускаем таймер таймаута
    task = asyncio.create_task(ready_check_timeout_handler(callback.bot, match_id, game_format))
    ready_check_timers[match_id] = task
    
    await callback.message.edit_text(
        f"{EMOJI['clock']} *Ожидание подтверждения готовности...*\n\n"
        f"{format_data['emoji']} Формат: *{format_data['name']}*\n"
        f"Все игроки должны подтвердить готовность в течение {READY_CHECK_TIMEOUT} секунд.\n\n"
        f"{EMOJI['map']} Карта: *{map_name}*",
        parse_mode="Markdown"
    )
    
    await callback.answer("Ready check отправлен всем игрокам!")
    logger.info(f"Match {match_id} ({game_format}) created from lobby {lobby_id} with ready check")


async def notify_lobby_players_update(
    bot: Bot,
    lobby_id: int,
    lobby: Dict[str, Any],
    players: List[Dict[str, Any]],
    creator_name: str,
    existing_player_ids: List[int],
    new_joined_ids: List[int]
) -> None:
    """
    Уведомить существующих участников лобби о присоединении новых игроков.
    Отправляет обновлённое сообщение со списком участников.
    
    Args:
        bot: Экземпляр бота
        lobby_id: ID лобби
        lobby: Данные лобби
        players: Актуальный список игроков в лобби
        creator_name: Имя создателя лобби
        existing_player_ids: ID игроков, которые были в лобби до присоединения
        new_joined_ids: ID игроков, которые только что присоединились
    """
    if not existing_player_ids:
        return
    
    game_format = lobby.get('game_format', '5x5')
    format_data = GAME_FORMATS.get(game_format, GAME_FORMATS['5x5'])
    lobby_size = format_data['lobby_size']
    
    is_full = len(players) >= lobby_size
    
    # Получаем имена новых игроков для уведомления
    new_players_names = []
    for player in players:
        if player['user_id'] in new_joined_ids:
            new_players_names.append(format_player_name(player))
    
    new_players_text = ", ".join(new_players_names) if new_players_names else "Новый игрок"
    
    # Отправляем уведомление каждому существующему участнику
    for player_id in existing_player_ids:
        try:
            is_creator = lobby['creator_id'] == player_id
            
            # Формируем текст уведомления
            notification_text = (
                f"{EMOJI['users']} *Обновление лобби!*\n\n"
                f"{EMOJI['check']} {new_players_text} присоединился к лобби!\n\n"
                + format_lobby_info(lobby, players, creator_name)
            )
            
            await bot.send_message(
                player_id,
                notification_text,
                reply_markup=get_lobby_keyboard(lobby_id, is_creator, is_full),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.warning(f"Failed to notify player {player_id} about lobby update: {e}")
