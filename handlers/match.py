from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import asyncio
from datetime import datetime
import logging

import database as db
from keyboards import (
    get_match_keyboard, get_queue_keyboard, get_play_menu_keyboard,
    get_ready_check_keyboard, get_ready_check_accepted_keyboard,
    get_ready_check_declined_keyboard, get_ready_check_timeout_keyboard
)
from utils import (
    format_match_info, format_match_result, format_queue_status,
    balance_teams, assign_sides, get_random_map, calculate_team_rating,
    find_best_match_group, format_player_name
)
from config import EMOJI, MAX_RATING_DIFF, LOBBY_SIZE, READY_CHECK_TIMEOUT

router = Router()
logger = logging.getLogger(__name__)

ready_check_timers = {}
_match_creation_lock = asyncio.Lock()


class MatchStates(StatesGroup):
    waiting_for_screenshot = State()


@router.message(F.text.contains("Найти игру"))
async def find_game_button(message: Message):
    """Обработка кнопки Найти игру"""
    user = await db.get_user(message.from_user.id)
    if not user:
        await message.answer(f"{EMOJI['warning']} Сначала зарегистрируйтесь командой /start")
        return
    
    if user.get('is_banned'):
        await message.answer(f"{EMOJI['lock']} Вы заблокированы!")
        return
    
    if await db.is_user_in_active_or_pending_match(message.from_user.id):
        active_match = await db.get_user_active_match(message.from_user.id)
        if active_match:
            team1 = await db.get_match_players(active_match['match_id'], team=1)
            team2 = await db.get_match_players(active_match['match_id'], team=2)
            await message.answer(
                f"{EMOJI['sword']} *У вас есть активный матч!*\n\n" + format_match_info(active_match, team1, team2),
                reply_markup=get_match_keyboard(active_match['match_id']), parse_mode="Markdown")
        else:
            await message.answer(
                f"{EMOJI['warning']} *У вас есть матч, ожидающий подтверждения!*\n\nПожалуйста, подтвердите готовность.",
                parse_mode="Markdown")
        return
    
    if await db.is_in_queue(message.from_user.id):
        queue_count = await db.get_queue_count(user['platform'])
        await message.answer(format_queue_status(queue_count, user['platform']),
            reply_markup=get_queue_keyboard(), parse_mode="Markdown")
        return
    
    party_id = await db.get_user_party(message.from_user.id)
    if party_id:
        party_members = await db.get_party_members(party_id)
        for member in party_members:
            member_user = await db.get_user(member['user_id'])
            if member_user and not member_user.get('is_banned'):
                if not await db.is_user_in_active_or_pending_match(member['user_id']):
                    await db.join_queue(member['user_id'], user['platform'], member_user['rating'], party_id)
    else:
        await db.join_queue(message.from_user.id, user['platform'], user['rating'], None)
    
    queue_count = await db.get_queue_count(user['platform'])
    await message.answer(
        f"{EMOJI['check']} *Вы добавлены в очередь поиска!*\n\n" + format_queue_status(queue_count, user['platform']),
        reply_markup=get_queue_keyboard(), parse_mode="Markdown")
    await try_create_match_from_queue(message.bot, user['platform'])


@router.callback_query(F.data == "queue:join")
async def join_queue_callback(callback: CallbackQuery):
    user = await db.get_user(callback.from_user.id)
    if not user:
        await callback.answer("Сначала зарегистрируйтесь!", show_alert=True)
        return
    if user.get('is_banned'):
        await callback.answer("Вы заблокированы!", show_alert=True)
        return
    if await db.is_user_in_active_or_pending_match(callback.from_user.id):
        await callback.answer("У вас есть активный матч!", show_alert=True)
        return
    if await db.is_in_queue(callback.from_user.id):
        await callback.answer("Вы уже в очереди!", show_alert=True)
        return
    
    party_id = await db.get_user_party(callback.from_user.id)
    if party_id:
        party_members = await db.get_party_members(party_id)
        for member in party_members:
            member_user = await db.get_user(member['user_id'])
            if member_user and not member_user.get('is_banned'):
                if not await db.is_user_in_active_or_pending_match(member['user_id']):
                    await db.join_queue(member['user_id'], user['platform'], member_user['rating'], party_id)
    else:
        await db.join_queue(callback.from_user.id, user['platform'], user['rating'], None)
    
    queue_count = await db.get_queue_count(user['platform'])
    await callback.message.edit_text(
        f"{EMOJI['check']} *Вы добавлены в очередь поиска!*\n\n" + format_queue_status(queue_count, user['platform']),
        reply_markup=get_queue_keyboard(), parse_mode="Markdown")
    await callback.answer("Поиск начат!")
    await try_create_match_from_queue(callback.bot, user['platform'])


