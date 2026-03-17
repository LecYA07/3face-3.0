from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton, 
    ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from config import EMOJI, MAPS, PLATFORMS, WEBAPP_URL, GAME_FORMATS


def get_main_menu_keyboard(is_admin: bool = False) -> ReplyKeyboardMarkup:
    """Главное меню"""
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text=f"{EMOJI['search']} Найти игру"),
        KeyboardButton(text=f"{EMOJI['users']} Лобби")
    )
    builder.row(
        KeyboardButton(text=f"{EMOJI['user']} Профиль"),
        KeyboardButton(text=f"{EMOJI['trophy']} Топ игроков")
    )
    builder.row(
        KeyboardButton(text=f"{EMOJI['info']} Правила"),
        KeyboardButton(text="📩 Тикет")
    )
    if is_admin:
        builder.row(
            KeyboardButton(text="📱 Приложение", web_app=WebAppInfo(url=WEBAPP_URL))
        )
    return builder.as_markup(resize_keyboard=True)


def get_platform_keyboard() -> InlineKeyboardMarkup:
    """Выбор платформы"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=f"{PLATFORMS['pc']}", callback_data="platform:pc"),
        InlineKeyboardButton(text=f"{PLATFORMS['mobile']}", callback_data="platform:mobile")
    )
    return builder.as_markup()


def get_queue_keyboard(game_format: str = "5x5") -> InlineKeyboardMarkup:
    """Клавиатура очереди поиска"""
    builder = InlineKeyboardBuilder()
    format_data = GAME_FORMATS.get(game_format, GAME_FORMATS['5x5'])
    builder.row(
        InlineKeyboardButton(
            text=f"{EMOJI['cross']} Отменить поиск ({format_data['name']})",
            callback_data="queue:leave"
        )
    )
    return builder.as_markup()


def get_game_format_keyboard(action: str = "queue") -> InlineKeyboardMarkup:
    """Клавиатура выбора формата игры (5x5 или 2x2)"""
    builder = InlineKeyboardBuilder()
    
    for format_key, format_data in GAME_FORMATS.items():
        builder.row(
            InlineKeyboardButton(
                text=f"{format_data['emoji']} {format_data['name']}",
                callback_data=f"{action}:format:{format_key}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(
            text="◀️ Назад",
            callback_data="play:back"
        )
    )
    
    return builder.as_markup()


def get_play_menu_keyboard() -> InlineKeyboardMarkup:
    """Меню игры"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=f"{EMOJI['search']} Найти игру", 
            callback_data="queue:select_format"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=f"{EMOJI['users']} Создать лобби (приватное)", 
            callback_data="lobby:select_format"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=f"{EMOJI['link']} Публичные лобби", 
            callback_data="play:join_lobby"
        )
    )
    return builder.as_markup()


