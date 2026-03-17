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
from config import EMOJI, MAX_RATING_DIFF, LOBBY_SIZE, READY_CHECK_TIMEOUT, GAME_FORMATS

router = Router()
logger = logging.getLogger(__name__)

ready_check_timers = {}
_match_creation_lock = asyncio.Lock()


class MatchStates(StatesGroup):
    waiting_for_screenshot = State()


@router.message(F.text.contains("Найти игру"))
async def find_game_button(message: Message):
    """Обработка кнопки Найти игру - показываем выбор формата"""
    from keyboards import get_game_format_keyboard
    
    user = await db.get_user(message.from_user.id)
    if not user:
        await message.answer(f"{EMOJI['warning']} Сначала зарегистрируйтесь командой /start")
        return
    
    if user.get('is_banned'):
        await message.answer(f"{EMOJI['lock']} Вы заблокированы!")
        return
    
    # Проверяем только pending матчи (ready check) - их нельзя пропустить
    if await db.is_user_in_pending_match(message.from_user.id):
        await message.answer(
            f"{EMOJI['warning']} *У вас есть матч, ожидающий подтверждения!*\n\nПожалуйста, подтвердите готовность.",
            parse_mode="Markdown")
        return
    
    if await db.is_in_queue(message.from_user.id):
        game_format = await db.get_user_queue_format(message.from_user.id) or "5x5"
        queue_count = await db.get_queue_count(user['platform'], game_format)
        await message.answer(format_queue_status(queue_count, user['platform'], game_format),
            reply_markup=get_queue_keyboard(game_format), parse_mode="Markdown")
        return
    
    # Показываем выбор формата игры
    await message.answer(
        f"{EMOJI['game']} *Выберите формат игры:*",
        reply_markup=get_game_format_keyboard("queue"),
        parse_mode="Markdown")


@router.callback_query(F.data == "queue:select_format")
async def select_queue_format(callback: CallbackQuery):
    """Показать выбор формата для поиска игры"""
    from keyboards import get_game_format_keyboard
    
    user = await db.get_user(callback.from_user.id)
    if not user:
        await callback.answer("Сначала зарегистрируйтесь!", show_alert=True)
        return
    
    if user.get('is_banned'):
        await callback.answer("Вы заблокированы!", show_alert=True)
        return
    
    # Проверяем только pending матчи (ready check) - их нельзя пропустить
    if await db.is_user_in_pending_match(callback.from_user.id):
        await callback.answer("Подтвердите готовность в текущем матче!", show_alert=True)
        return
    
    if await db.is_in_queue(callback.from_user.id):
        await callback.answer("Вы уже в очереди!", show_alert=True)
        return
    
    await callback.message.edit_text(
        f"{EMOJI['game']} *Выберите формат игры:*",
        reply_markup=get_game_format_keyboard("queue"),
        parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data.startswith("queue:format:"))
async def join_queue_with_format(callback: CallbackQuery):
    """Присоединиться к очереди с выбранным форматом"""
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
    # Проверяем только pending матчи (ready check) - их нельзя пропустить
    if await db.is_user_in_pending_match(callback.from_user.id):
        await callback.answer("Подтвердите готовность в текущем матче!", show_alert=True)
        return
    if await db.is_in_queue(callback.from_user.id):
        await callback.answer("Вы уже в очереди!", show_alert=True)
        return
    
    format_data = GAME_FORMATS[game_format]
    
    party_id = await db.get_user_party(callback.from_user.id)
    if party_id:
        party_members = await db.get_party_members(party_id)
        # Проверяем размер пати для формата
        if len(party_members) > format_data['team_size']:
            await callback.answer(
                f"Ваша пати слишком большая для формата {format_data['name']}! Максимум {format_data['team_size']} человек.",
                show_alert=True)
            return
        for member in party_members:
            member_user = await db.get_user(member['user_id'])
            if member_user and not member_user.get('is_banned'):
                # Проверяем только pending матчи для участников пати
                if not await db.is_user_in_pending_match(member['user_id']):
                    await db.join_queue(member['user_id'], user['platform'], member_user['rating'], party_id, game_format)
    else:
        await db.join_queue(callback.from_user.id, user['platform'], user['rating'], None, game_format)
    
    queue_count = await db.get_queue_count(user['platform'], game_format)
    await callback.message.edit_text(
        f"{EMOJI['check']} *Вы добавлены в очередь поиска!*\n\n" + format_queue_status(queue_count, user['platform'], game_format),
        reply_markup=get_queue_keyboard(game_format), parse_mode="Markdown")
    await callback.answer("Поиск начат!")
    await try_create_match_from_queue(callback.bot, user['platform'], game_format)


@router.callback_query(F.data == "queue:join")
async def join_queue_callback(callback: CallbackQuery):
    """Присоединиться к очереди (для обратной совместимости - 5x5)"""
    callback.data = "queue:format:5x5"
    await join_queue_with_format(callback)


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