@router.callback_query(F.data == "queue:leave")
async def leave_queue_callback(callback: CallbackQuery):
    party_id = await db.get_user_party(callback.from_user.id)
    if party_id:
        party_members = await db.get_party_members(party_id)
        for member in party_members:
            await db.leave_queue(member['user_id'])
    else:
        await db.leave_queue(callback.from_user.id)
    await callback.message.edit_text(f"{EMOJI['cross']} *Поиск отменён*\n\nВы вышли из очереди.", parse_mode="Markdown")
    await callback.answer("Поиск отменён")


async def try_create_match_from_queue(bot: Bot, platform: str):
    async with _match_creation_lock:
        queue_players = await db.get_queue_players(platform)
        if len(queue_players) < LOBBY_SIZE:
            return
        
        valid_players = [p for p in queue_players if not await db.is_user_in_active_or_pending_match(p['user_id'])]
        if len(valid_players) < LOBBY_SIZE:
            return
        
        match_group = find_best_match_group(valid_players, MAX_RATING_DIFF)
        if not match_group and len(valid_players) >= LOBBY_SIZE:
            match_group = valid_players[:LOBBY_SIZE]
        if not match_group:
            return
        
        await create_match_with_ready_check(bot, match_group, platform)


async def create_match_with_ready_check(bot: Bot, players: list, platform: str):
    for player in players:
        if await db.is_user_in_active_or_pending_match(player['user_id']):
            logger.warning(f"Player {player['user_id']} already in match")
            return
    
    team1, team2 = balance_teams(players)
    if len(team1) != 5 or len(team2) != 5:
        logger.error("Team balancing failed")
        return
    
    team1_side, team2_side = assign_sides()
    map_name = get_random_map()
    team1_avg = calculate_team_rating(team1)
    team2_avg = calculate_team_rating(team2)
    
    lobby_id = await db.create_lobby(0, platform, is_private=True)
    match_id = await db.create_match_pending(
        lobby_id=lobby_id, platform=platform, map_name=map_name,
        team1_start_side=team1_side, team2_start_side=team2_side,
        team1_avg_rating=team1_avg, team2_avg_rating=team2_avg)
    
    for player in team1:
        await db.add_match_player(match_id, player['user_id'], team=1, rating_before=player.get('rating', 1000))
    for player in team2:
        await db.add_match_player(match_id, player['user_id'], team=2, rating_before=player.get('rating', 1000))
    
    await db.clear_queue_for_users([p['user_id'] for p in players])
    await db.update_lobby_status(lobby_id, 'ready_check')
    
    ready_text = (
        f"{EMOJI['fire']} *МАТЧ НАЙДЕН!*\n\n"
        f"{EMOJI['map']} Карта: *{map_name}*\n"
        f"{EMOJI['users']} Игроков: *10*\n\n"
        f"{EMOJI['clock']} У вас есть *{READY_CHECK_TIMEOUT} секунд* чтобы подтвердить готовность!\n\n"
        f"Нажмите кнопку *«Готов»*, чтобы начать матч.")
    
    successful = 0
    for player in players:
        try:
            await db.create_ready_check(match_id, player['user_id'])
            msg = await bot.send_message(player['user_id'], ready_text, 
                reply_markup=get_ready_check_keyboard(match_id), parse_mode="Markdown")
            await db.update_ready_check_message(match_id, player['user_id'], msg.message_id)
            successful += 1
        except Exception as e:
            logger.warning(f"Failed to notify {player['user_id']}: {e}")
    
    if successful < LOBBY_SIZE:
        await handle_ready_check_failed(bot, match_id, reason="notification_failed")
        return
    
    task = asyncio.create_task(ready_check_timeout_handler(bot, match_id))
    ready_check_timers[match_id] = task
    logger.info(f"Match {match_id} created, {successful} players notified")


async def ready_check_timeout_handler(bot: Bot, match_id: int):
    try:
        await asyncio.sleep(READY_CHECK_TIMEOUT)
        match = await db.get_match(match_id)
        if match and match['status'] == 'pending':
            logger.info(f"Ready check timeout for match {match_id}")
            await handle_ready_check_failed(bot, match_id, reason="timeout")
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error(f"Timeout handler error: {e}")
    finally:
        ready_check_timers.pop(match_id, None)


