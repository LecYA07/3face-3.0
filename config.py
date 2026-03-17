import os
from dotenv import load_dotenv

load_dotenv()

# Bot Token
BOT_TOKEN = os.getenv("BOT_TOKEN")

# OpenAI Settings (для автопроверки результатов матчей)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.onlysq.ru/ai/openai")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
AI_VERIFICATION_ENABLED = os.getenv("AI_VERIFICATION_ENABLED", "true").lower() == "true"
AI_AUTO_APPROVE_CONFIDENCE = float(os.getenv("AI_AUTO_APPROVE_CONFIDENCE", "0.95"))  # Порог автоподтверждения

# WebApp Settings
WEBAPP_HOST = os.getenv("WEBAPP_HOST", "0.0.0.0")
WEBAPP_PORT = int(os.getenv("WEBAPP_PORT", "443"))
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://3face.xyz")
SSL_CERT_PATH = os.getenv("SSL_CERT_PATH", "3face.xyz/certificate.crt")
SSL_KEY_PATH = os.getenv("SSL_KEY_PATH", "3face.xyz/newkey.key")

# Admin and Moderator IDs (загружаются из .env, но могут управляться через команды)
ADMIN_IDS = [int(id.strip()) for id in os.getenv("ADMIN_IDS", "").split(",") if id.strip()]
MODERATOR_IDS = [int(id.strip()) for id in os.getenv("MODERATOR_IDS", "").split(",") if id.strip()]

# Database
DATABASE_PATH = "database.db"

# Game Settings
LOBBY_SIZE = 5   # Размер лобби (одна команда) для 5x5
TEAM_SIZE = 5    # Размер команды для 5x5
MAX_PARTY_SIZE = 5  # Максимальный размер пати

# Game Formats (режимы игры)
# lobby_size - максимальное количество игроков в одном лобби (одна команда!)
#              Для 5x5 = 5 человек, для 2x2 = 2 человека
# team_size - размер команды в матче (равен lobby_size)
# match_size - общее количество игроков для матча (две команды)
GAME_FORMATS = {
    "5x5": {"lobby_size": 5, "team_size": 5, "match_size": 10, "name": "5x5", "emoji": "⚔️"},
    "2x2": {"lobby_size": 2, "team_size": 2, "match_size": 4, "name": "2x2", "emoji": "🎯"}
}
DEFAULT_GAME_FORMAT = "5x5"
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