@router.callback_query(F.data == "play:back")
async def play_back_callback(callback: CallbackQuery):
    """Вернуться в меню игры"""
    await callback.message.edit_text(
        f"{EMOJI['game']} *ИГРАТЬ*\n━━━━━━━━━━━━━━━━━━━━\n\nВыберите действие:",
        reply_markup=get_play_menu_keyboard(), parse_mode="Markdown")
    await callback.answer()


async def try_create_match_from_queue(bot: Bot, platform: str, game_format: str = "5x5"):
    async with _match_creation_lock:
        format_data = GAME_FORMATS.get(game_format, GAME_FORMATS['5x5'])
        match_size = format_data['match_size']
        
        queue_players = await db.get_queue_players(platform, game_format)
        if len(queue_players) < match_size:
            return
        
        # Проверяем только pending матчи - игроки в активных матчах могут искать следующий
        valid_players = [p for p in queue_players if not await db.is_user_in_pending_match(p['user_id'])]
        if len(valid_players) < match_size:
            return
        
        match_group = find_best_match_group(valid_players, MAX_RATING_DIFF, game_format)
        if not match_group and len(valid_players) >= match_size:
            match_group = valid_players[:match_size]
        if not match_group:
            return
        
        await create_match_with_ready_check(bot, match_group, platform, game_format)