@router.callback_query(F.data.startswith("ready:accept:"))
async def ready_check_accept(callback: CallbackQuery):
    try:
        match_id = int(callback.data.split(":")[2])
    except (IndexError, ValueError):
        await callback.answer("Ошибка!", show_alert=True)
        return
    
    result = await db.set_player_ready_and_check(match_id, callback.from_user.id)
    
    if not result['success']:
        error = result.get('error', 'unknown')
        messages = {
            'match_not_found': "Матч не найден!",
            'match_not_pending': "Матч уже начался или отменён!",
            'player_not_in_match': "Вы не участник этого матча!",
            'already_ready': "Вы уже подтвердили готовность!"
        }
        await callback.answer(messages.get(error, "Ошибка!"), show_alert=True)
        return
    
    try:
        await callback.message.edit_text(
            f"{EMOJI['check']} *Вы подтвердили готовность!*\n\n"
            f"Готовы: *{result['ready_count']}/{result['total_count']}* игроков\n\n"
            f"Ожидание остальных...", reply_markup=get_ready_check_accepted_keyboard(), parse_mode="Markdown")
    except Exception:
        pass
    
    await callback.answer("Готовность подтверждена!")
    
    if result['all_ready']:
        started = await db.try_start_match_atomically(match_id)
        if started:
            await start_match_after_ready_check(callback.bot, match_id)


@router.callback_query(F.data.startswith("ready:decline:"))
async def ready_check_decline(callback: CallbackQuery):
    try:
        match_id = int(callback.data.split(":")[2])
    except (IndexError, ValueError):
        await callback.answer("Ошибка!", show_alert=True)
        return
    
    player_check = await db.get_player_ready_check(match_id, callback.from_user.id)
    if not player_check:
        await callback.answer("Вы не участник этого матча!", show_alert=True)
        return
    
    match = await db.get_match(match_id)
    if not match or match['status'] != 'pending':
        await callback.answer("Матч уже начался или отменён!", show_alert=True)
        return
    
    try:
        await callback.message.edit_text(
            f"{EMOJI['cross']} *Вы отказались от матча*\n\nВы вернулись в главное меню.",
            reply_markup=get_ready_check_declined_keyboard(), parse_mode="Markdown")
    except Exception:
        pass
    
    await callback.answer("Вы отказались от матча")
    await handle_ready_check_failed(callback.bot, match_id, reason="declined", declined_by=callback.from_user.id)


@router.callback_query(F.data == "ready:already_accepted")
async def ready_already_accepted(callback: CallbackQuery):
    await callback.answer("Вы уже подтвердили готовность. Ожидайте остальных.", show_alert=True)


@router.callback_query(F.data == "ready:already_declined")
async def ready_already_declined(callback: CallbackQuery):
    await callback.answer("Вы уже отказались от матча.", show_alert=True)


@router.callback_query(F.data == "ready:timeout")
async def ready_timeout_click(callback: CallbackQuery):
    await callback.answer("Время на подтверждение истекло.", show_alert=True)


