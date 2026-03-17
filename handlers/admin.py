from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import shutil
import os
from datetime import datetime

import database as db
from keyboards import (
    get_admin_menu_keyboard, get_submission_review_keyboard,
    get_team_winner_keyboard, get_mvp_selection_keyboard
)
from utils import format_match_info, calculate_rating_change, calculate_team_rating
from config import EMOJI, RATING_MVP_BONUS, DATABASE_PATH

router = Router()


class AdminStates(StatesGroup):
    entering_score = State()
    selecting_mvp = State()
    entering_player_stats = State()


async def is_admin(user_id: int) -> bool:
    """Проверить, является ли пользователь администратором"""
    return await db.is_user_admin(user_id)


async def is_moderator(user_id: int) -> bool:
    """Проверить, является ли пользователь модератором"""
    return await db.is_user_moderator(user_id)


@router.message(F.text == "/admin")
async def admin_panel(message: Message):
    """Панель администратора"""
    if not await is_moderator(message.from_user.id):
        await message.answer(f"{EMOJI['lock']} У вас нет доступа к админ-панели.")
        return
    
    pending = await db.get_pending_submissions()
    
    await message.answer(
        f"{EMOJI['gear']} *ПАНЕЛЬ МОДЕРАТОРА*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{EMOJI['camera']} Заявок на проверку: *{len(pending)}*\n\n"
        f"Выберите действие:",
        reply_markup=get_admin_menu_keyboard(),
        parse_mode="Markdown"
    )