async def create_match_with_ready_check(bot: Bot, players: list, platform: str, game_format: str = "5x5"):
    format_data = GAME_FORMATS.get(game_format, GAME_FORMATS['5x5'])
    match_size = format_data['match_size']
    team_size = format_data['team_size']
    
    # Проверяем только pending матчи - игроки в активных матчах могут участвовать в ready check
    for player in players:
        if await db.is_user_in_pending_match(player['user_id']):
            logger.warning(f"Player {player['user_id']} already in pending match")
            return
    
    team1, team2 = balance_teams(players, game_format)
    if len(team1) != team_size or len(team2) != team_size:
        logger.error(f"Team balancing failed for {game_format}: team1={len(team1)}, team2={len(team2)}")
        return
    
    team1_side, team2_side = assign_sides()
    map_name = get_random_map()
    team1_avg = calculate_team_rating(team1)
    team2_avg = calculate_team_rating(team2)
    
    lobby_id = await db.create_lobby(0, platform, is_private=True, game_format=game_format)
    match_id = await db.create_match_pending(
        lobby_id=lobby_id, platform=platform, map_name=map_name,
        team1_start_side=team1_side, team2_start_side=team2_side,
        team1_avg_rating=team1_avg, team2_avg_rating=team2_avg,
        game_format=game_format)
    
    for player in team1:
        await db.add_match_player(match_id, player['user_id'], team=1, rating_before=player.get('rating', 1000))
    for player in team2:
        await db.add_match_player(match_id, player['user_id'], team=2, rating_before=player.get('rating', 1000))
    
    await db.clear_queue_for_users([p['user_id'] for p in players])
    await db.update_lobby_status(lobby_id, 'ready_check')
    
    ready_text = (
        f"{EMOJI['fire']} *МАТЧ НАЙДЕН!*\n\n"
        f"{format_data['emoji']} Формат: *{format_data['name']}*\n"
        f"{EMOJI['map']} Карта: *{map_name}*\n"
        f"{EMOJI['users']} Игроков: *{match_size}*\n\n"
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
    
    if successful < match_size:
        await handle_ready_check_failed(bot, match_id, reason="notification_failed", game_format=game_format)
        return
    
    task = asyncio.create_task(ready_check_timeout_handler(bot, match_id, game_format))
    ready_check_timers[match_id] = task
    logger.info(f"Match {match_id} ({game_format}) created, {successful} players notified")


async def ready_check_timeout_handler(bot: Bot, match_id: int, game_format: str = "5x5"):
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


async def handle_ready_check_failed(bot: Bot, match_id: int, reason: str, declined_by: int = None, game_format: str = "5x5"):
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
    
    # Получаем формат из матча для правильного возврата в очередь
    match_game_format = match.get('game_format', '5x5')
    
    for player in ready:
        if player['user_id'] != declined_by:
            user = await db.get_user(player['user_id'])
            if user and not user.get('is_banned'):
                party_id = await db.get_user_party(player['user_id'])
                await db.join_queue(player['user_id'], match['platform'], user['rating'], party_id, match_game_format)
    
    await db.cancel_match(match_id)
    await try_create_match_from_queue(bot, match['platform'], match_game_format)


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
    from config import AI_VERIFICATION_ENABLED
    
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
    
    # Если включена AI проверка, запускаем анализ
    if AI_VERIFICATION_ENABLED:
        await message.answer(
            f"{EMOJI['check']} *Скриншот получен!*\n\n"
            f"🤖 Запускаю AI анализ результатов...\n"
            f"Это займёт несколько секунд.",
            parse_mode="Markdown")
        
        # Запускаем AI анализ в фоне
        asyncio.create_task(
            process_ai_verification(message.bot, submission_id, match_id, photo.file_id)
        )
    else:
        await message.answer(
            f"{EMOJI['check']} *Скриншот отправлен на проверку!*\n\n"
            f"Номер заявки: #{submission_id}\nМатч: #{match_id}\n\n"
            f"Модераторы проверят результаты и обновят статистику.",
            parse_mode="Markdown")


async def process_ai_verification(bot, submission_id: int, match_id: int, photo_file_id: str):
    """Обработка AI проверки скриншота"""
    import json
    from ai_verification import analyze_match_screenshot, download_and_encode_photo, format_ai_result_for_admin, is_valid_match_screenshot
    from keyboards import get_ai_verification_keyboard, get_ai_invalid_screenshot_keyboard
    
    try:
        # Получаем данные матча
        match = await db.get_match(match_id)
        if not match:
            logger.error(f"Match {match_id} not found for AI verification")
            return
        
        team1_players = await db.get_match_players(match_id, team=1)
        team2_players = await db.get_match_players(match_id, team=2)
        
        # Скачиваем и кодируем изображение
        image_base64 = await download_and_encode_photo(bot, photo_file_id)
        if not image_base64:
            logger.error(f"Failed to download photo for submission {submission_id}")
            await notify_admins_manual_check(bot, submission_id, match_id, "Не удалось скачать изображение")
            return
        
        # Запускаем AI анализ
        ai_result = await analyze_match_screenshot(
            image_base64=image_base64,
            team1_players=team1_players,
            team2_players=team2_players,
            team1_side=match.get('team1_start_side', 'Атака'),
            team2_side=match.get('team2_start_side', 'Защита'),
            map_name=match.get('map_name', 'Неизвестно')
        )
        
        # Сохраняем результат AI в базу
        verification_id = await db.create_ai_verification(
            submission_id=submission_id,
            match_id=match_id,
            ai_result=json.dumps(ai_result, ensure_ascii=False),
            confidence=ai_result.get('confidence', 0),
            team1_score=ai_result.get('team1_score'),
            team2_score=ai_result.get('team2_score'),
            winner_team=ai_result.get('winner_team'),
            mvp_user_id=ai_result.get('mvp_user_id')
        )
        
        # Формируем сообщение для админов
        admin_text = format_ai_result_for_admin(ai_result, match, team1_players, team2_players)
        
        # Выбираем клавиатуру в зависимости от валидности скриншота
        if ai_result.get('is_valid_screenshot') == False:
            # Невалидный скриншот - специальная клавиатура
            keyboard = get_ai_invalid_screenshot_keyboard(verification_id, match_id, submission_id)
        else:
            # Валидный скриншот - обычная клавиатура
            keyboard = get_ai_verification_keyboard(verification_id, match_id)
        
        # Отправляем уведомления всем админам и модераторам
        admins = await db.get_all_admins_and_moderators()
        
        submission = await db.get_submission(submission_id)
        
        for admin in admins:
            try:
                # Отправляем скриншот с результатами AI
                await bot.send_photo(
                    chat_id=admin['user_id'],
                    photo=photo_file_id,
                    caption=(
                        f"📷 *Новая заявка #{submission_id}*\n"
                        f"Матч: #{match_id}\n"
                        f"━━━━━━━━━━━━━━━━━━━━\n\n"
                        f"{admin_text}"
                    ),
                    reply_markup=keyboard,
                    parse_mode="Markdown"
                )
            except Exception as e:
                logger.warning(f"Failed to notify admin {admin['user_id']}: {e}")
        
        # Логируем результат
        is_valid = ai_result.get('is_valid_screenshot', True)
        screenshot_type = ai_result.get('screenshot_type', 'unknown')
        logger.info(f"AI verification completed for submission {submission_id}: valid={is_valid}, type={screenshot_type}, confidence={ai_result.get('confidence', 0)}")
        
    except Exception as e:
        logger.error(f"AI verification error for submission {submission_id}: {e}")
        await notify_admins_manual_check(bot, submission_id, match_id, str(e))


async def notify_admins_manual_check(bot, submission_id: int, match_id: int, error_reason: str):
    """Уведомить админов о необходимости ручной проверки"""
    from keyboards import get_submission_review_keyboard
    
    admins = await db.get_all_admins_and_moderators()
    submission = await db.get_submission(submission_id)
    
    if not submission:
        return
    
    for admin in admins:
        try:
            await bot.send_photo(
                chat_id=admin['user_id'],
                photo=submission['screenshot_file_id'],
                caption=(
                    f"📷 *Новая заявка #{submission_id}*\n"
                    f"Матч: #{match_id}\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"🤖 *AI анализ не удался*\n"
                    f"Причина: {error_reason}\n\n"
                    f"⚠️ Требуется ручная проверка!"
                ),
                reply_markup=get_submission_review_keyboard(submission_id, match_id),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.warning(f"Failed to notify admin {admin['user_id']}: {e}")


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
        game_format = await db.get_user_queue_format(message.from_user.id) or "5x5"
        queue_count = await db.get_queue_count(user['platform'], game_format)
        await message.answer(format_queue_status(queue_count, user['platform'], game_format),
            reply_markup=get_queue_keyboard(game_format), parse_mode="Markdown")
        return
    
    active_lobby = await db.get_user_active_lobby(message.from_user.id)
    if active_lobby:
        from keyboards import get_lobby_keyboard
        from utils import format_lobby_info
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
