import os
from dotenv import load_dotenv

load_dotenv()

# Bot Token
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Admin and Moderator IDs (загружаются из .env, но могут управляться через команды)
ADMIN_IDS = [int(id.strip()) for id in os.getenv("ADMIN_IDS", "").split(",") if id.strip()]
MODERATOR_IDS = [int(id.strip()) for id in os.getenv("MODERATOR_IDS", "").split(",") if id.strip()]

# Database
DATABASE_PATH = "database.db"

# Game Settings
LOBBY_SIZE = 10  # Размер лобби для матча (10 игроков для 5x5)
TEAM_SIZE = 5    # Размер команды
MAX_PARTY_SIZE = 5  # Максимальный размер пати
DEFAULT_RATING = 1000  # Начальный рейтинг
MIN_RATING = 0  # Минимальный рейтинг

# Matchmaking Settings
MAX_RATING_DIFF = 300  # Максимальная разница рейтинга для быстрого подбора
RATING_DIFF_EXPAND_TIME = 20  # Через сколько секунд расширять диапазон
RATING_DIFF_EXPAND_STEP = 300  # На сколько расширять диапазон

# Ready Check Settings
READY_CHECK_TIMEOUT = 60  # Секунд на подтверждение готовности

# Maps
MAPS = [
    "🏜️ Sandstone",
    "🏢 Hanami", 
    "🌊 Breeze",
    "🏭 Zone7",
    "🏔️ Rust",
    "🌴 Dune"
]

# Sides
SIDES = ["🔴 Атака (T)", "🔵 Защита (CT)"]

# Platform types
PLATFORMS = {
    "pc": "🖥️ ПК",
    "mobile": "📱 Телефон"
}

# Emojis
EMOJI = {
    "trophy": "🏆",
    "star": "⭐",
    "fire": "🔥",
    "crown": "👑",
    "sword": "⚔️",
    "shield": "🛡️",
    "target": "🎯",
    "chart": "📊",
    "user": "👤",
    "users": "👥",
    "check": "✅",
    "cross": "❌",
    "warning": "⚠️",
    "info": "ℹ️",
    "gear": "⚙️",
    "game": "🎮",
    "map": "🗺️",
    "clock": "🕐",
    "camera": "📷",
    "medal": "🏅",
    "up": "📈",
    "down": "📉",
    "party": "🎉",
    "link": "🔗",
    "lock": "🔒",
    "unlock": "🔓",
    "red": "🔴",
    "blue": "🔵",
    "green": "🟢",
    "yellow": "🟡",
    "search": "🔍",
    "queue": "⏳"
}

# Rating changes - базовые значения (будут модифицироваться в зависимости от разницы рейтингов)
BASE_RATING_WIN = 25
BASE_RATING_LOSE = 20
RATING_MVP_BONUS = 10

# Множители для разницы рейтингов
# Если победили более сильную команду - больше очков
# Если проиграли более слабой - больше потеря
RATING_DIFF_MULTIPLIER = 0.04  # Каждые 25 очков разницы = ±1 к изменению рейтинга