import asyncio
import logging
from aiogram import Bot, Dispatcher, F, Router
from aiogram.types import Message
from aiogram.filters import CommandStart, Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import BOT_TOKEN, EMOJI
from database import (
    init_db, create_user, get_user, join_lobby, get_lobby, 
    join_party, get_party, get_party_members, update_user_game_info, is_user_registered
)
from keyboards import get_main_menu_keyboard, get_party_invite_keyboard
from utils import format_welcome_message, format_player_name, format_lobby_info, format_party_info

# Импортируем роутеры
from handlers.lobby import router as lobby_router
from handlers.match import router as match_router
from handlers.admin import router as admin_router
from handlers.profile import router as profile_router
from handlers.ticket import router as ticket_router

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


async def main():
    """Главная функция запуска бота"""
    
    # Проверяем токен
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN не установлен! Создайте файл .env с токеном бота.")
        return
    
    # Инициализируем базу данных
    await init_db()
    logger.info("База данных инициализирована")
    
    # Создаём бота и диспетчер
    bot = Bot(token=BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Регистрируем роутеры
    dp.include_router(lobby_router)
    dp.include_router(match_router)
    dp.include_router(admin_router)
    dp.include_router(profile_router)
    dp.include_router(ticket_router)
    
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
                                reply_markup=get_main_menu_keyboard()
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
                            reply_markup=get_main_menu_keyboard()
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
            reply_markup=get_main_menu_keyboard(),
            parse_mode="Markdown"
        )
    
    async def start_registration(message: Message, state: FSMContext):
        """Начать процесс регистрации"""
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
            reply_markup=get_main_menu_keyboard(),
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
                reply_markup=get_main_menu_keyboard()
            )
            return
        
        # Проверяем, завершена ли регистрация
        if not await is_user_registered(message.from_user.id):
            await start_registration(message, state)
            return
        
        await message.answer(
            f"{EMOJI['info']} Используйте кнопки меню для навигации.",
            reply_markup=get_main_menu_keyboard()
        )
    
    # Регистрируем fallback роутер ПОСЛЕДНИМ
    dp.include_router(fallback_router)
    
    # Запускаем бота
    logger.info("Бот запускается...")
    
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())