@router.callback_query(F.data == "admin:submissions")
async def show_submissions(callback: CallbackQuery):
    """Показать заявки на проверку"""
    if not await is_moderator(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return
    
    submissions = await db.get_pending_submissions()
    
    if not submissions:
        await callback.message.edit_text(
            f"{EMOJI['check']} *Нет заявок на проверку*\n\n"
            f"Все результаты матчей обработаны.",
            reply_markup=get_admin_menu_keyboard(),
            parse_mode="Markdown"
        )
        return
    
    # Показываем первую заявку
    submission = submissions[0]
    
    await callback.message.answer_photo(
        photo=submission['screenshot_file_id'],
        caption=(
            f"{EMOJI['camera']} *Заявка #{submission['submission_id']}*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{EMOJI['game']} Матч: #{submission['match_id']}\n"
            f"{EMOJI['map']} Карта: {submission.get('map_name', 'Неизвестно')}\n"
            f"{EMOJI['user']} Отправил: @{submission.get('submitter_name', 'unknown')}\n"
            f"{EMOJI['chart']} Рейтинг команд: {submission.get('team1_avg_rating', 0)} vs {submission.get('team2_avg_rating', 0)}\n\n"
            f"Выберите действие:"
        ),
        reply_markup=get_submission_review_keyboard(
            submission['submission_id'], 
            submission['match_id']
        ),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("submission:approve:"))
async def approve_submission(callback: CallbackQuery, state: FSMContext):
    """Одобрить заявку и перейти к вводу результатов"""
    if not await is_moderator(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return
    
    parts = callback.data.split(":")
    submission_id = int(parts[2])
    match_id = int(parts[3])
    
    # Сохраняем данные в состояние
    await state.update_data(
        submission_id=submission_id,
        match_id=match_id,
        reviewer_id=callback.from_user.id
    )
    
    # Показываем информацию о матче и запрашиваем победителя
    match = await db.get_match(match_id)
    team1 = await db.get_match_players(match_id, team=1)
    team2 = await db.get_match_players(match_id, team=2)
    
    # Формируем список игроков без Markdown-проблем
    def format_player(p):
        username = p.get('username') or p.get('game_nickname') or 'игрок'
        rating = p.get('rating_before', p.get('rating', 0))
        return f"  • {username} [{rating}]"
    
    team1_list = "\n".join([format_player(p) for p in team1])
    team2_list = "\n".join([format_player(p) for p in team2])
    
    await callback.message.answer(
        f"{EMOJI['target']} <b>Ввод результатов матча #{match_id}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{EMOJI['map']} Карта: {match['map_name']}\n\n"
        f"{EMOJI['red']} <b>Команда 1</b> ({match['team1_start_side']}):\n"
        f"Средний рейтинг: {match.get('team1_avg_rating', 0)}\n"
        f"{team1_list}\n\n"
        f"{EMOJI['blue']} <b>Команда 2</b> ({match['team2_start_side']}):\n"
        f"Средний рейтинг: {match.get('team2_avg_rating', 0)}\n"
        f"{team2_list}\n\n"
        f"{EMOJI['info']} <b>Выберите команду-победителя:</b>",
        reply_markup=get_team_winner_keyboard(match_id),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("result:winner:"))
async def select_winner(callback: CallbackQuery, state: FSMContext):
    """Выбрать победителя и запросить счёт"""
    if not await is_moderator(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return
    
    parts = callback.data.split(":")
    match_id = int(parts[2])
    winner_team = int(parts[3])
    
    await state.update_data(winner_team=winner_team, match_id=match_id)
    await state.set_state(AdminStates.entering_score)
    
    winner_text = "Команда 1" if winner_team == 1 else "Команда 2"
    
    await callback.message.edit_text(
        f"{EMOJI['trophy']} Победитель: *{winner_text}*\n\n"
        f"{EMOJI['target']} Введите счёт матча в формате:\n"
        f"`счёт_команды1:счёт_команды2`\n\n"
        f"Например: `16:14` или `13:16`",
        parse_mode="Markdown"
    )
    await callback.answer()


@router.message(AdminStates.entering_score)
async def enter_score(message: Message, state: FSMContext):
    """Ввести счёт матча"""
    if not await is_moderator(message.from_user.id):
        return
    
    try:
        score_parts = message.text.strip().split(":")
        team1_score = int(score_parts[0])
        team2_score = int(score_parts[1])
    except (ValueError, IndexError):
        await message.answer(
            f"{EMOJI['warning']} Неверный формат! Введите счёт в формате `16:14`",
            parse_mode="Markdown"
        )
        return
    
    data = await state.get_data()
    match_id = data.get('match_id')
    
    await state.update_data(team1_score=team1_score, team2_score=team2_score)
    
    # Получаем всех игроков матча для выбора MVP
    all_players = await db.get_match_players(match_id)
    
    await state.set_state(AdminStates.selecting_mvp)
    
    await message.answer(
        f"{EMOJI['star']} *Выберите MVP матча:*\n\n"
        f"Счёт: {team1_score}:{team2_score}",
        reply_markup=get_mvp_selection_keyboard(match_id, all_players),
        parse_mode="Markdown"
    )


@router.callback_query(AdminStates.selecting_mvp, F.data.startswith("result:mvp:"))
async def select_mvp(callback: CallbackQuery, state: FSMContext):
    """Выбрать MVP и завершить обработку матча"""
    if not await is_moderator(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return
    
    parts = callback.data.split(":")
    match_id = int(parts[2])
    mvp_user_id = int(parts[3])  # 0 если без MVP
    
    data = await state.get_data()
    winner_team = data.get('winner_team')
    team1_score = data.get('team1_score')
    team2_score = data.get('team2_score')
    submission_id = data.get('submission_id')
    
    # Получаем информацию о матче
    match = await db.get_match(match_id)
    team1_avg = match.get('team1_avg_rating', 1000)
    team2_avg = match.get('team2_avg_rating', 1000)
    
    # Определяем рейтинги команд
    if winner_team == 1:
        winner_rating = team1_avg
        loser_rating = team2_avg
    else:
        winner_rating = team2_avg
        loser_rating = team1_avg
    
    # Обновляем результат матча
    await db.update_match_result(match_id, team1_score, team2_score, winner_team)
    
    # Обновляем статистику игроков
    team1_players = await db.get_match_players(match_id, team=1)
    team2_players = await db.get_match_players(match_id, team=2)
    
    # Команда 1
    for player in team1_players:
        is_winner = winner_team == 1
        is_mvp = player['user_id'] == mvp_user_id
        rating_change = calculate_rating_change(winner_rating, loser_rating, is_winner, is_mvp)
        
        await db.update_match_player_stats(
            match_id=match_id,
            user_id=player['user_id'],
            kills=0,
            deaths=0,
            assists=0,
            is_mvp=is_mvp,
            rating_change=rating_change
        )
        
        await db.update_user_stats(
            user_id=player['user_id'],
            wins=1 if is_winner else 0,
            losses=0 if is_winner else 1,
            rating_change=rating_change,
            is_mvp=is_mvp
        )
    
    # Команда 2
    for player in team2_players:
        is_winner = winner_team == 2
        is_mvp = player['user_id'] == mvp_user_id
        rating_change = calculate_rating_change(winner_rating, loser_rating, is_winner, is_mvp)
        
        await db.update_match_player_stats(
            match_id=match_id,
            user_id=player['user_id'],
            kills=0,
            deaths=0,
            assists=0,
            is_mvp=is_mvp,
            rating_change=rating_change
        )
        
        await db.update_user_stats(
            user_id=player['user_id'],
            wins=1 if is_winner else 0,
            losses=0 if is_winner else 1,
            rating_change=rating_change,
            is_mvp=is_mvp
        )
    
    # Обновляем статус заявки
    if submission_id:
        await db.update_submission_status(submission_id, 'approved', callback.from_user.id)
    
    await state.clear()
    
    winner_text = "Команда 1" if winner_team == 1 else "Команда 2"
    mvp_text = f"MVP: User ID {mvp_user_id}" if mvp_user_id else "Без MVP"
    
    await callback.message.edit_text(
        f"{EMOJI['check']} *Результаты матча #{match_id} сохранены!*\n\n"
        f"{EMOJI['trophy']} Победитель: *{winner_text}*\n"
        f"{EMOJI['target']} Счёт: *{team1_score}:{team2_score}*\n"
        f"{EMOJI['star']} {mvp_text}\n\n"
        f"Статистика игроков обновлена.\n"
        f"Рейтинг рассчитан с учётом разницы команд.",
        parse_mode="Markdown"
    )
    await callback.answer("Матч обработан!")


@router.callback_query(F.data.startswith("submission:reject:"))
async def reject_submission(callback: CallbackQuery):
    """Отклонить заявку"""
    if not await is_moderator(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return
    
    submission_id = int(callback.data.split(":")[2])
    
    await db.update_submission_status(submission_id, 'rejected', callback.from_user.id)
    
    await callback.message.edit_caption(
        caption=f"{EMOJI['cross']} *Заявка #{submission_id} отклонена*\n\n"
        f"Игрок должен отправить новый скриншот.",
        parse_mode="Markdown"
    )
    await callback.answer("Заявка отклонена")


@router.callback_query(F.data.startswith("submission:details:"))
async def show_match_details(callback: CallbackQuery):
    """Показать детали матча"""
    if not await is_moderator(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return
    
    match_id = int(callback.data.split(":")[2])
    
    match = await db.get_match(match_id)
    if not match:
        await callback.answer("Матч не найден!", show_alert=True)
        return
    
    team1 = await db.get_match_players(match_id, team=1)
    team2 = await db.get_match_players(match_id, team=2)
    
    await callback.message.answer(
        format_match_info(match, team1, team2),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data == "admin:stats")
async def show_admin_stats(callback: CallbackQuery):
    """Показать статистику"""
    if not await is_moderator(callback.from_user.id):
        await callback.answer("Нет доступа!", show_alert=True)
        return
    
    import aiosqlite
    from config import DATABASE_PATH
    
    async with aiosqlite.connect(DATABASE_PATH) as db_conn:
        async with db_conn.execute("SELECT COUNT(*) FROM users") as cursor:
            users_count = (await cursor.fetchone())[0]
        
        async with db_conn.execute("SELECT COUNT(*) FROM matches") as cursor:
            matches_count = (await cursor.fetchone())[0]
        
        async with db_conn.execute("SELECT COUNT(*) FROM matches WHERE status = 'active'") as cursor:
            active_matches = (await cursor.fetchone())[0]
        
        async with db_conn.execute("SELECT COUNT(*) FROM match_submissions WHERE status = 'pending'") as cursor:
            pending_submissions = (await cursor.fetchone())[0]
        
        async with db_conn.execute("SELECT COUNT(*) FROM lobbies WHERE status = 'waiting'") as cursor:
            active_lobbies = (await cursor.fetchone())[0]
        
        async with db_conn.execute("SELECT COUNT(*) FROM matchmaking_queue") as cursor:
            queue_count = (await cursor.fetchone())[0]
    
    await callback.message.edit_text(
        f"{EMOJI['chart']} *СТАТИСТИКА*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{EMOJI['users']} Пользователей: *{users_count}*\n"
        f"{EMOJI['game']} Всего матчей: *{matches_count}*\n"
        f"{EMOJI['sword']} Активных матчей: *{active_matches}*\n"
        f"{EMOJI['users']} Активных лобби: *{active_lobbies}*\n"
        f"{EMOJI['search']} В очереди поиска: *{queue_count}*\n"
        f"{EMOJI['camera']} Ожидают проверки: *{pending_submissions}*",
        reply_markup=get_admin_menu_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data == "admin:bans")
async def show_ban_menu(callback: CallbackQuery):
    """Показать меню банов"""
    if not await is_admin(callback.from_user.id):
        await callback.answer("Только для администраторов!", show_alert=True)
        return
    
    await callback.message.edit_text(
        f"{EMOJI['lock']} <b>УПРАВЛЕНИЕ БАНАМИ</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Используйте команды:\n\n"
        f"<code>/ban @username</code> - забанить игрока\n"
        f"<code>/unban @username</code> - разбанить игрока\n\n"
        f"Или укажите user_id:\n"
        f"<code>/ban 123456789</code>",
        reply_markup=get_admin_menu_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "admin:roles")
async def show_roles_menu(callback: CallbackQuery):
    """Показать меню управления ролями"""
    if not await is_admin(callback.from_user.id):
        await callback.answer("Только для администраторов!", show_alert=True)
        return
    
    await callback.message.edit_text(
        f"{EMOJI['crown']} *УПРАВЛЕНИЕ РОЛЯМИ*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"*Команды для администраторов:*\n"
        f"`/addadmin @username` - назначить админа\n"
        f"`/removeadmin @username` - снять админа\n\n"
        f"*Команды для модераторов:*\n"
        f"`/addmod @username` - назначить модератора\n"
        f"`/removemod @username` - снять модератора\n\n"
        f"*Управление рейтингом:*\n"
        f"`/addrating @username 100` - добавить рейтинг\n"
        f"`/removerating @username 50` - снять рейтинг\n"
        f"`/setrating @username 1500` - установить рейтинг",
        reply_markup=get_admin_menu_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()


# ============ ADMIN COMMANDS ============

@router.message(F.text.startswith("/ban"))
async def ban_user_command(message: Message):
    """Забанить пользователя"""
    if not await is_admin(message.from_user.id):
        await message.answer(f"{EMOJI['lock']} Только для администраторов!")
        return
    
    args = message.text.split()
    if len(args) < 2:
        await message.answer(
            f"{EMOJI['warning']} Укажите пользователя!\n"
            f"Пример: `/ban @username` или `/ban 123456789`",
            parse_mode="Markdown"
        )
        return
    
    target = args[1]
    user = await _get_target_user(target)
    
    if not user:
        await message.answer(f"{EMOJI['warning']} Пользователь не найден!")
        return
    
    await db.ban_user(user['user_id'])
    await message.answer(
        f"{EMOJI['check']} Пользователь `{user['user_id']}` (@{user.get('username', 'unknown')}) забанен.",
        parse_mode="Markdown"
    )


@router.message(F.text.startswith("/unban"))
async def unban_user_command(message: Message):
    """Разбанить пользователя"""
    if not await is_admin(message.from_user.id):
        await message.answer(f"{EMOJI['lock']} Только для администраторов!")
        return
    
    args = message.text.split()
    if len(args) < 2:
        await message.answer(
            f"{EMOJI['warning']} Укажите пользователя!\n"
            f"Пример: `/unban @username` или `/unban 123456789`",
            parse_mode="Markdown"
        )
        return
    
    target = args[1]
    user = await _get_target_user(target)
    
    if not user:
        await message.answer(f"{EMOJI['warning']} Пользователь не найден!")
        return
    
    await db.unban_user(user['user_id'])
    await message.answer(
        f"{EMOJI['check']} Пользователь `{user['user_id']}` (@{user.get('username', 'unknown')}) разбанен.",
        parse_mode="Markdown"
    )


@router.message(F.text.startswith("/addadmin"))
async def add_admin_command(message: Message):
    """Назначить администратора"""
    if not await is_admin(message.from_user.id):
        await message.answer(f"{EMOJI['lock']} Только для администраторов!")
        return
    
    args = message.text.split()
    if len(args) < 2:
        await message.answer(
            f"{EMOJI['warning']} Укажите пользователя!\n"
            f"Пример: <code>/addadmin @username</code>",
            parse_mode="HTML"
        )
        return
    
    target = args[1]
    user = await _get_target_user(target)
    
    if not user:
        await message.answer(f"{EMOJI['warning']} Пользователь не найден!")
        return
    
    await db.set_user_admin(user['user_id'], True)
    username = user.get('username') or 'без username'
    await message.answer(
        f"{EMOJI['crown']} Пользователь {user['user_id']} ({username}) назначен администратором."
    )


@router.message(F.text.startswith("/removeadmin"))
async def remove_admin_command(message: Message):
    """Снять права администратора"""
    if not await is_admin(message.from_user.id):
        await message.answer(f"{EMOJI['lock']} Только для администраторов!")
        return
    
    args = message.text.split()
    if len(args) < 2:
        await message.answer(
            f"{EMOJI['warning']} Укажите пользователя!\n"
            f"Пример: `/removeadmin @username`",
            parse_mode="Markdown"
        )
        return
    
    target = args[1]
    user = await _get_target_user(target)
    
    if not user:
        await message.answer(f"{EMOJI['warning']} Пользователь не найден!")
        return
    
    await db.set_user_admin(user['user_id'], False)
    await message.answer(
        f"{EMOJI['check']} С пользователя `{user['user_id']}` сняты права администратора.",
        parse_mode="Markdown"
    )


@router.message(F.text.startswith("/addmod"))
async def add_moderator_command(message: Message):
    """Назначить модератора"""
    if not await is_admin(message.from_user.id):
        await message.answer(f"{EMOJI['lock']} Только для администраторов!")
        return
    
    args = message.text.split()
    if len(args) < 2:
        await message.answer(
            f"{EMOJI['warning']} Укажите пользователя!\n"
            f"Пример: /addmod @username",
            parse_mode="Markdown"
        )
        return
    
    target = args[1]
    user = await _get_target_user(target)
    
    if not user:
        await message.answer(f"{EMOJI['warning']} Пользователь не найден!")
        return
    
    await db.set_user_moderator(user['user_id'], True)
    username = user.get('username') or 'без username'
    await message.answer(
        f"{EMOJI['check']} Пользователь {user['user_id']} ({username}) назначен модератором."
    )


@router.message(F.text.startswith("/removemod"))
async def remove_moderator_command(message: Message):
    """Снять права модератора"""
    if not await is_admin(message.from_user.id):
        await message.answer(f"{EMOJI['lock']} Только для администраторов!")
        return
    
    args = message.text.split()
    if len(args) < 2:
        await message.answer(
            f"{EMOJI['warning']} Укажите пользователя!\n"
            f"Пример: `/removemod @username`",
            parse_mode="Markdown"
        )
        return
    
    target = args[1]
    user = await _get_target_user(target)
    
    if not user:
        await message.answer(f"{EMOJI['warning']} Пользователь не найден!")
        return
    
    await db.set_user_moderator(user['user_id'], False)
    await message.answer(
        f"{EMOJI['check']} С пользователя `{user['user_id']}` сняты права модератора.",
        parse_mode="Markdown"
    )


@router.message(F.text.startswith("/addrating"))
async def add_rating_command(message: Message):
    """Добавить рейтинг пользователю"""
    if not await is_admin(message.from_user.id):
        await message.answer(f"{EMOJI['lock']} Только для администраторов!")
        return
    
    args = message.text.split()
    if len(args) < 3:
        await message.answer(
            f"{EMOJI['warning']} Неверный формат!\n"
            f"Пример: `/addrating @username 100`",
            parse_mode="Markdown"
        )
        return
    
    target = args[1]
    try:
        amount = int(args[2])
    except ValueError:
        await message.answer(f"{EMOJI['warning']} Укажите число!")
        return
    
    user = await _get_target_user(target)
    
    if not user:
        await message.answer(f"{EMOJI['warning']} Пользователь не найден!")
        return
    
    await db.add_user_rating(user['user_id'], amount)
    updated_user = await db.get_user(user['user_id'])
    
    await message.answer(
        f"{EMOJI['up']} Пользователю @{user.get('username', 'unknown')} добавлено *{amount}* рейтинга.\n"
        f"Новый рейтинг: *{updated_user['rating']}*",
        parse_mode="Markdown"
    )


@router.message(F.text.startswith("/removerating"))
async def remove_rating_command(message: Message):
    """Снять рейтинг у пользователя"""
    if not await is_admin(message.from_user.id):
        await message.answer(f"{EMOJI['lock']} Только для администраторов!")
        return
    
    args = message.text.split()
    if len(args) < 3:
        await message.answer(
            f"{EMOJI['warning']} Неверный формат!\n"
            f"Пример: `/removerating @username 50`",
            parse_mode="Markdown"
        )
        return
    
    target = args[1]
    try:
        amount = int(args[2])
    except ValueError:
        await message.answer(f"{EMOJI['warning']} Укажите число!")
        return
    
    user = await _get_target_user(target)
    
    if not user:
        await message.answer(f"{EMOJI['warning']} Пользователь не найден!")
        return
    
    await db.add_user_rating(user['user_id'], -amount)
    updated_user = await db.get_user(user['user_id'])
    
    await message.answer(
        f"{EMOJI['down']} У пользователя @{user.get('username', 'unknown')} снято *{amount}* рейтинга.\n"
        f"Новый рейтинг: *{updated_user['rating']}*",
        parse_mode="Markdown"
    )


@router.message(F.text.startswith("/setrating"))
async def set_rating_command(message: Message):
    """Установить рейтинг пользователю"""
    if not await is_admin(message.from_user.id):
        await message.answer(f"{EMOJI['lock']} Только для администраторов!")
        return
    
    args = message.text.split()
    if len(args) < 3:
        await message.answer(
            f"{EMOJI['warning']} Неверный формат!\n"
            f"Пример: `/setrating @username 1500`",
            parse_mode="Markdown"
        )
        return
    
    target = args[1]
    try:
        new_rating = int(args[2])
    except ValueError:
        await message.answer(f"{EMOJI['warning']} Укажите число!")
        return
    
    user = await _get_target_user(target)
    
    if not user:
        await message.answer(f"{EMOJI['warning']} Пользователь не найден!")
        return
    
    old_rating = user['rating']
    await db.set_user_rating(user['user_id'], new_rating)
    
    await message.answer(
        f"{EMOJI['chart']} Рейтинг пользователя @{user.get('username', 'unknown')} изменён.\n"
        f"Было: *{old_rating}* → Стало: *{new_rating}*",
        parse_mode="Markdown"
    )


async def _get_target_user(target: str):
    """Получить пользователя по username или user_id"""
    try:
        user_id = int(target)
        return await db.get_user(user_id)
    except ValueError:
        return await db.get_user_by_username(target.replace("@", ""))


# ============ BACKUP COMMAND ============

@router.message(F.text.startswith("/backup"))
async def backup_database(message: Message):
    """Создать и отправить бэкап базы данных"""
    if not await is_admin(message.from_user.id):
        await message.answer(f"{EMOJI['lock']} Только для администраторов!")
        return
    
    try:
        # Создаём папку для бэкапов если её нет
        backup_dir = "backups"
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        
        # Формируем имя файла бэкапа
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"backup_{timestamp}.db"
        backup_path = os.path.join(backup_dir, backup_filename)
        
        # Копируем базу данных
        shutil.copy2(DATABASE_PATH, backup_path)
        
        # Получаем информацию о файле
        file_size = os.path.getsize(backup_path)
        file_size_kb = file_size / 1024
        file_size_mb = file_size_kb / 1024
        
        if file_size_mb >= 1:
            size_str = f"{file_size_mb:.2f} МБ"
        else:
            size_str = f"{file_size_kb:.2f} КБ"
        
        # Получаем статистику
        import aiosqlite
        async with aiosqlite.connect(DATABASE_PATH) as db_conn:
            async with db_conn.execute("SELECT COUNT(*) FROM users") as cursor:
                users_count = (await cursor.fetchone())[0]
            async with db_conn.execute("SELECT COUNT(*) FROM matches") as cursor:
                matches_count = (await cursor.fetchone())[0]
            async with db_conn.execute("SELECT COUNT(*) FROM lobbies") as cursor:
                lobbies_count = (await cursor.fetchone())[0]
        
        # Отправляем файл админу
        backup_file = FSInputFile(backup_path, filename=backup_filename)
        
        await message.answer_document(
            document=backup_file,
            caption=(
                f"{EMOJI['check']} *Бэкап базы данных создан!*\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"{EMOJI['info']} *Информация:*\n"
                f"📁 Файл: `{backup_filename}`\n"
                f"📊 Размер: *{size_str}*\n"
                f"🕐 Дата: *{datetime.now().strftime('%d.%m.%Y %H:%M:%S')}*\n\n"
                f"{EMOJI['chart']} *Статистика БД:*\n"
                f"👥 Пользователей: *{users_count}*\n"
                f"⚔️ Матчей: *{matches_count}*\n"
                f"🏠 Лобби: *{lobbies_count}*\n\n"
                f"{EMOJI['warning']} Храните бэкап в безопасном месте!"
            ),
            parse_mode="Markdown"
        )
        
        # Удаляем локальную копию бэкапа (опционально оставить)
        # os.remove(backup_path)
        
    except Exception as e:
        await message.answer(
            f"{EMOJI['warning']} *Ошибка создания бэкапа!*\n\n"
            f"Причина: `{str(e)}`",
            parse_mode="Markdown"
        )


# ============ UPDATE COMMAND ============

# URL для скачивания архива с GitHub
# Формат: username/repository
GITHUB_REPO = os.getenv("GITHUB_REPO", "LecYA07/3face-3.0")
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "master")

# Файлы и папки которые нужно сохранить при обновлении
PRESERVE_FILES = [".env", "database.db", "backups"]
# Файлы и папки которые НЕ нужно копировать из архива
SKIP_FILES = [".env.example", ".git", ".gitignore", "__pycache__"]


@router.message(F.text.startswith("/update"))
async def update_bot_command(message: Message):
    """Обновить бота с GitHub с сохранением БД и конфигов (без git)"""
    if not await is_admin(message.from_user.id):
        await message.answer(f"{EMOJI['lock']} Только для администраторов!")
        return
    
    import aiohttp
    import zipfile
    import io
    import sys
    
    await message.answer(
        f"{EMOJI['gear']} *Начинаю обновление бота...*\n\n"
        f"1️⃣ Создание бэкапа...",
        parse_mode="Markdown"
    )
    
    try:
        # 1. Создаём папку для бэкапов
        backup_dir = "backups"
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Бэкап базы данных
        backup_filename = f"backup_before_update_{timestamp}.db"
        backup_path = os.path.join(backup_dir, backup_filename)
        if os.path.exists(DATABASE_PATH):
            shutil.copy2(DATABASE_PATH, backup_path)
        
        # Сохраняем .env
        env_backup = None
        if os.path.exists(".env"):
            with open(".env", "r", encoding="utf-8") as f:
                env_backup = f.read()
        
        await message.answer(
            f"{EMOJI['check']} Бэкап создан\n\n"
            f"2️⃣ Скачивание обновлений с GitHub...",
            parse_mode="Markdown"
        )
        
        # 2. Скачиваем архив с GitHub
        download_url = f"https://github.com/{GITHUB_REPO}/archive/refs/heads/{GITHUB_BRANCH}.zip"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(download_url) as response:
                if response.status != 200:
                    await message.answer(
                        f"{EMOJI['warning']} Ошибка скачивания: HTTP {response.status}",
                        parse_mode="Markdown"
                    )
                    return
                
                zip_data = await response.read()
        
        await message.answer(
            f"{EMOJI['check']} Архив скачан ({len(zip_data) // 1024} КБ)\n\n"
            f"3️⃣ Распаковка и обновление файлов...",
            parse_mode="Markdown"
        )
        
        # 3. Распаковываем архив
        with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
            # Получаем имя корневой папки в архиве (обычно repo-branch)
            root_folder = zf.namelist()[0].split('/')[0]
            
            updated_files = []
            skipped_files = []
            
            for file_info in zf.infolist():
                # Пропускаем директории
                if file_info.is_dir():
                    continue
                
                # Получаем относительный путь (без корневой папки архива)
                relative_path = file_info.filename.replace(f"{root_folder}/", "", 1)
                
                if not relative_path:
                    continue
                
                # Пропускаем файлы из списка SKIP и сохраняемые файлы
                skip = False
                for skip_pattern in SKIP_FILES + PRESERVE_FILES:
                    if relative_path.startswith(skip_pattern) or relative_path == skip_pattern:
                        skip = True
                        skipped_files.append(relative_path)
                        break
                
                if skip:
                    continue
                
                # Создаём директории если нужно
                dir_path = os.path.dirname(relative_path)
                if dir_path and not os.path.exists(dir_path):
                    os.makedirs(dir_path)
                
                # Извлекаем файл
                with zf.open(file_info) as src:
                    content = src.read()
                    with open(relative_path, 'wb') as dst:
                        dst.write(content)
                
                updated_files.append(relative_path)
        
        # 4. Восстанавливаем .env
        if env_backup:
            with open(".env", "w", encoding="utf-8") as f:
                f.write(env_backup)
        
        # 5. Восстанавливаем БД
        if os.path.exists(backup_path):
            shutil.copy2(backup_path, DATABASE_PATH)
        
        await message.answer(
            f"{EMOJI['check']} Файлы обновлены\n\n"
            f"4️⃣ Установка зависимостей...",
            parse_mode="Markdown"
        )
        
        # 6. Устанавливаем зависимости
        import subprocess
        pip_result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "-q"],
            capture_output=True,
            text=True,
            cwd=os.getcwd()
        )
        
        # Формируем отчёт
        files_summary = f"Обновлено файлов: {len(updated_files)}"
        if len(updated_files) <= 10:
            files_list = "\n".join([f"  • {f}" for f in updated_files[:10]])
        else:
            files_list = "\n".join([f"  • {f}" for f in updated_files[:10]]) + f"\n  ... и ещё {len(updated_files) - 10}"
        
        await message.answer(
            f"{EMOJI['check']} *Обновление завершено!*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📦 {files_summary}\n"
            f"💾 БД сохранена: {backup_filename}\n"
            f"⚙️ .env сохранён\n"
            f"📚 Зависимости обновлены\n\n"
            f"📝 *Обновлённые файлы:*\n{files_list}\n\n"
            f"{EMOJI['warning']} *Для применения изменений требуется перезапуск!*\n\n"
            f"Используйте /restart для перезапуска бота.",
            parse_mode="Markdown"
        )
        
    except aiohttp.ClientError as e:
        await message.answer(
            f"{EMOJI['warning']} *Ошибка сети!*\n\n"
            f"Не удалось скачать обновления: {str(e)}\n\n"
            f"Проверьте подключение к интернету.",
            parse_mode="Markdown"
        )
    except Exception as e:
        await message.answer(
            f"{EMOJI['warning']} *Ошибка обновления!*\n\n"
            f"Причина: {str(e)}\n\n"
            f"База данных и конфиги сохранены в папке backups/",
            parse_mode="Markdown"
        )


@router.message(F.text.startswith("/restart"))
async def restart_bot_command(message: Message):
    """Перезапустить бота"""
    if not await is_admin(message.from_user.id):
        await message.answer(f"{EMOJI['lock']} Только для администраторов!")
        return
    
    await message.answer(
        f"{EMOJI['gear']} *Перезапуск бота...*\n\n"
        f"Бот будет перезапущен через 3 секунды.",
        parse_mode="Markdown"
    )
    
    import asyncio
    import sys
    
    await asyncio.sleep(3)
    
    # Перезапускаем процесс
    os.execv(sys.executable, [sys.executable] + sys.argv)


@router.message(F.text.startswith("/version"))
async def version_command(message: Message):
    """Показать текущую версию бота"""
    if not await is_admin(message.from_user.id):
        await message.answer(f"{EMOJI['lock']} Только для администраторов!")
        return
    
    import aiohttp
    
    try:
        # Получаем информацию о последних коммитах с GitHub API
        api_url = f"https://api.github.com/repos/{GITHUB_REPO}/commits?sha={GITHUB_BRANCH}&per_page=1"
        
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "3face-bot"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    if data and len(data) > 0:
                        commit = data[0]
                        commit_sha = commit['sha'][:7]
                        commit_msg = commit['commit']['message'].split('\n')[0][:50]
                        commit_date = commit['commit']['committer']['date'][:10]
                        author = commit['commit']['author']['name']
                        
                        await message.answer(
                            f"{EMOJI['info']} *Информация о репозитории*\n"
                            f"━━━━━━━━━━━━━━━━━━━━\n\n"
                            f"📦 Репозиторий: {GITHUB_REPO}\n"
                            f"🌿 Ветка: {GITHUB_BRANCH}\n\n"
                            f"📝 *Последний коммит:*\n"
                            f"  • SHA: `{commit_sha}`\n"
                            f"  • Дата: {commit_date}\n"
                            f"  • Автор: {author}\n"
                            f"  • Сообщение: {commit_msg}",
                            parse_mode="Markdown"
                        )
                    else:
                        await message.answer(
                            f"{EMOJI['warning']} Коммиты не найдены.",
                            parse_mode="Markdown"
                        )
                else:
                    await message.answer(
                        f"{EMOJI['warning']} Не удалось получить информацию о версии.\n"
                        f"HTTP статус: {response.status}",
                        parse_mode="Markdown"
                    )
    except Exception as e:
        await message.answer(
            f"{EMOJI['warning']} Ошибка: {str(e)}"
        )


@router.callback_query(F.data == "admin:backup")
async def backup_database_callback(callback: CallbackQuery):
    """Создать бэкап через кнопку в админ-панели"""
    if not await is_admin(callback.from_user.id):
        await callback.answer("Только для администраторов!", show_alert=True)
        return
    
    try:
        # Создаём папку для бэкапов если её нет
        backup_dir = "backups"
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        
        # Формируем имя файла бэкапа
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"backup_{timestamp}.db"
        backup_path = os.path.join(backup_dir, backup_filename)
        
        # Копируем базу данных
        shutil.copy2(DATABASE_PATH, backup_path)
        
        # Получаем информацию о файле
        file_size = os.path.getsize(backup_path)
        file_size_kb = file_size / 1024
        file_size_mb = file_size_kb / 1024
        
        if file_size_mb >= 1:
            size_str = f"{file_size_mb:.2f} МБ"
        else:
            size_str = f"{file_size_kb:.2f} КБ"
        
        # Получаем статистику
        import aiosqlite
        async with aiosqlite.connect(DATABASE_PATH) as db_conn:
            async with db_conn.execute("SELECT COUNT(*) FROM users") as cursor:
                users_count = (await cursor.fetchone())[0]
            async with db_conn.execute("SELECT COUNT(*) FROM matches") as cursor:
                matches_count = (await cursor.fetchone())[0]
            async with db_conn.execute("SELECT COUNT(*) FROM lobbies") as cursor:
                lobbies_count = (await cursor.fetchone())[0]
        
        # Отправляем файл админу
        backup_file = FSInputFile(backup_path, filename=backup_filename)
        
        await callback.message.answer_document(
            document=backup_file,
            caption=(
                f"{EMOJI['check']} *Бэкап базы данных создан!*\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"{EMOJI['info']} *Информация:*\n"
                f"📁 Файл: `{backup_filename}`\n"
                f"📊 Размер: *{size_str}*\n"
                f"🕐 Дата: *{datetime.now().strftime('%d.%m.%Y %H:%M:%S')}*\n\n"
                f"{EMOJI['chart']} *Статистика БД:*\n"
                f"👥 Пользователей: *{users_count}*\n"
                f"⚔️ Матчей: *{matches_count}*\n"
                f"🏠 Лобби: *{lobbies_count}*\n\n"
                f"{EMOJI['warning']} Храните бэкап в безопасном месте!"
            ),
            parse_mode="Markdown"
        )
        
        await callback.answer("Бэкап создан и отправлен!")
        
    except Exception as e:
        await callback.message.answer(
            f"{EMOJI['warning']} *Ошибка создания бэкапа!*\n\n"
            f"Причина: `{str(e)}`",
            parse_mode="Markdown"
        )
        await callback.answer("Ошибка!", show_alert=True)