def get_lobby_keyboard(lobby_id: int, is_creator: bool = False, is_full: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура лобби"""
    builder = InlineKeyboardBuilder()
    
    if is_creator and is_full:
        builder.row(
            InlineKeyboardButton(
                text=f"{EMOJI['map']} Выбрать карту", 
                callback_data=f"lobby:select_map:{lobby_id}"
            )
        )
    
    if is_creator:
        builder.row(
            InlineKeyboardButton(
                text=f"{EMOJI['cross']} Расформировать лобби", 
                callback_data=f"lobby:disband:{lobby_id}"
            )
        )
    else:
        builder.row(
            InlineKeyboardButton(
                text=f"{EMOJI['cross']} Покинуть лобби", 
                callback_data=f"lobby:leave:{lobby_id}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(
            text=f"{EMOJI['link']} Пригласить друзей", 
            callback_data=f"lobby:invite:{lobby_id}"
        )
    )
    
    return builder.as_markup()


def get_lobbies_list_keyboard(lobbies: list, platform: str) -> InlineKeyboardMarkup:
    """Список доступных лобби"""
    builder = InlineKeyboardBuilder()
    
    for lobby in lobbies[:10]:  # Максимум 10 лобби
        game_format = lobby.get('game_format', '5x5')
        format_data = GAME_FORMATS.get(game_format, GAME_FORMATS['5x5'])
        lobby_size = format_data['lobby_size']
        builder.row(
            InlineKeyboardButton(
                text=f"{format_data['emoji']} Лобби #{lobby['lobby_id']} [{format_data['name']}] ({lobby.get('player_count', 0)}/{lobby_size})",
                callback_data=f"lobby:join:{lobby['lobby_id']}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(
            text=f"{EMOJI['gear']} Создать своё лобби",
            callback_data=f"lobby:select_format"
        )
    )
    
    return builder.as_markup()


def get_maps_keyboard(lobby_id: int) -> InlineKeyboardMarkup:
    """Выбор карты"""
    builder = InlineKeyboardBuilder()
    
    for map_name in MAPS:
        builder.row(
            InlineKeyboardButton(
                text=map_name,
                callback_data=f"map:select:{lobby_id}:{map_name}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(
            text=f"{EMOJI['target']} Случайная карта",
            callback_data=f"map:random:{lobby_id}"
        )
    )
    
    return builder.as_markup()


def get_match_keyboard(match_id: int) -> InlineKeyboardMarkup:
    """Клавиатура активного матча"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text=f"{EMOJI['camera']} Отправить скриншот результата",
            callback_data=f"match:submit:{match_id}"
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text=f"{EMOJI['info']} Информация о матче",
            callback_data=f"match:info:{match_id}"
        )
    )
    
    return builder.as_markup()


def get_party_keyboard(party_id: int, is_leader: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура пати"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text=f"{EMOJI['link']} Пригласить друга",
            callback_data=f"party:invite:{party_id}"
        )
    )
    
    if is_leader:
        builder.row(
            InlineKeyboardButton(
                text=f"{EMOJI['cross']} Распустить пати",
                callback_data=f"party:disband:{party_id}"
            )
        )
    else:
        builder.row(
            InlineKeyboardButton(
                text=f"{EMOJI['cross']} Покинуть пати",
                callback_data=f"party:leave:{party_id}"
            )
        )
    
    return builder.as_markup()


def get_party_invite_keyboard(party_id: int) -> InlineKeyboardMarkup:
    """Клавиатура приглашения в пати"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text=f"{EMOJI['check']} Принять",
            callback_data=f"party:accept:{party_id}"
        ),
        InlineKeyboardButton(
            text=f"{EMOJI['cross']} Отклонить",
            callback_data=f"party:decline:{party_id}"
        )
    )
    
    return builder.as_markup()


def get_top_players_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура топа игроков"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text=f"{EMOJI['trophy']} Общий топ", callback_data="top:all"),
    )
    builder.row(
        InlineKeyboardButton(text=f"{PLATFORMS['pc']} Топ", callback_data="top:pc"),
        InlineKeyboardButton(text=f"{PLATFORMS['mobile']} Топ", callback_data="top:mobile")
    )
    
    return builder.as_markup()


def get_profile_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Клавиатура профиля"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text=f"{EMOJI['chart']} История матчей",
            callback_data=f"profile:history:{user_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=f"{EMOJI['gear']} Сменить платформу",
            callback_data=f"profile:platform:{user_id}"
        )
    )
    
    return builder.as_markup()


# ============ ADMIN KEYBOARDS ============

def get_admin_menu_keyboard() -> InlineKeyboardMarkup:
    """Админ меню"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text=f"{EMOJI['camera']} Проверить результаты",
            callback_data="admin:submissions"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=f"{EMOJI['chart']} Статистика",
            callback_data="admin:stats"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=f"{EMOJI['lock']} Управление банами",
            callback_data="admin:bans"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=f"{EMOJI['crown']} Управление ролями",
            callback_data="admin:roles"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="💾 Бэкап базы данных",
            callback_data="admin:backup"
        )
    )
    
    return builder.as_markup()


