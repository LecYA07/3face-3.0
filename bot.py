import asyncio
import logging
import os
from datetime import datetime
from aiogram import Bot, Dispatcher, F, Router
from aiogram.types import Message
from aiogram.filters import CommandStart, Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import (
    BOT_TOKEN, EMOJI, WEBAPP_HOST, WEBAPP_PORT, 
    SSL_CERT_PATH, SSL_KEY_PATH, DATABASE_PATH, ADMIN_IDS
)
from database import (
    init_db, create_user, get_user, join_lobby, get_lobby, 
    join_party, get_party, get_party_members, update_user_game_info, is_user_registered,
    is_registration_closed, ban_user, log_blocked_registration_attempt, 
    get_all_admins_and_moderators, get_all_banned_users, cancel_all_user_matches
)
from keyboards import get_main_menu_keyboard, get_party_invite_keyboard
from utils import format_welcome_message, format_player_name, format_lobby_info, format_party_info

# Импортируем роутеры
from handlers.lobby import router as lobby_router
from handlers.match import router as match_router
from handlers.admin import router as admin_router
from handlers.profile import router as profile_router
from handlers.ticket import router as ticket_router
from handlers.webapp import router as webapp_router

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Состояния для регистрации
class RegistrationStates(StatesGroup):
    waiting_for_nickname = State()
    waiting_for_game_id = State()


async def cancel_banned_users_matches():
    """
    Проверить всех забаненных игроков и отменить их матчи.
    Вызывается при старте бота для обеспечения консистентности данных.
    """
    try:
        banned_users = await get_all_banned_users()
        
        if not banned_users:
            logger.info("Нет забаненных пользователей для проверки матчей")
            return
        
        total_cancelled = 0
        affected_users = []
        
        for user in banned_users:
            user_id = user['user_id']
            result = await cancel_all_user_matches(user_id)
            
            if result['cancelled_count'] > 0:
                total_cancelled += result['cancelled_count']
                affected_users.append({
                    'user_id': user_id,
                    'username': user.get('username'),
                    'cancelled_count': result['cancelled_count'],
                    'match_ids': result['match_ids']
                })
                logger.info(
                    f"Отменено {result['cancelled_count']} матчей забаненного игрока "
                    f"{user_id} (@{user.get('username', 'unknown')})"
                )
        
        if total_cancelled > 0:
            logger.info(
                f"Всего отменено {total_cancelled} матчей у {len(affected_users)} забаненных игроков"
            )
        else:
            logger.info("Матчей для отмены у забаненных игроков не найдено")
            
    except Exception as e:
        logger.error(f"Ошибка при отмене матчей забаненных игроков: {e}")