async def handle_ready_check_failed(bot: Bot, match_id: int, reason: str, declined_by: int = None):
    if match_id in ready_check_timers:
        ready_check_timers[match_id].cancel()
        ready_check_timers.pop(match_id, None)
    
    match = await db.get_match(match_id)
    if not match:
        return
    
    ready_status = await db.get_ready_check_status(match_id)
    players = ready_status['players']
    not_ready = [p for p in players if not p['is_ready']]
    ready = [p for p in players if p['is_ready']]
    
    if reason == "declined":
        declined_user = await db.get_user(declined_by)
        declined_name = format_player_name(declined_user) if declined_user else "Игрок"
        fail_text = f"{EMOJI['cross']} *МАТЧ ОТМЕНЁН*\n\n{declined_name} отказался от матча.\n\nГотовые игроки возвращены в очередь."
    elif reason == "notification_failed":
        fail_text = f"{EMOJI['warning']} *МАТЧ ОТМЕНЁН*\n\nНе удалось уведомить всех игроков."
    else:
        not_ready_names = [format_player_name(await db.get_user(p['user_id'])) for p in not_ready]
        fail_text = (f"{EMOJI['clock']} *ВРЕМЯ ВЫШЛО*\n\nНе все игроки подтвердили готовность.\n\n"
                    f"Не подтвердили: {', '.join(not_ready_names)}\n\nГотовые игроки возвращены в очередь.")
    
    for player in players:
        try:
            if player['user_id'] == declined_by:
                kb = get_ready_check_declined_keyboard()
            elif reason == "timeout" and not player['is_ready']:
                kb = get_ready_check_timeout_keyboard()
            else:
                kb = None
            
            if player.get('message_id'):
                try:
                    await bot.edit_message_text(chat_id=player['user_id'], message_id=player['message_id'],
                        text=fail_text, reply_markup=kb, parse_mode="Markdown")
                except Exception:
                    await bot.send_message(player['user_id'], fail_text, parse_mode="Markdown")
            else:
                await bot.send_message(player['user_id'], fail_text, parse_mode="Markdown")
        except Exception as e:
            logger.warning(f"Failed to notify {player['user_id']}: {e}")
    
    for player in ready:
        if player['user_id'] != declined_by:
            user = await db.get_user(player['user_id'])
            if user and not user.get('is_banned'):
                party_id = await db.get_user_party(player['user_id'])
                await db.join_queue(player['user_id'], match['platform'], user['rating'], party_id)
    
    await db.cancel_match(match_id)
    await try_create_match_from_queue(bot, match['platform'])


async def start_match_after_ready_check(bot: Bot, match_id: int):
    if match_id in ready_check_timers:
        ready_check_timers[match_id].cancel()
        ready_check_timers.pop(match_id, None)
    
    match = await db.get_match(match_id)
    team1_players = await db.get_match_players(match_id, team=1)
    team2_players = await db.get_match_players(match_id, team=2)
    
    if match.get('lobby_id'):
        await db.update_lobby_status(match['lobby_id'], 'in_match')
    
    match_text = (
        f"{EMOJI['fire']} *МАТЧ НАЧИНАЕТСЯ!*\n\n"
        f"Все игроки подтвердили готовность!\n\n" +
        format_match_info(match, team1_players, team2_players))
    
    ready_status = await db.get_ready_check_status(match_id)
    for player in ready_status['players']:
        try:
            if player.get('message_id'):
                try:
                    await bot.edit_message_text(
                        chat_id=player['user_id'], message_id=player['message_id'],
                        text=match_text, reply_markup=get_match_keyboard(match_id), parse_mode="Markdown")
                except Exception:
                    await bot.send_message(player['user_id'], match_text,
                        reply_markup=get_match_keyboard(match_id), parse_mode="Markdown")
            else:
                await bot.send_message(player['user_id'], match_text,
                    reply_markup=get_match_keyboard(match_id), parse_mode="Markdown")
        except Exception as e:
            logger.warning(f"Failed to notify {player['user_id']} about match start: {e}")
    
    await db.delete_ready_checks(match_id)
    logger.info(f"Match {match_id} started after ready check")


# ============ MATCH HANDLERS ============

@router.callback_query(F.data.startswith("match:info:"))
async def show_match_info(callback: CallbackQuery):
    try:
        match_id = int(callback.data.split(":")[2])
    except (IndexError, ValueError):
        await callback.answer("Ошибка!", show_alert=True)
        return
    
    match = await db.get_match(match_id)
    if not match:
        await callback.answer("Матч не найден!", show_alert=True)
        return
    
    team1 = await db.get_match_players(match_id, team=1)
    team2 = await db.get_match_players(match_id, team=2)
    
    if match['status'] == 'finished':
        text = format_match_result(match, team1, team2)
    else:
        text = format_match_info(match, team1, team2)
    
    await callback.message.edit_text(
        text, reply_markup=get_match_keyboard(match_id) if match['status'] == 'active' else None,
        parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data.startswith("match:submit:"))