def get_submission_review_keyboard(submission_id: int, match_id: int) -> InlineKeyboardMarkup:
    """Клавиатура проверки результата матча"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text=f"{EMOJI['check']} Подтвердить и заполнить",
            callback_data=f"submission:approve:{submission_id}:{match_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=f"{EMOJI['cross']} Отклонить",
            callback_data=f"submission:reject:{submission_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=f"{EMOJI['info']} Детали матча",
            callback_data=f"submission:details:{match_id}"
        )
    )
    
    return builder.as_markup()


def get_team_winner_keyboard(match_id: int) -> InlineKeyboardMarkup:
    """Выбор команды-победителя"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text=f"{EMOJI['red']} Команда 1 победила",
            callback_data=f"result:winner:{match_id}:1"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=f"{EMOJI['blue']} Команда 2 победила",
            callback_data=f"result:winner:{match_id}:2"
        )
    )
    
    return builder.as_markup()


def get_mvp_selection_keyboard(match_id: int, players: list) -> InlineKeyboardMarkup:
    """Выбор MVP матча"""
    builder = InlineKeyboardBuilder()
    
    for player in players:
        name = player.get('username') or player.get('full_name', 'Игрок')
        builder.row(
            InlineKeyboardButton(
                text=f"{EMOJI['star']} {name}",
                callback_data=f"result:mvp:{match_id}:{player['user_id']}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(
            text=f"{EMOJI['cross']} Без MVP",
            callback_data=f"result:mvp:{match_id}:0"
        )
    )
    
    return builder.as_markup()


def get_confirm_keyboard(action: str, data: str) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text=f"{EMOJI['check']} Да",
            callback_data=f"confirm:{action}:{data}:yes"
        ),
        InlineKeyboardButton(
            text=f"{EMOJI['cross']} Нет",
            callback_data=f"confirm:{action}:{data}:no"
        )
    )
    
    return builder.as_markup()


def get_back_keyboard(callback_data: str) -> InlineKeyboardMarkup:
    """Кнопка назад"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text=f"◀️ Назад",
            callback_data=callback_data
        )
    )
    
    return builder.as_markup()


# ============ READY CHECK KEYBOARDS ============

def get_ready_check_keyboard(match_id: int) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения готовности"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text=f"{EMOJI['check']} Готов",
            callback_data=f"ready:accept:{match_id}"
        ),
        InlineKeyboardButton(
            text=f"{EMOJI['cross']} Не готов",
            callback_data=f"ready:decline:{match_id}"
        )
    )
    
    return builder.as_markup()


def get_ready_check_accepted_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура после принятия готовности (кнопка неактивна)"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text=f"{EMOJI['check']} Вы готовы! Ожидание остальных...",
            callback_data="ready:already_accepted"
        )
    )
    
    return builder.as_markup()


def get_ready_check_declined_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура после отказа"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text=f"{EMOJI['cross']} Вы отказались от матча",
            callback_data="ready:already_declined"
        )
    )
    
    return builder.as_markup()


def get_ready_check_timeout_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура после таймаута"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text=f"{EMOJI['clock']} Время вышло",
            callback_data="ready:timeout"
        )
    )
    
    return builder.as_markup()


# ============ TICKET KEYBOARDS ============

def get_ticket_cancel_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура отмены создания тикета"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text=f"{EMOJI['cross']} Отменить",
            callback_data="ticket:cancel"
        )
    )
    
    return builder.as_markup()


def get_ticket_type_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора типа тикета"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text="❓ Вопрос",
            callback_data="ticket:type:question"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🚨 Жалоба на игрока",
            callback_data="ticket:type:report"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🐛 Баг/Ошибка",
            callback_data="ticket:type:bug"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="💡 Предложение",
            callback_data="ticket:type:suggestion"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=f"{EMOJI['cross']} Отмена",
            callback_data="ticket:cancel"
        )
    )
    
    return builder.as_markup()


def get_ticket_admin_keyboard(ticket_id: int, has_photo: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура для ответа на тикет (для админов)"""
    builder = InlineKeyboardBuilder()
    
    if has_photo:
        builder.row(
            InlineKeyboardButton(
                text="📷 Посмотреть фото",
                callback_data=f"ticket:photo:{ticket_id}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(
            text="💬 Ответить",
            callback_data=f"ticket:reply:{ticket_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=f"{EMOJI['check']} Закрыть тикет",
            callback_data=f"ticket:close:{ticket_id}"
        )
    )
    
    return builder.as_markup()