async def main():
    """Главная функция запуска бота"""
    
    # Проверяем токен
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN не установлен! Создайте файл .env с токеном бота.")
        return
    
    # Инициализируем базу данных
    await init_db()
    logger.info("База данных инициализирована")
    
    # Проверяем забаненных игроков и отменяем их матчи
    await cancel_banned_users_matches()
    
    # Создаём бота и диспетчер
    bot = Bot(token=BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Регистрируем роутеры
    # ВАЖНО: ticket_router должен быть в начале, чтобы FSM состояния 
    # (ожидание ответа на тикет) имели приоритет над другими хендлерами
    dp.include_router(ticket_router)
    dp.include_router(admin_router)
    dp.include_router(lobby_router)
    dp.include_router(match_router)
    dp.include_router(profile_router)
    dp.include_router(webapp_router)
    
    # Обработчик команды /start
    @dp.message(CommandStart())
    async def cmd_start(message: Message, state: FSMContext):
        """Обработка команды /start"""
        user_id = message.from_user.id
        username = message.from_user.username
        full_name = message.from_user.full_name
        
        # Проверяем deep link
        args = message.text.split()
        if len(args) > 1:
            deep_link = args[1]
            
            # Приглашение в лобби
            if deep_link.startswith("lobby_"):
                lobby_id = int(deep_link.replace("lobby_", ""))
                
                # Регистрируем пользователя если нужно
                await create_user(user_id, username, full_name)
                
                # Проверяем регистрацию
                if not await is_user_registered(user_id):
                    await state.update_data(pending_lobby=lobby_id)
                    await start_registration(message, state)
                    return
                
                lobby = await get_lobby(lobby_id)
                if lobby and lobby['status'] == 'waiting':
                    from database import get_user_party, get_lobby_player_count, get_lobby_players
                    
                    player_count = await get_lobby_player_count(lobby_id)
                    if player_count < 10:
                        party_id = await get_user_party(user_id)
                        success = await join_lobby(lobby_id, user_id, party_id)
                        
                        if success:
                            players = await get_lobby_players(lobby_id)
                            creator = await get_user(lobby['creator_id'])
                            creator_name = format_player_name(creator) if creator else "Неизвестно"
                            
                            from keyboards import get_lobby_keyboard
                            
                            await message.answer(
                                f"{EMOJI['check']} *Вы присоединились к лобби!*\n\n" +
                                format_lobby_info(lobby, players, creator_name),
                                reply_markup=get_lobby_keyboard(lobby_id, is_creator=False, is_full=len(players) >= 10),
                                parse_mode="Markdown"
                            )
                            await message.answer(
                                "Используйте меню для навигации:",
                                reply_markup=get_main_menu_keyboard(is_admin=user_id in ADMIN_IDS)
                            )
                            return
                        else:
                            await message.answer(
                                f"{EMOJI['warning']} Вы уже в этом лобби или не удалось присоединиться."
                            )
                    else:
                        await message.answer(f"{EMOJI['warning']} Лобби заполнено!")
                else:
                    await message.answer(f"{EMOJI['warning']} Лобби не найдено или уже началось!")
            
            # Приглашение в пати
            elif deep_link.startswith("party_"):
                party_id = int(deep_link.replace("party_", ""))
                
                # Регистрируем пользователя если нужно
                await create_user(user_id, username, full_name)
                
                # Проверяем регистрацию
                if not await is_user_registered(user_id):
                    await state.update_data(pending_party=party_id)
                    await start_registration(message, state)
                    return
                
                party = await get_party(party_id)
                if party:
                    members = await get_party_members(party_id)
                    if len(members) < 5:
                        leader = await get_user(party['leader_id'])
                        leader_name = format_player_name(leader) if leader else "Неизвестно"
                        
                        await message.answer(
                            f"{EMOJI['party']} *Приглашение в пати!*\n\n"
                            f"Лидер: {leader_name}\n"
                            f"Участников: {len(members)}/5\n\n"
                            f"Принять приглашение?",
                            reply_markup=get_party_invite_keyboard(party_id),
                            parse_mode="Markdown"
                        )
                        await message.answer(
                            "Используйте меню для навигации:",
                            reply_markup=get_main_menu_keyboard(is_admin=user_id in ADMIN_IDS)
                        )
                        return
                    else:
                        await message.answer(f"{EMOJI['warning']} Пати заполнено!")
                else:
                    await message.answer(f"{EMOJI['warning']} Пати не найдено!")
        
        # Обычный /start - проверяем регистрацию
        await create_user(user_id, username, full_name)
        
        # Проверяем, завершена ли регистрация
        if not await is_user_registered(user_id):
            await start_registration(message, state)
            return
        
        await message.answer(
            format_welcome_message(full_name),
            reply_markup=get_main_menu_keyboard(is_admin=user_id in ADMIN_IDS),
            parse_mode="Markdown"
        )
    
    async def notify_admins_blocked_registration(user_id: int, username: str, full_name: str):
        """Уведомить админов о попытке регистрации при закрытой регистрации"""
        try:
            admins = await get_all_admins_and_moderators()
            
            user_info = f"ID: `{user_id}`"
            if username:
                user_info += f"\nUsername: @{username}"
            if full_name:
                user_info += f"\nИмя: {full_name}"
            
            notification_text = (
                f"🚫 *ПОПЫТКА РЕГИСТРАЦИИ ПРИ ЗАКРЫТОЙ РЕГИСТРАЦИИ*\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"👤 *Пользователь:*\n{user_info}\n\n"
                f"⚠️ Пользователь автоматически *ЗАБАНЕН*!\n\n"
                f"📅 Время: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"
            )
            
            for admin in admins:
                try:
                    await bot.send_message(
                        chat_id=admin['user_id'],
                        text=notification_text,
                        parse_mode="Markdown"
                    )
                except Exception as e:
                    logger.warning(f"Failed to notify admin {admin['user_id']}: {e}")
        except Exception as e:
            logger.error(f"Error notifying admins about blocked registration: {e}")
    
    async def start_registration(message: Message, state: FSMContext):
        """Начать процесс регистрации"""
        user_id = message.from_user.id
        username = message.from_user.username
        full_name = message.from_user.full_name
        
        # Проверяем, закрыта ли регистрация
        if await is_registration_closed():
            # Баним пользователя за попытку регистрации при закрытой регистрации
            await ban_user(user_id)
            
            # Логируем попытку
            await log_blocked_registration_attempt(
                user_id=user_id,
                username=username,
                full_name=full_name,
                ban_applied=True
            )
            
            # Уведомляем админов
            await notify_admins_blocked_registration(user_id, username, full_name)
            
            # Сообщаем пользователю
            await message.answer(
                f"🚫 *РЕГИСТРАЦИЯ ЗАКРЫТА*\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"В данный момент регистрация новых пользователей временно закрыта.\n\n"
                f"⚠️ *Ваш аккаунт был автоматически заблокирован* за попытку регистрации в период закрытия.\n\n"
                f"Если вы считаете, что это ошибка, обратитесь к администрации.",
                parse_mode="Markdown"
            )
            
            await state.clear()
            return
        
        await state.set_state(RegistrationStates.waiting_for_nickname)
        await message.answer(
            f"{EMOJI['user']} *РЕГИСТРАЦИЯ*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Добро пожаловать! Для начала игры необходимо завершить регистрацию.\n\n"
            f"{EMOJI['target']} *Шаг 1/2*\n"
            f"Введите ваш игровой ник:\n\n"
            f"⚠️ *Ник должен совпадать с ником в игре!*",
            parse_mode="Markdown"
        )
    
    @dp.message(RegistrationStates.waiting_for_nickname)
    async def process_nickname(message: Message, state: FSMContext):
        """Обработка ввода игрового ника"""
        nickname = message.text.strip()
        
        if len(nickname) < 2:
            await message.answer(
                f"{EMOJI['warning']} Ник слишком короткий! Минимум 2 символа.",
                parse_mode="Markdown"
            )
            return
        
        if len(nickname) > 32:
            await message.answer(
                f"{EMOJI['warning']} Ник слишком длинный! Максимум 32 символа.",
                parse_mode="Markdown"
            )
            return
        
        await state.update_data(game_nickname=nickname)
        await state.set_state(RegistrationStates.waiting_for_game_id)
        
        await message.answer(
            f"{EMOJI['check']} Ник принят: *{nickname}*\n\n"
            f"{EMOJI['target']} *Шаг 2/2*\n"
            f"Теперь введите ваш *игровой ID*:\n\n"
            f"{EMOJI['info']} Это уникальный идентификатор вашего аккаунта в игре.",
            parse_mode="Markdown"
        )
    
    @dp.message(RegistrationStates.waiting_for_game_id)
    async def process_game_id(message: Message, state: FSMContext):
        """Обработка ввода игрового ID"""
        game_id = message.text.strip()
        
        if len(game_id) < 1:
            await message.answer(
                f"{EMOJI['warning']} ID не может быть пустым!",
                parse_mode="Markdown"
            )
            return
        
        if len(game_id) > 64:
            await message.answer(
                f"{EMOJI['warning']} ID слишком длинный! Максимум 64 символа.",
                parse_mode="Markdown"
            )
            return
        
        data = await state.get_data()
        game_nickname = data.get('game_nickname')
        
        # Сохраняем данные в БД
        await update_user_game_info(message.from_user.id, game_nickname, game_id)
        
        await state.clear()
        
        # Проверяем, есть ли отложенные действия
        pending_lobby = data.get('pending_lobby')
        pending_party = data.get('pending_party')
        
        await message.answer(
            f"{EMOJI['check']} *Регистрация завершена!*\n\n"
            f"{EMOJI['user']} Ник: *{game_nickname}*\n"
            f"{EMOJI['target']} ID: *{game_id}*\n\n"
            f"Теперь вы можете начать играть!",
            reply_markup=get_main_menu_keyboard(is_admin=message.from_user.id in ADMIN_IDS),
            parse_mode="Markdown"
        )
        
        # Обрабатываем отложенные действия
        if pending_lobby:
            lobby = await get_lobby(pending_lobby)
            if lobby and lobby['status'] == 'waiting':
                from database import get_user_party, get_lobby_player_count, get_lobby_players
                
                player_count = await get_lobby_player_count(pending_lobby)
                if player_count < 10:
                    party_id = await get_user_party(message.from_user.id)
                    success = await join_lobby(pending_lobby, message.from_user.id, party_id)
                    
                    if success:
                        players = await get_lobby_players(pending_lobby)
                        creator = await get_user(lobby['creator_id'])
                        creator_name = format_player_name(creator) if creator else "Неизвестно"
                        
                        from keyboards import get_lobby_keyboard
                        
                        await message.answer(
                            f"{EMOJI['check']} *Вы присоединились к лобби!*\n\n" +
                            format_lobby_info(lobby, players, creator_name),
                            reply_markup=get_lobby_keyboard(pending_lobby, is_creator=False, is_full=len(players) >= 10),
                            parse_mode="Markdown"
                        )
        
        if pending_party:
            party = await get_party(pending_party)
            if party:
                members = await get_party_members(pending_party)
                if len(members) < 5:
                    leader = await get_user(party['leader_id'])
                    leader_name = format_player_name(leader) if leader else "Неизвестно"
                    
                    await message.answer(
                        f"{EMOJI['party']} *Приглашение в пати!*\n\n"
                        f"Лидер: {leader_name}\n"
                        f"Участников: {len(members)}/5\n\n"
                        f"Принять приглашение?",
                        reply_markup=get_party_invite_keyboard(pending_party),
                        parse_mode="Markdown"
                    )
    
    # Обработчик команды /help
    @dp.message(Command("help"))
    async def cmd_help(message: Message):
        """Обработка команды /help"""
        help_text = f"""
{EMOJI['info']} *ПОМОЩЬ*
━━━━━━━━━━━━━━━━━━━━

{EMOJI['game']} *Основные команды:*
/start - Начать работу с ботом
/help - Показать эту справку
/admin - Панель модератора (для модераторов)

{EMOJI['target']} *Как играть:*
1. Нажмите "{EMOJI['game']} Играть"
2. Создайте лобби или присоединитесь к существующему
3. Дождитесь 10 игроков
4. Создатель лобби выбирает карту
5. Бот автоматически разделит команды
6. После матча отправьте скриншот результатов

{EMOJI['users']} *Пати:*
Создайте пати, чтобы всегда играть в одной команде с друзьями!

{EMOJI['trophy']} *Рейтинг:*
• Победа: +25 очков
• Поражение: -20 очков
• MVP: +5 очков дополнительно

{EMOJI['warning']} *Поддержка:*
Если возникли проблемы, обратитесь к администраторам.
"""
        await message.answer(help_text, parse_mode="Markdown")
    
    # Создаём отдельный роутер для fallback обработчика (должен быть последним)
    fallback_router = Router()
    
    @fallback_router.message()
    async def unknown_message(message: Message, state: FSMContext):
        """Обработка неизвестных сообщений"""
        # Проверяем, в состоянии ли пользователь
        current_state = await state.get_state()
        if current_state:
            return  # Пропускаем, если пользователь в процессе регистрации
        
        # Проверяем, зарегистрирован ли пользователь
        user = await get_user(message.from_user.id)
        if not user:
            await message.answer(
                f"{EMOJI['warning']} Сначала зарегистрируйтесь командой /start",
                reply_markup=get_main_menu_keyboard(is_admin=message.from_user.id in ADMIN_IDS)
            )
            return
        
        # Проверяем, завершена ли регистрация
        if not await is_user_registered(message.from_user.id):
            await start_registration(message, state)
            return
        
        await message.answer(
            f"{EMOJI['info']} Используйте кнопки меню для навигации.",
            reply_markup=get_main_menu_keyboard(is_admin=message.from_user.id in ADMIN_IDS)
        )
    
    # Регистрируем fallback роутер ПОСЛЕДНИМ
    dp.include_router(fallback_router)
    
    # Запускаем веб-приложение Mini App
    webapp_runner = None
    if os.path.exists(SSL_CERT_PATH) and os.path.exists(SSL_KEY_PATH):
        try:
            from webapp.server import run_webapp
            webapp_runner = await run_webapp(
                bot_token=BOT_TOKEN,
                host=WEBAPP_HOST,
                port=WEBAPP_PORT,
                cert_path=SSL_CERT_PATH,
                key_path=SSL_KEY_PATH,
                db_path=DATABASE_PATH
            )
            logger.info(f"Mini App сервер запущен на порту {WEBAPP_PORT}")
        except Exception as e:
            logger.warning(f"Не удалось запустить Mini App сервер: {e}")
    else:
        logger.warning("SSL сертификаты не найдены. Mini App сервер не запущен.")
    
    # Запускаем бота
    logger.info("Бот запускается...")
    
    try:
        await dp.start_polling(bot)
    finally:
        if webapp_runner:
            await webapp_runner.cleanup()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())