async def request_screenshot(callback: CallbackQuery, state: FSMContext):
    try:
        match_id = int(callback.data.split(":")[2])
    except (IndexError, ValueError):
        await callback.answer("Ошибка!", show_alert=True)
        return
    
    match = await db.get_match(match_id)
    if not match:
        await callback.answer("Матч не найден!", show_alert=True)
        return
    
    if match['status'] != 'active':
        await callback.answer("Матч уже завершён или ещё не начался!", show_alert=True)
        return
    
    players = await db.get_match_players(match_id)
    user_ids = [p['user_id'] for p in players]
    
    if callback.from_user.id not in user_ids:
        await callback.answer("Вы не участник этого матча!", show_alert=True)
        return
    
    await state.update_data(match_id=match_id)
    await state.set_state(MatchStates.waiting_for_screenshot)
    
    await callback.message.answer(
        f"{EMOJI['camera']} *Отправка результатов матча*\n\n"
        f"Пожалуйста, отправьте скриншот с результатами матча.\n\n"
        f"{EMOJI['info']} На скриншоте должны быть видны:\n"
        f"• Финальный счёт\n• Статистика игроков (K/D/A)\n• MVP матча (если есть)\n\n"
        f"{EMOJI['warning']} *Важно:* Помните, что стороны меняются после 15 раунда!",
        parse_mode="Markdown")
    await callback.answer()


@router.message(MatchStates.waiting_for_screenshot, F.photo)
async def receive_screenshot(message: Message, state: FSMContext):
    data = await state.get_data()
    match_id = data.get('match_id')
    
    if not match_id:
        await message.answer(f"{EMOJI['warning']} Ошибка: матч не найден.")
        await state.clear()
        return
    
    match = await db.get_match(match_id)
    if not match:
        await message.answer(f"{EMOJI['warning']} Матч не найден!")
        await state.clear()
        return
    
    photo = message.photo[-1]
    submission_id = await db.create_submission(match_id, message.from_user.id, photo.file_id)
    
    await state.clear()
    await message.answer(
        f"{EMOJI['check']} *Скриншот отправлен на проверку!*\n\n"
        f"Номер заявки: #{submission_id}\nМатч: #{match_id}\n\n"
        f"Модераторы проверят результаты и обновят статистику.",
        parse_mode="Markdown")


@router.message(MatchStates.waiting_for_screenshot)
async def invalid_screenshot(message: Message):
    await message.answer(f"{EMOJI['warning']} Пожалуйста, отправьте *фотографию* результатов матча.", parse_mode="Markdown")


@router.message(F.text.contains("Играть"))
async def show_play_menu(message: Message):
    user = await db.get_user(message.from_user.id)
    if not user:
        await message.answer(f"{EMOJI['warning']} Сначала зарегистрируйтесь командой /start")
        return
    
    if await db.is_user_in_active_or_pending_match(message.from_user.id):
        active_match = await db.get_user_active_match(message.from_user.id)
        if active_match:
            team1 = await db.get_match_players(active_match['match_id'], team=1)
            team2 = await db.get_match_players(active_match['match_id'], team=2)
            await message.answer(
                f"{EMOJI['sword']} *У вас есть активный матч!*\n\n" + format_match_info(active_match, team1, team2),
                reply_markup=get_match_keyboard(active_match['match_id']), parse_mode="Markdown")
        else:
            await message.answer(
                f"{EMOJI['warning']} *У вас есть матч, ожидающий подтверждения!*",
                parse_mode="Markdown")
        return
    
    if await db.is_in_queue(message.from_user.id):
        queue_count = await db.get_queue_count(user['platform'])
        await message.answer(format_queue_status(queue_count, user['platform']),
            reply_markup=get_queue_keyboard(), parse_mode="Markdown")
        return
    
    active_lobby = await db.get_user_active_lobby(message.from_user.id)
    if active_lobby:
        from keyboards import get_lobby_keyboard
        from utils import format_lobby_info
        lobby = await db.get_lobby(active_lobby)
        players = await db.get_lobby_players(active_lobby)
        creator = await db.get_user(lobby['creator_id'])
        creator_name = format_player_name(creator) if creator else "Неизвестно"
        is_creator = lobby['creator_id'] == message.from_user.id
        is_full = len(players) >= 10
        await message.answer(
            f"{EMOJI['info']} *Вы уже в лобби!*\n\n" + format_lobby_info(lobby, players, creator_name),
            reply_markup=get_lobby_keyboard(active_lobby, is_creator, is_full), parse_mode="Markdown")
        return
    
    await message.answer(
        f"{EMOJI['game']} *ИГРАТЬ*\n━━━━━━━━━━━━━━━━━━━━\n\nВыберите действие:",
        reply_markup=get_play_menu_keyboard(), parse_mode="Markdown")


@router.callback_query(F.data == "play:find_match")
async def find_match_callback(callback: CallbackQuery):
    callback.data = "queue:join"
    await join_queue_callback(callback)
