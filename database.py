import aiosqlite
from config import DATABASE_PATH, DEFAULT_RATING, MIN_RATING
from typing import Optional, List, Dict, Any
from datetime import datetime


async def init_db():
    """Инициализация базы данных"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Таблица системных настроек
        await db.execute("""
            CREATE TABLE IF NOT EXISTS system_settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Таблица пользователей
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                game_nickname TEXT,
                game_id TEXT,
                rating INTEGER DEFAULT 1000,
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                kills INTEGER DEFAULT 0,
                deaths INTEGER DEFAULT 0,
                assists INTEGER DEFAULT 0,
                mvp_count INTEGER DEFAULT 0,
                win_streak INTEGER DEFAULT 0,
                platform TEXT DEFAULT 'pc',
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_banned INTEGER DEFAULT 0,
                is_admin INTEGER DEFAULT 0,
                is_moderator INTEGER DEFAULT 0,
                is_registered INTEGER DEFAULT 0
            )
        """)
        
        # Таблица очереди поиска матча
        await db.execute("""
            CREATE TABLE IF NOT EXISTS matchmaking_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE,
                party_id INTEGER DEFAULT NULL,
                lobby_id INTEGER DEFAULT NULL,
                platform TEXT DEFAULT 'pc',
                rating INTEGER,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                FOREIGN KEY (lobby_id) REFERENCES lobbies(lobby_id)
            )
        """)
        
        # Таблица лобби
        await db.execute("""
            CREATE TABLE IF NOT EXISTS lobbies (
                lobby_id INTEGER PRIMARY KEY AUTOINCREMENT,
                creator_id INTEGER,
                platform TEXT DEFAULT 'pc',
                game_format TEXT DEFAULT '5x5',
                status TEXT DEFAULT 'waiting',
                is_private INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (creator_id) REFERENCES users(user_id)
            )
        """)
        
        # Таблица участников лобби
        await db.execute("""
            CREATE TABLE IF NOT EXISTS lobby_players (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lobby_id INTEGER,
                user_id INTEGER,
                party_id INTEGER DEFAULT NULL,
                lobby_message_id INTEGER DEFAULT NULL,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (lobby_id) REFERENCES lobbies(lobby_id),
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # Таблица пати (групп друзей)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS parties (
                party_id INTEGER PRIMARY KEY AUTOINCREMENT,
                leader_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (leader_id) REFERENCES users(user_id)
            )
        """)
        
        # Таблица участников пати
        await db.execute("""
            CREATE TABLE IF NOT EXISTS party_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                party_id INTEGER,
                user_id INTEGER,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (party_id) REFERENCES parties(party_id),
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # Таблица матчей
        await db.execute("""
            CREATE TABLE IF NOT EXISTS matches (
                match_id INTEGER PRIMARY KEY AUTOINCREMENT,
                lobby_id INTEGER,
                platform TEXT,
                game_format TEXT DEFAULT '5x5',
                map_name TEXT,
                status TEXT DEFAULT 'pending',
                team1_score INTEGER DEFAULT 0,
                team2_score INTEGER DEFAULT 0,
                team1_avg_rating INTEGER DEFAULT 0,
                team2_avg_rating INTEGER DEFAULT 0,
                team1_start_side TEXT,
                team2_start_side TEXT,
                winner_team INTEGER DEFAULT NULL,
                screenshot_file_id TEXT DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                finished_at TIMESTAMP DEFAULT NULL,
                verified_by INTEGER DEFAULT NULL,
                FOREIGN KEY (lobby_id) REFERENCES lobbies(lobby_id),
                FOREIGN KEY (verified_by) REFERENCES users(user_id)
            )
        """)
        
        # Таблица игроков матча
        await db.execute("""
            CREATE TABLE IF NOT EXISTS match_players (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_id INTEGER,
                user_id INTEGER,
                team INTEGER,
                kills INTEGER DEFAULT 0,
                deaths INTEGER DEFAULT 0,
                assists INTEGER DEFAULT 0,
                is_mvp INTEGER DEFAULT 0,
                rating_change INTEGER DEFAULT 0,
                rating_before INTEGER DEFAULT 0,
                FOREIGN KEY (match_id) REFERENCES matches(match_id),
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # Таблица заявок на проверку результатов
        await db.execute("""
            CREATE TABLE IF NOT EXISTS match_submissions (
                submission_id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_id INTEGER,
                submitted_by INTEGER,
                screenshot_file_id TEXT,
                status TEXT DEFAULT 'pending',
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reviewed_by INTEGER DEFAULT NULL,
                reviewed_at TIMESTAMP DEFAULT NULL,
                FOREIGN KEY (match_id) REFERENCES matches(match_id),
                FOREIGN KEY (submitted_by) REFERENCES users(user_id),
                FOREIGN KEY (reviewed_by) REFERENCES users(user_id)
            )
        """)
        
        # Таблица проверки готовности к матчу
        await db.execute("""
            CREATE TABLE IF NOT EXISTS match_ready_checks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_id INTEGER,
                user_id INTEGER,
                is_ready INTEGER DEFAULT 0,
                message_id INTEGER DEFAULT NULL,
                responded_at TIMESTAMP DEFAULT NULL,
                FOREIGN KEY (match_id) REFERENCES matches(match_id),
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                UNIQUE(match_id, user_id)
            )
        """)
        
        # Таблица тикетов
        await db.execute("""
            CREATE TABLE IF NOT EXISTS tickets (
                ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                ticket_type TEXT,
                message TEXT,
                photo_file_id TEXT DEFAULT NULL,
                status TEXT DEFAULT 'open',
                admin_response TEXT DEFAULT NULL,
                responded_by INTEGER DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                closed_at TIMESTAMP DEFAULT NULL,
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                FOREIGN KEY (responded_by) REFERENCES users(user_id)
            )
        """)
        
        # Таблица сообщений в тикетах
        await db.execute("""
            CREATE TABLE IF NOT EXISTS ticket_messages (
                message_id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id INTEGER,
                user_id INTEGER,
                message TEXT,
                is_admin INTEGER DEFAULT 0,
                photo_file_id TEXT DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (ticket_id) REFERENCES tickets(ticket_id),
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # Таблица AI проверок результатов матчей
        await db.execute("""
            CREATE TABLE IF NOT EXISTS ai_verifications (
                verification_id INTEGER PRIMARY KEY AUTOINCREMENT,
                submission_id INTEGER,
                match_id INTEGER,
                ai_result TEXT,
                confidence REAL DEFAULT 0,
                team1_score INTEGER DEFAULT NULL,
                team2_score INTEGER DEFAULT NULL,
                winner_team INTEGER DEFAULT NULL,
                mvp_user_id INTEGER DEFAULT NULL,
                status TEXT DEFAULT 'pending',
                admin_id INTEGER DEFAULT NULL,
                admin_action TEXT DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reviewed_at TIMESTAMP DEFAULT NULL,
                FOREIGN KEY (submission_id) REFERENCES match_submissions(submission_id),
                FOREIGN KEY (match_id) REFERENCES matches(match_id),
                FOREIGN KEY (admin_id) REFERENCES users(user_id),
                FOREIGN KEY (mvp_user_id) REFERENCES users(user_id)
            )
        """)
        
        # Миграция: добавляем столбец photo_file_id если его нет
        try:
            await db.execute("ALTER TABLE tickets ADD COLUMN photo_file_id TEXT DEFAULT NULL")
        except Exception:
            pass  # Столбец уже существует
        
        # Миграция: добавляем столбец game_format в lobbies если его нет
        try:
            await db.execute("ALTER TABLE lobbies ADD COLUMN game_format TEXT DEFAULT '5x5'")
        except Exception:
            pass  # Столбец уже существует
        
        # Миграция: добавляем столбец game_format в matches если его нет
        try:
            await db.execute("ALTER TABLE matches ADD COLUMN game_format TEXT DEFAULT '5x5'")
        except Exception:
            pass  # Столбец уже существует
        
        # Миграция: добавляем столбец game_format в matchmaking_queue если его нет
        try:
            await db.execute("ALTER TABLE matchmaking_queue ADD COLUMN game_format TEXT DEFAULT '5x5'")
        except Exception:
            pass  # Столбец уже существует
        
        # Миграция: добавляем столбец win_streak в users если его нет
        try:
            await db.execute("ALTER TABLE users ADD COLUMN win_streak INTEGER DEFAULT 0")
        except Exception:
            pass  # Столбец уже существует
        
        # Миграция: добавляем столбец lobby_id в matchmaking_queue если его нет
        try:
            await db.execute("ALTER TABLE matchmaking_queue ADD COLUMN lobby_id INTEGER DEFAULT NULL")
        except Exception:
            pass  # Столбец уже существует
        
        # Миграция: добавляем столбец lobby_message_id в lobby_players если его нет
        try:
            await db.execute("ALTER TABLE lobby_players ADD COLUMN lobby_message_id INTEGER DEFAULT NULL")
        except Exception:
            pass  # Столбец уже существует
        
        # Таблица логирования попыток регистрации при закрытой регистрации
        await db.execute("""
            CREATE TABLE IF NOT EXISTS blocked_registration_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                full_name TEXT,
                ban_applied INTEGER DEFAULT 1,
                attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.commit()


# ============ USER FUNCTIONS ============

async def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    """Получить пользователя по ID"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def create_user(user_id: int, username: str, full_name: str) -> None:
    """Создать нового пользователя"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            INSERT OR IGNORE INTO users (user_id, username, full_name, rating)
            VALUES (?, ?, ?, ?)
        """, (user_id, username, full_name, DEFAULT_RATING))
        await db.commit()


async def update_user_game_info(user_id: int, game_nickname: str, game_id: str) -> None:
    """Обновить игровой ник и ID пользователя"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            UPDATE users SET game_nickname = ?, game_id = ?, is_registered = 1 
            WHERE user_id = ?
        """, (game_nickname, game_id, user_id))
        await db.commit()


async def update_user_game_nickname(user_id: int, game_nickname: str) -> None:
    """Обновить только игровой ник пользователя"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            UPDATE users SET game_nickname = ? WHERE user_id = ?
        """, (game_nickname, user_id))
        await db.commit()


async def update_user_game_id(user_id: int, game_id: str) -> None:
    """Обновить только игровой ID пользователя"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            UPDATE users SET game_id = ? WHERE user_id = ?
        """, (game_id, user_id))
        await db.commit()


async def is_user_registered(user_id: int) -> bool:
    """Проверить, завершил ли пользователь регистрацию"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            "SELECT is_registered FROM users WHERE user_id = ?", 
            (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return bool(row and row[0])


async def update_user_platform(user_id: int, platform: str) -> None:
    """Обновить платформу пользователя"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("UPDATE users SET platform = ? WHERE user_id = ?", (platform, user_id))
        await db.commit()


async def update_user_stats(user_id: int, wins: int = 0, losses: int = 0, 
                           kills: int = 0, deaths: int = 0, assists: int = 0,
                           rating_change: int = 0, is_mvp: bool = False) -> None:
    """Обновить статистику пользователя"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        mvp_add = 1 if is_mvp else 0
        await db.execute("""
            UPDATE users SET 
                wins = wins + ?,
                losses = losses + ?,
                kills = kills + ?,
                deaths = deaths + ?,
                assists = assists + ?,
                rating = MAX(?, rating + ?),
                mvp_count = mvp_count + ?
            WHERE user_id = ?
        """, (wins, losses, kills, deaths, assists, MIN_RATING, rating_change, mvp_add, user_id))
        await db.commit()


async def set_user_rating(user_id: int, new_rating: int) -> None:
    """Установить рейтинг пользователя напрямую"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "UPDATE users SET rating = MAX(?, ?) WHERE user_id = ?", 
            (MIN_RATING, new_rating, user_id)
        )
        await db.commit()


async def set_user_stat(user_id: int, stat_name: str, value: int) -> bool:
    """
    Установить любой числовой параметр статистики пользователя.
    
    Допустимые параметры: rating, wins, losses, kills, deaths, assists, mvp_count, win_streak
    
    Returns:
        True если успешно, False если параметр недопустим
    """
    allowed_stats = ['rating', 'wins', 'losses', 'kills', 'deaths', 'assists', 'mvp_count', 'win_streak']
    
    if stat_name not in allowed_stats:
        return False
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        if stat_name == 'rating':
            # Для рейтинга применяем минимальное значение
            await db.execute(
                f"UPDATE users SET {stat_name} = MAX(?, ?) WHERE user_id = ?", 
                (MIN_RATING, value, user_id)
            )
        else:
            # Для остальных параметров просто устанавливаем значение (не меньше 0)
            await db.execute(
                f"UPDATE users SET {stat_name} = MAX(0, ?) WHERE user_id = ?", 
                (value, user_id)
            )
        await db.commit()
        return True


async def reset_user_stats(user_id: int) -> None:
    """Сбросить всю статистику пользователя"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            UPDATE users SET 
                rating = ?,
                wins = 0,
                losses = 0,
                kills = 0,
                deaths = 0,
                assists = 0,
                mvp_count = 0,
                win_streak = 0
            WHERE user_id = ?
        """, (DEFAULT_RATING, user_id))
        await db.commit()


async def add_user_rating(user_id: int, amount: int) -> None:
    """Добавить/вычесть рейтинг пользователя"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "UPDATE users SET rating = MAX(?, rating + ?) WHERE user_id = ?", 
            (MIN_RATING, amount, user_id)
        )
        await db.commit()


async def get_top_players(limit: int = 10, platform: str = None) -> List[Dict[str, Any]]:
    """Получить топ игроков по рейтингу"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        if platform:
            query = """
                SELECT * FROM users 
                WHERE is_banned = 0 AND platform = ?
                ORDER BY rating DESC 
                LIMIT ?
            """
            async with db.execute(query, (platform, limit)) as cursor:
                rows = await cursor.fetchall()
        else:
            query = """
                SELECT * FROM users 
                WHERE is_banned = 0
                ORDER BY rating DESC 
                LIMIT ?
            """
            async with db.execute(query, (limit,)) as cursor:
                rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def ban_user(user_id: int) -> None:
    """Забанить пользователя"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("UPDATE users SET is_banned = 1 WHERE user_id = ?", (user_id,))
        await db.commit()


async def unban_user(user_id: int) -> None:
    """Разбанить пользователя"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("UPDATE users SET is_banned = 0 WHERE user_id = ?", (user_id,))
        await db.commit()


async def set_user_admin(user_id: int, is_admin: bool) -> None:
    """Установить/снять права администратора"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "UPDATE users SET is_admin = ? WHERE user_id = ?", 
            (1 if is_admin else 0, user_id)
        )
        await db.commit()


async def set_user_moderator(user_id: int, is_moderator: bool) -> None:
    """Установить/снять права модератора"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "UPDATE users SET is_moderator = ? WHERE user_id = ?", 
            (1 if is_moderator else 0, user_id)
        )
        await db.commit()


async def is_user_admin(user_id: int) -> bool:
    """Проверить, является ли пользователь админом"""
    user = await get_user(user_id)
    if user and user.get('is_admin'):
        return True
    from config import ADMIN_IDS
    return user_id in ADMIN_IDS


async def is_user_moderator(user_id: int) -> bool:
    """Проверить, является ли пользователь модератором"""
    user = await get_user(user_id)
    if user and (user.get('is_moderator') or user.get('is_admin')):
        return True
    from config import ADMIN_IDS, MODERATOR_IDS
    return user_id in ADMIN_IDS or user_id in MODERATOR_IDS


async def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    """Получить пользователя по username"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE username = ?", 
            (username.replace("@", ""),)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def search_users(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Поиск пользователей по нику, телеграм username, telegram ID или игровому ID.
    
    Args:
        query: Поисковый запрос
        limit: Максимальное количество результатов
    
    Returns:
        Список найденных пользователей
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        # Убираем @ если есть
        clean_query = query.replace("@", "").strip()
        
        # Проверяем, является ли запрос числом (telegram ID)
        is_numeric = clean_query.isdigit()
        
        if is_numeric:
            # Поиск по telegram ID
            sql_query = """
                SELECT * FROM users 
                WHERE user_id = ? OR CAST(user_id AS TEXT) LIKE ?
                LIMIT ?
            """
            async with db.execute(sql_query, (int(clean_query), f"%{clean_query}%", limit)) as cursor:
                rows = await cursor.fetchall()
        else:
            # Поиск по нику, username или игровому ID
            search_pattern = f"%{clean_query}%"
            sql_query = """
                SELECT * FROM users 
                WHERE username LIKE ? 
                   OR full_name LIKE ? 
                   OR game_nickname LIKE ? 
                   OR game_id LIKE ?
                ORDER BY 
                    CASE 
                        WHEN username = ? THEN 1
                        WHEN game_nickname = ? THEN 2
                        WHEN game_id = ? THEN 3
                        WHEN username LIKE ? THEN 4
                        WHEN game_nickname LIKE ? THEN 5
                        ELSE 6
                    END
                LIMIT ?
            """
            async with db.execute(sql_query, (
                search_pattern, search_pattern, search_pattern, search_pattern,
                clean_query, clean_query, clean_query,
                f"{clean_query}%", f"{clean_query}%",
                limit
            )) as cursor:
                rows = await cursor.fetchall()
        
        return [dict(row) for row in rows]


# ============ MATCHMAKING QUEUE FUNCTIONS ============

async def join_queue(user_id: int, platform: str, rating: int, party_id: int = None, game_format: str = "5x5", lobby_id: int = None) -> bool:
    """Добавить игрока в очередь поиска"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        try:
            await db.execute("""
                INSERT OR REPLACE INTO matchmaking_queue (user_id, platform, rating, party_id, game_format, lobby_id, joined_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (user_id, platform, rating, party_id, game_format, lobby_id, datetime.now()))
            await db.commit()
            return True
        except Exception:
            return False


async def leave_queue(user_id: int) -> None:
    """Удалить игрока из очереди поиска"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("DELETE FROM matchmaking_queue WHERE user_id = ?", (user_id,))
        await db.commit()


async def is_in_queue(user_id: int) -> bool:
    """Проверить, находится ли игрок в очереди"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            "SELECT id FROM matchmaking_queue WHERE user_id = ?", 
            (user_id,)
        ) as cursor:
            return await cursor.fetchone() is not None


async def get_queue_players(platform: str, game_format: str = "5x5", min_rating: int = None, max_rating: int = None) -> List[Dict[str, Any]]:
    """Получить игроков из очереди с фильтром по рейтингу и формату"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        if min_rating is not None and max_rating is not None:
            query = """
                SELECT mq.*, u.username, u.full_name
                FROM matchmaking_queue mq
                JOIN users u ON mq.user_id = u.user_id
                WHERE mq.platform = ? AND mq.game_format = ? AND mq.rating BETWEEN ? AND ?
                ORDER BY mq.joined_at
            """
            async with db.execute(query, (platform, game_format, min_rating, max_rating)) as cursor:
                rows = await cursor.fetchall()
        else:
            query = """
                SELECT mq.*, u.username, u.full_name
                FROM matchmaking_queue mq
                JOIN users u ON mq.user_id = u.user_id
                WHERE mq.platform = ? AND mq.game_format = ?
                ORDER BY mq.joined_at
            """
            async with db.execute(query, (platform, game_format)) as cursor:
                rows = await cursor.fetchall()
        
        return [dict(row) for row in rows]


async def get_queue_count(platform: str, game_format: str = "5x5") -> int:
    """Получить количество игроков в очереди"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM matchmaking_queue WHERE platform = ? AND game_format = ?", 
            (platform, game_format)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0


async def get_user_queue_format(user_id: int) -> Optional[str]:
    """Получить формат игры, в очереди которого находится игрок"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            "SELECT game_format FROM matchmaking_queue WHERE user_id = ?", 
            (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None


async def clear_queue_for_users(user_ids: List[int]) -> None:
    """Удалить указанных игроков из очереди"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        placeholders = ','.join('?' * len(user_ids))
        await db.execute(f"DELETE FROM matchmaking_queue WHERE user_id IN ({placeholders})", user_ids)
        await db.commit()


# ============ LOBBY FUNCTIONS ============

async def create_lobby(creator_id: int, platform: str, is_private: bool = False, game_format: str = "5x5") -> int:
    """Создать лобби"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO lobbies (creator_id, platform, game_format, status, is_private)
            VALUES (?, ?, ?, 'waiting', ?)
        """, (creator_id, platform, game_format, 1 if is_private else 0))
        lobby_id = cursor.lastrowid
        await db.commit()
        return lobby_id


async def get_lobby(lobby_id: int) -> Optional[Dict[str, Any]]:
    """Получить лобби по ID"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM lobbies WHERE lobby_id = ?", (lobby_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def get_active_lobbies(platform: str = None) -> List[Dict[str, Any]]:
    """Получить активные лобби"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        if platform:
            query = """
                SELECT * FROM lobbies 
                WHERE status = 'waiting' AND platform = ? AND is_private = 0
                ORDER BY created_at DESC
            """
            async with db.execute(query, (platform,)) as cursor:
                rows = await cursor.fetchall()
        else:
            query = """
                SELECT * FROM lobbies 
                WHERE status = 'waiting' AND is_private = 0
                ORDER BY created_at DESC
            """
            async with db.execute(query) as cursor:
                rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def join_lobby(lobby_id: int, user_id: int, party_id: int = None) -> bool:
    """Присоединиться к лобби"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Проверяем, не в лобби ли уже игрок
        async with db.execute(
            "SELECT id FROM lobby_players WHERE lobby_id = ? AND user_id = ?", 
            (lobby_id, user_id)
        ) as cursor:
            if await cursor.fetchone():
                return False
        
        await db.execute("""
            INSERT INTO lobby_players (lobby_id, user_id, party_id)
            VALUES (?, ?, ?)
        """, (lobby_id, user_id, party_id))
        await db.commit()
        return True


async def leave_lobby(lobby_id: int, user_id: int) -> None:
    """Покинуть лобби"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "DELETE FROM lobby_players WHERE lobby_id = ? AND user_id = ?",
            (lobby_id, user_id)
        )
        await db.commit()


async def get_lobby_players(lobby_id: int) -> List[Dict[str, Any]]:
    """Получить игроков в лобби"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = """
            SELECT lp.*, u.username, u.full_name, u.rating, u.platform,
                   u.game_nickname, u.game_id, u.wins, u.losses
            FROM lobby_players lp
            JOIN users u ON lp.user_id = u.user_id
            WHERE lp.lobby_id = ?
            ORDER BY lp.joined_at
        """
        async with db.execute(query, (lobby_id,)) as cursor:
            rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_lobby_player_count(lobby_id: int) -> int:
    """Получить количество игроков в лобби"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM lobby_players WHERE lobby_id = ?", 
            (lobby_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0


async def update_lobby_status(lobby_id: int, status: str) -> None:
    """Обновить статус лобби"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("UPDATE lobbies SET status = ? WHERE lobby_id = ?", (status, lobby_id))
        await db.commit()


async def delete_lobby(lobby_id: int) -> None:
    """Удалить лобби"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("DELETE FROM lobby_players WHERE lobby_id = ?", (lobby_id,))
        await db.execute("DELETE FROM lobbies WHERE lobby_id = ?", (lobby_id,))
        await db.commit()


async def get_user_active_lobby(user_id: int) -> Optional[int]:
    """Получить активное лобби пользователя (включая статусы waiting, searching)"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        query = """
            SELECT lp.lobby_id FROM lobby_players lp
            JOIN lobbies l ON lp.lobby_id = l.lobby_id
            WHERE lp.user_id = ? AND l.status IN ('waiting', 'searching')
        """
        async with db.execute(query, (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None


async def get_user_lobby_any_status(user_id: int) -> Optional[int]:
    """Получить лобби пользователя в любом активном статусе (включая in_match, ready_check)"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        query = """
            SELECT lp.lobby_id FROM lobby_players lp
            JOIN lobbies l ON lp.lobby_id = l.lobby_id
            WHERE lp.user_id = ? AND l.status NOT IN ('finished', 'cancelled')
        """
        async with db.execute(query, (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None


async def get_user_queue_lobby(user_id: int) -> Optional[int]:
    """Получить lobby_id из очереди поиска для пользователя"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            "SELECT lobby_id FROM matchmaking_queue WHERE user_id = ?", 
            (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None


async def restore_lobby_after_match(lobby_id: int) -> None:
    """Восстановить статус лобби после матча для продолжения игры"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "UPDATE lobbies SET status = 'waiting' WHERE lobby_id = ? AND status IN ('in_match', 'ready_check')", 
            (lobby_id,)
        )
        await db.commit()


async def update_lobby_player_message(lobby_id: int, user_id: int, message_id: int) -> None:
    """Обновить ID сообщения лобби для игрока"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "UPDATE lobby_players SET lobby_message_id = ? WHERE lobby_id = ? AND user_id = ?",
            (message_id, lobby_id, user_id)
        )
        await db.commit()


async def get_lobby_player_message(lobby_id: int, user_id: int) -> Optional[int]:
    """Получить ID сообщения лобби для игрока"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            "SELECT lobby_message_id FROM lobby_players WHERE lobby_id = ? AND user_id = ?",
            (lobby_id, user_id)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row and row[0] else None


async def get_lobby_players_with_messages(lobby_id: int) -> List[Dict[str, Any]]:
    """Получить игроков в лобби с их message_id"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = """
            SELECT lp.*, u.username, u.full_name, u.rating, u.platform,
                   u.game_nickname, u.game_id, u.wins, u.losses
            FROM lobby_players lp
            JOIN users u ON lp.user_id = u.user_id
            WHERE lp.lobby_id = ?
            ORDER BY lp.joined_at
        """
        async with db.execute(query, (lobby_id,)) as cursor:
            rows = await cursor.fetchall()
        return [dict(row) for row in rows]


# ============ PARTY FUNCTIONS ============

async def create_party(leader_id: int) -> int:
    """Создать пати"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO parties (leader_id)
            VALUES (?)
        """, (leader_id,))
        party_id = cursor.lastrowid
        
        # Добавляем лидера в пати
        await db.execute("""
            INSERT INTO party_members (party_id, user_id)
            VALUES (?, ?)
        """, (party_id, leader_id))
        
        await db.commit()
        return party_id


async def get_party(party_id: int) -> Optional[Dict[str, Any]]:
    """Получить пати по ID"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM parties WHERE party_id = ?", (party_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def join_party(party_id: int, user_id: int) -> bool:
    """Присоединиться к пати"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Проверяем, не в пати ли уже игрок
        async with db.execute(
            "SELECT id FROM party_members WHERE party_id = ? AND user_id = ?", 
            (party_id, user_id)
        ) as cursor:
            if await cursor.fetchone():
                return False
        
        # Проверяем размер пати
        async with db.execute(
            "SELECT COUNT(*) FROM party_members WHERE party_id = ?", 
            (party_id,)
        ) as cursor:
            count = (await cursor.fetchone())[0]
            from config import MAX_PARTY_SIZE
            if count >= MAX_PARTY_SIZE:
                return False
        
        await db.execute("""
            INSERT INTO party_members (party_id, user_id)
            VALUES (?, ?)
        """, (party_id, user_id))
        await db.commit()
        return True


async def leave_party(party_id: int, user_id: int) -> None:
    """Покинуть пати"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "DELETE FROM party_members WHERE party_id = ? AND user_id = ?",
            (party_id, user_id)
        )
        await db.commit()


async def get_party_members(party_id: int) -> List[Dict[str, Any]]:
    """Получить участников пати"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = """
            SELECT pm.*, u.username, u.full_name, u.rating,
                   u.game_nickname, u.game_id, u.wins, u.losses
            FROM party_members pm
            JOIN users u ON pm.user_id = u.user_id
            WHERE pm.party_id = ?
        """
        async with db.execute(query, (party_id,)) as cursor:
            rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_user_party(user_id: int) -> Optional[int]:
    """Получить пати пользователя"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            "SELECT party_id FROM party_members WHERE user_id = ?", 
            (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None


async def delete_party(party_id: int) -> None:
    """Удалить пати"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("DELETE FROM party_members WHERE party_id = ?", (party_id,))
        await db.execute("DELETE FROM parties WHERE party_id = ?", (party_id,))
        await db.commit()


# ============ MATCH FUNCTIONS ============

async def create_match(lobby_id: int, platform: str, map_name: str, 
                       team1_start_side: str, team2_start_side: str,
                       team1_avg_rating: int = 0, team2_avg_rating: int = 0,
                       game_format: str = "5x5") -> int:
    """Создать матч"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO matches (lobby_id, platform, map_name, team1_start_side, team2_start_side, 
                                team1_avg_rating, team2_avg_rating, game_format, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active')
        """, (lobby_id, platform, map_name, team1_start_side, team2_start_side, 
              team1_avg_rating, team2_avg_rating, game_format))
        match_id = cursor.lastrowid
        await db.commit()
        return match_id


async def create_match_pending(lobby_id: int, platform: str, map_name: str, 
                               team1_start_side: str, team2_start_side: str,
                               team1_avg_rating: int = 0, team2_avg_rating: int = 0,
                               game_format: str = "5x5") -> int:
    """Создать матч в статусе ожидания ready check"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO matches (lobby_id, platform, map_name, team1_start_side, team2_start_side, 
                                team1_avg_rating, team2_avg_rating, game_format, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending')
        """, (lobby_id, platform, map_name, team1_start_side, team2_start_side, 
              team1_avg_rating, team2_avg_rating, game_format))
        match_id = cursor.lastrowid
        await db.commit()
        return match_id


async def get_match(match_id: int) -> Optional[Dict[str, Any]]:
    """Получить матч по ID"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM matches WHERE match_id = ?", (match_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def add_match_player(match_id: int, user_id: int, team: int, rating_before: int = 0) -> None:
    """Добавить игрока в матч"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            INSERT INTO match_players (match_id, user_id, team, rating_before)
            VALUES (?, ?, ?, ?)
        """, (match_id, user_id, team, rating_before))
        await db.commit()


async def get_match_players(match_id: int, team: int = None) -> List[Dict[str, Any]]:
    """Получить игроков матча"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        if team:
            query = """
                SELECT mp.*, u.username, u.full_name, u.rating,
                       u.game_nickname, u.game_id, u.wins, u.losses
                FROM match_players mp
                JOIN users u ON mp.user_id = u.user_id
                WHERE mp.match_id = ? AND mp.team = ?
            """
            async with db.execute(query, (match_id, team)) as cursor:
                rows = await cursor.fetchall()
        else:
            query = """
                SELECT mp.*, u.username, u.full_name, u.rating,
                       u.game_nickname, u.game_id, u.wins, u.losses
                FROM match_players mp
                JOIN users u ON mp.user_id = u.user_id
                WHERE mp.match_id = ?
            """
            async with db.execute(query, (match_id,)) as cursor:
                rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def update_match_result(match_id: int, team1_score: int, team2_score: int, 
                              winner_team: int) -> None:
    """Обновить результат матча"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            UPDATE matches SET 
                team1_score = ?,
                team2_score = ?,
                winner_team = ?,
                status = 'finished',
                finished_at = ?
            WHERE match_id = ?
        """, (team1_score, team2_score, winner_team, datetime.now(), match_id))
        await db.commit()


async def update_match_player_stats(match_id: int, user_id: int, kills: int, 
                                    deaths: int, assists: int, is_mvp: bool,
                                    rating_change: int) -> None:
    """Обновить статистику игрока в матче"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            UPDATE match_players SET 
                kills = ?,
                deaths = ?,
                assists = ?,
                is_mvp = ?,
                rating_change = ?
            WHERE match_id = ? AND user_id = ?
        """, (kills, deaths, assists, 1 if is_mvp else 0, rating_change, match_id, user_id))
        await db.commit()


async def get_user_active_match(user_id: int) -> Optional[Dict[str, Any]]:
    """Получить активный матч пользователя"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = """
            SELECT m.* FROM matches m
            JOIN match_players mp ON m.match_id = mp.match_id
            WHERE mp.user_id = ? AND m.status = 'active'
        """
        async with db.execute(query, (user_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def get_pending_matches() -> List[Dict[str, Any]]:
    """Получить матчи, ожидающие проверки"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = """
            SELECT m.*, ms.submission_id, ms.screenshot_file_id, ms.submitted_by
            FROM matches m
            JOIN match_submissions ms ON m.match_id = ms.match_id
            WHERE ms.status = 'pending'
            ORDER BY ms.submitted_at
        """
        async with db.execute(query) as cursor:
            rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_user_match_history(user_id: int, limit: int = 10, include_cancelled: bool = True) -> List[Dict[str, Any]]:
    """
    Получить историю матчей пользователя.
    
    Args:
        user_id: ID пользователя
        limit: Максимальное количество матчей
        include_cancelled: Включать отменённые матчи (по умолчанию True)
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        if include_cancelled:
            query = """
                SELECT m.*, mp.team, mp.kills, mp.deaths, mp.assists, mp.is_mvp, mp.rating_change
                FROM matches m
                JOIN match_players mp ON m.match_id = mp.match_id
                WHERE mp.user_id = ? AND m.status IN ('finished', 'cancelled')
                ORDER BY COALESCE(m.finished_at, m.created_at) DESC
                LIMIT ?
            """
        else:
            query = """
                SELECT m.*, mp.team, mp.kills, mp.deaths, mp.assists, mp.is_mvp, mp.rating_change
                FROM matches m
                JOIN match_players mp ON m.match_id = mp.match_id
                WHERE mp.user_id = ? AND m.status = 'finished'
                ORDER BY m.finished_at DESC
                LIMIT ?
            """
        async with db.execute(query, (user_id, limit)) as cursor:
            rows = await cursor.fetchall()
        return [dict(row) for row in rows]


# ============ SUBMISSION FUNCTIONS ============

async def create_submission(match_id: int, submitted_by: int, screenshot_file_id: str) -> int:
    """Создать заявку на проверку результатов"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO match_submissions (match_id, submitted_by, screenshot_file_id)
            VALUES (?, ?, ?)
        """, (match_id, submitted_by, screenshot_file_id))
        submission_id = cursor.lastrowid
        await db.commit()
        return submission_id


async def get_submission(submission_id: int) -> Optional[Dict[str, Any]]:
    """Получить заявку по ID"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM match_submissions WHERE submission_id = ?", 
            (submission_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def update_submission_status(submission_id: int, status: str, reviewed_by: int) -> None:
    """Обновить статус заявки"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            UPDATE match_submissions SET 
                status = ?,
                reviewed_by = ?,
                reviewed_at = ?
            WHERE submission_id = ?
        """, (status, reviewed_by, datetime.now(), submission_id))
        await db.commit()


async def get_pending_submissions() -> List[Dict[str, Any]]:
    """Получить заявки, ожидающие проверки"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = """
            SELECT ms.*, m.map_name, m.platform, m.team1_avg_rating, m.team2_avg_rating,
                   u.username as submitter_name
            FROM match_submissions ms
            JOIN matches m ON ms.match_id = m.match_id
            JOIN users u ON ms.submitted_by = u.user_id
            WHERE ms.status = 'pending'
            ORDER BY ms.submitted_at
        """
        async with db.execute(query) as cursor:
            rows = await cursor.fetchall()
        return [dict(row) for row in rows]


# ============ READY CHECK FUNCTIONS ============

async def create_ready_check(match_id: int, user_id: int, message_id: int = None) -> bool:
    """Создать запись проверки готовности для игрока"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        try:
            await db.execute("""
                INSERT OR REPLACE INTO match_ready_checks (match_id, user_id, is_ready, message_id, responded_at)
                VALUES (?, ?, 0, ?, NULL)
            """, (match_id, user_id, message_id))
            await db.commit()
            return True
        except Exception:
            return False


async def set_player_ready(match_id: int, user_id: int, is_ready: bool = True) -> bool:
    """Установить статус готовности игрока"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        try:
            await db.execute("""
                UPDATE match_ready_checks 
                SET is_ready = ?, responded_at = ?
                WHERE match_id = ? AND user_id = ?
            """, (1 if is_ready else 0, datetime.now(), match_id, user_id))
            await db.commit()
            return True
        except Exception:
            return False


async def update_ready_check_message(match_id: int, user_id: int, message_id: int) -> None:
    """Обновить ID сообщения для ready check"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            UPDATE match_ready_checks SET message_id = ?
            WHERE match_id = ? AND user_id = ?
        """, (message_id, match_id, user_id))
        await db.commit()


async def get_ready_check_status(match_id: int) -> Dict[str, Any]:
    """Получить статус готовности всех игроков в матче"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = """
            SELECT rc.*, u.username, u.full_name
            FROM match_ready_checks rc
            JOIN users u ON rc.user_id = u.user_id
            WHERE rc.match_id = ?
        """
        async with db.execute(query, (match_id,)) as cursor:
            rows = await cursor.fetchall()
        
        players = [dict(row) for row in rows]
        ready_count = sum(1 for p in players if p['is_ready'])
        total_count = len(players)
        all_ready = ready_count == total_count and total_count > 0
        
        return {
            'players': players,
            'ready_count': ready_count,
            'total_count': total_count,
            'all_ready': all_ready
        }


async def get_player_ready_check(match_id: int, user_id: int) -> Optional[Dict[str, Any]]:
    """Получить запись ready check для конкретного игрока"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM match_ready_checks WHERE match_id = ? AND user_id = ?",
            (match_id, user_id)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def get_not_ready_players(match_id: int) -> List[Dict[str, Any]]:
    """Получить игроков, которые не подтвердили готовность"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = """
            SELECT rc.*, u.username, u.full_name
            FROM match_ready_checks rc
            JOIN users u ON rc.user_id = u.user_id
            WHERE rc.match_id = ? AND rc.is_ready = 0
        """
        async with db.execute(query, (match_id,)) as cursor:
            rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def delete_ready_checks(match_id: int) -> None:
    """Удалить все записи ready check для матча"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("DELETE FROM match_ready_checks WHERE match_id = ?", (match_id,))
        await db.commit()


async def get_match_by_ready_check(user_id: int) -> Optional[Dict[str, Any]]:
    """Получить матч, для которого у игрока есть активный ready check"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = """
            SELECT m.* FROM matches m
            JOIN match_ready_checks rc ON m.match_id = rc.match_id
            WHERE rc.user_id = ? AND m.status = 'pending'
        """
        async with db.execute(query, (user_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def update_match_status(match_id: int, status: str) -> None:
    """Обновить статус матча"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("UPDATE matches SET status = ? WHERE match_id = ?", (status, match_id))
        await db.commit()


async def cancel_match(match_id: int) -> None:
    """Отменить матч (удалить все связанные данные)"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Удаляем ready checks
        await db.execute("DELETE FROM match_ready_checks WHERE match_id = ?", (match_id,))
        # Удаляем игроков матча
        await db.execute("DELETE FROM match_players WHERE match_id = ?", (match_id,))
        # Обновляем статус матча на cancelled
        await db.execute("UPDATE matches SET status = 'cancelled' WHERE match_id = ?", (match_id,))
        await db.commit()


async def try_start_match_atomically(match_id: int) -> bool:
    """
    Атомарно попытаться запустить матч.
    Возвращает True если матч успешно запущен, False если уже был запущен другим процессом.
    Это защищает от race condition когда несколько игроков одновременно подтверждают готовность.
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Проверяем что матч в статусе pending и получаем формат
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT status, game_format FROM matches WHERE match_id = ?", 
            (match_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if not row or row['status'] != 'pending':
                return False  # Матч уже не pending
            
            game_format = row['game_format'] or '5x5'
        
        # Определяем размер матча по формату
        from config import GAME_FORMATS
        format_data = GAME_FORMATS.get(game_format, GAME_FORMATS['5x5'])
        match_size = format_data['match_size']
        
        # Проверяем что все игроки готовы (количество зависит от формата)
        async with db.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN is_ready = 1 THEN 1 ELSE 0 END) as ready_count
            FROM match_ready_checks 
            WHERE match_id = ?
        """, (match_id,)) as cursor:
            row = await cursor.fetchone()
            if not row or row['total'] != match_size or row['ready_count'] != match_size:
                return False  # Не все готовы или неправильное количество игроков
        
        # Атомарно обновляем статус (UPDATE вернёт 0 строк если статус уже изменился)
        cursor = await db.execute("""
            UPDATE matches SET status = 'active' 
            WHERE match_id = ? AND status = 'pending'
        """, (match_id,))
        
        if cursor.rowcount == 0:
            return False  # Другой процесс уже изменил статус
        
        await db.commit()
        return True


async def set_player_ready_and_check(match_id: int, user_id: int) -> Dict[str, Any]:
    """
    Установить готовность игрока и вернуть текущий статус.
    Возвращает словарь с информацией о статусе ready check.
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        # Проверяем статус матча и получаем формат
        async with db.execute(
            "SELECT status, game_format FROM matches WHERE match_id = ?", 
            (match_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return {'success': False, 'error': 'match_not_found'}
            if row['status'] != 'pending':
                return {'success': False, 'error': 'match_not_pending', 'status': row['status']}
            game_format = row['game_format'] or '5x5'
        
        # Получаем размер матча для данного формата
        from config import GAME_FORMATS
        format_data = GAME_FORMATS.get(game_format, GAME_FORMATS['5x5'])
        match_size = format_data['match_size']
        
        # Проверяем что игрок в этом матче
        async with db.execute(
            "SELECT is_ready FROM match_ready_checks WHERE match_id = ? AND user_id = ?",
            (match_id, user_id)
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return {'success': False, 'error': 'player_not_in_match'}
            if row['is_ready'] == 1:
                return {'success': False, 'error': 'already_ready'}
        
        # Устанавливаем готовность
        await db.execute("""
            UPDATE match_ready_checks 
            SET is_ready = 1, responded_at = ?
            WHERE match_id = ? AND user_id = ?
        """, (datetime.now(), match_id, user_id))
        
        # Получаем текущий статус
        async with db.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN is_ready = 1 THEN 1 ELSE 0 END) as ready_count
            FROM match_ready_checks 
            WHERE match_id = ?
        """, (match_id,)) as cursor:
            row = await cursor.fetchone()
            total = row['total']
            ready_count = row['ready_count']
        
        await db.commit()
        
        return {
            'success': True,
            'ready_count': ready_count,
            'total_count': total,
            'all_ready': ready_count == total and total == match_size
        }


async def get_user_pending_match(user_id: int) -> Optional[Dict[str, Any]]:
    """Получить pending матч пользователя (в статусе ready check)"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = """
            SELECT m.* FROM matches m
            JOIN match_players mp ON m.match_id = mp.match_id
            WHERE mp.user_id = ? AND m.status = 'pending'
        """
        async with db.execute(query, (user_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def is_user_in_active_or_pending_match(user_id: int) -> bool:
    """Проверить, участвует ли пользователь в активном или pending матче"""
    from config import READY_CHECK_TIMEOUT
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Проверяем только матчи, которые не просрочены
        # Pending матчи старше READY_CHECK_TIMEOUT + 60 секунд считаются зависшими
        query = """
            SELECT 1 FROM matches m
            JOIN match_players mp ON m.match_id = mp.match_id
            WHERE mp.user_id = ? AND (
                m.status = 'active' 
                OR (m.status = 'pending' AND datetime(m.created_at, '+' || ? || ' seconds') > datetime('now'))
            )
            LIMIT 1
        """
        timeout_with_buffer = READY_CHECK_TIMEOUT + 60  # Добавляем буфер на случай задержек
        async with db.execute(query, (user_id, timeout_with_buffer)) as cursor:
            return await cursor.fetchone() is not None


async def is_user_in_pending_match(user_id: int) -> bool:
    """Проверить, участвует ли пользователь только в pending матче (ready check)"""
    from config import READY_CHECK_TIMEOUT
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Проверяем только pending матчи, которые не просрочены
        query = """
            SELECT 1 FROM matches m
            JOIN match_players mp ON m.match_id = mp.match_id
            WHERE mp.user_id = ? 
            AND m.status = 'pending' 
            AND datetime(m.created_at, '+' || ? || ' seconds') > datetime('now')
            LIMIT 1
        """
        timeout_with_buffer = READY_CHECK_TIMEOUT + 60
        async with db.execute(query, (user_id, timeout_with_buffer)) as cursor:
            return await cursor.fetchone() is not None


async def cleanup_stale_ready_checks(timeout_seconds: int = 120) -> List[int]:
    """
    Очистить зависшие ready checks (матчи в статусе pending дольше timeout).
    Возвращает список отменённых match_id.
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Находим зависшие матчи
        query = """
            SELECT match_id FROM matches 
            WHERE status = 'pending' 
            AND datetime(created_at, '+' || ? || ' seconds') < datetime('now')
        """
        async with db.execute(query, (timeout_seconds,)) as cursor:
            rows = await cursor.fetchall()
        
        cancelled_matches = [row[0] for row in rows]
        
        # Отменяем каждый
        for match_id in cancelled_matches:
            await db.execute("DELETE FROM match_ready_checks WHERE match_id = ?", (match_id,))
            await db.execute("DELETE FROM match_players WHERE match_id = ?", (match_id,))
            await db.execute("UPDATE matches SET status = 'cancelled' WHERE match_id = ?", (match_id,))
        
        await db.commit()
        return cancelled_matches


# ============ TICKET FUNCTIONS ============

async def create_ticket(user_id: int, ticket_type: str, message: str, photo_file_id: str = None) -> int:
    """Создать новый тикет"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO tickets (user_id, ticket_type, message, photo_file_id, status)
            VALUES (?, ?, ?, ?, 'open')
        """, (user_id, ticket_type, message, photo_file_id))
        ticket_id = cursor.lastrowid
        await db.commit()
        return ticket_id


async def get_ticket(ticket_id: int) -> Optional[Dict[str, Any]]:
    """Получить тикет по ID"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM tickets WHERE ticket_id = ?", 
            (ticket_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def get_open_tickets() -> List[Dict[str, Any]]:
    """Получить все открытые тикеты"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = """
            SELECT t.*, u.username, u.full_name, u.game_nickname
            FROM tickets t
            JOIN users u ON t.user_id = u.user_id
            WHERE t.status = 'open'
            ORDER BY t.created_at ASC
        """
        async with db.execute(query) as cursor:
            rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_user_tickets(user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    """Получить тикеты пользователя"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = """
            SELECT * FROM tickets 
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """
        async with db.execute(query, (user_id, limit)) as cursor:
            rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def respond_to_ticket(ticket_id: int, admin_response: str, responded_by: int) -> None:
    """Ответить на тикет (устаревший метод для совместимости)"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            UPDATE tickets SET 
                admin_response = ?,
                responded_by = ?,
                status = 'answered'
            WHERE ticket_id = ?
        """, (admin_response, responded_by, ticket_id))
        await db.commit()
    
    # Также добавляем в историю сообщений
    await add_ticket_message(ticket_id, responded_by, admin_response, is_admin=True)


async def add_ticket_message(ticket_id: int, user_id: int, message: str, is_admin: bool = False, photo_file_id: str = None) -> int:
    """Добавить сообщение в тикет"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO ticket_messages (ticket_id, user_id, message, is_admin, photo_file_id)
            VALUES (?, ?, ?, ?, ?)
        """, (ticket_id, user_id, message, 1 if is_admin else 0, photo_file_id))
        message_id = cursor.lastrowid
        await db.commit()
        return message_id


async def get_ticket_messages(ticket_id: int) -> List[Dict[str, Any]]:
    """Получить все сообщения тикета"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = """
            SELECT tm.*, u.username, u.full_name, u.game_nickname
            FROM ticket_messages tm
            JOIN users u ON tm.user_id = u.user_id
            WHERE tm.ticket_id = ?
            ORDER BY tm.created_at ASC
        """
        async with db.execute(query, (ticket_id,)) as cursor:
            rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_all_tickets(status: str = None, limit: int = 50) -> List[Dict[str, Any]]:
    """Получить все тикеты (для модераторов)"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        if status:
            query = """
                SELECT t.*, u.username, u.full_name, u.game_nickname,
                       r.username as responder_username, r.full_name as responder_name
                FROM tickets t
                JOIN users u ON t.user_id = u.user_id
                LEFT JOIN users r ON t.responded_by = r.user_id
                WHERE t.status = ?
                ORDER BY t.created_at DESC
                LIMIT ?
            """
            async with db.execute(query, (status, limit)) as cursor:
                rows = await cursor.fetchall()
        else:
            query = """
                SELECT t.*, u.username, u.full_name, u.game_nickname,
                       r.username as responder_username, r.full_name as responder_name
                FROM tickets t
                JOIN users u ON t.user_id = u.user_id
                LEFT JOIN users r ON t.responded_by = r.user_id
                ORDER BY t.created_at DESC
                LIMIT ?
            """
            async with db.execute(query, (limit,)) as cursor:
                rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def reopen_ticket(ticket_id: int) -> None:
    """Переоткрыть тикет (сменить статус на open)"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            UPDATE tickets SET status = 'open' WHERE ticket_id = ?
        """, (ticket_id,))
        await db.commit()


async def close_ticket(ticket_id: int, responded_by: int) -> None:
    """Закрыть тикет"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            UPDATE tickets SET 
                status = 'closed',
                responded_by = ?,
                closed_at = ?
            WHERE ticket_id = ?
        """, (responded_by, datetime.now(), ticket_id))
        await db.commit()


async def get_ticket_stats() -> Dict[str, int]:
    """Получить статистику по тикетам"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        stats = {}
        
        # Общее количество
        async with db.execute("SELECT COUNT(*) FROM tickets") as cursor:
            stats['total'] = (await cursor.fetchone())[0]
        
        # Открытые
        async with db.execute("SELECT COUNT(*) FROM tickets WHERE status = 'open'") as cursor:
            stats['open'] = (await cursor.fetchone())[0]
        
        # Отвеченные
        async with db.execute("SELECT COUNT(*) FROM tickets WHERE status = 'answered'") as cursor:
            stats['answered'] = (await cursor.fetchone())[0]
        
        # Закрытые
        async with db.execute("SELECT COUNT(*) FROM tickets WHERE status = 'closed'") as cursor:
            stats['closed'] = (await cursor.fetchone())[0]
        
        return stats


# ============ AI VERIFICATION FUNCTIONS ============

async def create_ai_verification(
    submission_id: int,
    match_id: int,
    ai_result: str,
    confidence: float,
    team1_score: int = None,
    team2_score: int = None,
    winner_team: int = None,
    mvp_user_id: int = None
) -> int:
    """Создать запись AI проверки"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO ai_verifications 
            (submission_id, match_id, ai_result, confidence, team1_score, team2_score, winner_team, mvp_user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (submission_id, match_id, ai_result, confidence, team1_score, team2_score, winner_team, mvp_user_id))
        verification_id = cursor.lastrowid
        await db.commit()
        return verification_id


async def get_ai_verification(verification_id: int) -> Optional[Dict[str, Any]]:
    """Получить AI проверку по ID"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM ai_verifications WHERE verification_id = ?",
            (verification_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def get_ai_verification_by_submission(submission_id: int) -> Optional[Dict[str, Any]]:
    """Получить AI проверку по ID заявки"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM ai_verifications WHERE submission_id = ? ORDER BY created_at DESC LIMIT 1",
            (submission_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def get_pending_ai_verifications() -> List[Dict[str, Any]]:
    """Получить AI проверки, ожидающие подтверждения администратора"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = """
            SELECT av.*, m.map_name, m.platform, m.team1_avg_rating, m.team2_avg_rating,
                   m.team1_start_side, m.team2_start_side, m.game_format,
                   ms.screenshot_file_id, ms.submitted_by,
                   u.username as submitter_name
            FROM ai_verifications av
            JOIN matches m ON av.match_id = m.match_id
            JOIN match_submissions ms ON av.submission_id = ms.submission_id
            JOIN users u ON ms.submitted_by = u.user_id
            WHERE av.status = 'pending'
            ORDER BY av.created_at ASC
        """
        async with db.execute(query) as cursor:
            rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def update_ai_verification_status(
    verification_id: int,
    status: str,
    admin_id: int,
    admin_action: str
) -> None:
    """Обновить статус AI проверки"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            UPDATE ai_verifications SET 
                status = ?,
                admin_id = ?,
                admin_action = ?,
                reviewed_at = ?
            WHERE verification_id = ?
        """, (status, admin_id, admin_action, datetime.now(), verification_id))
        await db.commit()


async def update_ai_verification_result(
    verification_id: int,
    team1_score: int,
    team2_score: int,
    winner_team: int,
    mvp_user_id: int = None
) -> None:
    """Обновить результаты AI проверки (после редактирования администратором)"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            UPDATE ai_verifications SET 
                team1_score = ?,
                team2_score = ?,
                winner_team = ?,
                mvp_user_id = ?
            WHERE verification_id = ?
        """, (team1_score, team2_score, winner_team, mvp_user_id, verification_id))
        await db.commit()


async def revert_match_result(match_id: int) -> bool:
    """
    Отменить результаты матча и вернуть статистику игроков.
    Возвращает True если успешно, False если матч не найден или не был завершён.
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        # Проверяем что матч существует и завершён
        async with db.execute(
            "SELECT * FROM matches WHERE match_id = ? AND status = 'finished'",
            (match_id,)
        ) as cursor:
            match = await cursor.fetchone()
            if not match:
                return False
        
        # Получаем игроков матча с их изменениями статистики
        async with db.execute(
            "SELECT * FROM match_players WHERE match_id = ?",
            (match_id,)
        ) as cursor:
            players = await cursor.fetchall()
        
        winner_team = match['winner_team']
        
        # Откатываем статистику каждого игрока
        for player in players:
            user_id = player['user_id']
            team = player['team']
            kills = player['kills'] or 0
            deaths = player['deaths'] or 0
            assists = player['assists'] or 0
            is_mvp = player['is_mvp']
            rating_change = player['rating_change'] or 0
            
            is_winner = team == winner_team
            
            # Откатываем статистику (вычитаем то что было добавлено)
            await db.execute("""
                UPDATE users SET 
                    wins = wins - ?,
                    losses = losses - ?,
                    kills = MAX(0, kills - ?),
                    deaths = MAX(0, deaths - ?),
                    assists = MAX(0, assists - ?),
                    rating = MAX(?, rating - ?),
                    mvp_count = MAX(0, mvp_count - ?)
                WHERE user_id = ?
            """, (
                1 if is_winner else 0,
                0 if is_winner else 1,
                kills,
                deaths,
                assists,
                MIN_RATING,
                rating_change,
                1 if is_mvp else 0,
                user_id
            ))
        
        # Возвращаем матч в статус active
        await db.execute("""
            UPDATE matches SET 
                status = 'active',
                team1_score = 0,
                team2_score = 0,
                winner_team = NULL,
                finished_at = NULL
            WHERE match_id = ?
        """, (match_id,))
        
        # Сбрасываем статистику игроков в матче
        await db.execute("""
            UPDATE match_players SET 
                kills = 0,
                deaths = 0,
                assists = 0,
                is_mvp = 0,
                rating_change = 0
            WHERE match_id = ?
        """, (match_id,))
        
        await db.commit()
        return True


async def cancel_finished_match(match_id: int) -> Dict[str, Any]:
    """
    Отменить завершённый матч с возвратом рейтинга всем участникам.
    Матч помечается как 'cancelled' в базе данных.
    
    Returns:
        Словарь с результатом:
        - success: bool
        - error: str (если есть ошибка)
        - affected_players: List[int] (user_id затронутых игроков)
        - rating_reverted: Dict[int, int] (user_id -> вернувшийся рейтинг)
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        # Проверяем что матч существует и завершён
        async with db.execute(
            "SELECT * FROM matches WHERE match_id = ?",
            (match_id,)
        ) as cursor:
            match = await cursor.fetchone()
            if not match:
                return {'success': False, 'error': 'match_not_found'}
            
            if match['status'] == 'cancelled':
                return {'success': False, 'error': 'already_cancelled'}
            
            if match['status'] != 'finished':
                return {'success': False, 'error': 'match_not_finished'}
        
        # Получаем игроков матча с их изменениями статистики
        async with db.execute(
            "SELECT * FROM match_players WHERE match_id = ?",
            (match_id,)
        ) as cursor:
            players = await cursor.fetchall()
        
        if not players:
            return {'success': False, 'error': 'no_players_found'}
        
        winner_team = match['winner_team']
        affected_players = []
        rating_reverted = {}
        
        # Откатываем статистику каждого игрока
        for player in players:
            user_id = player['user_id']
            team = player['team']
            kills = player['kills'] or 0
            deaths = player['deaths'] or 0
            assists = player['assists'] or 0
            is_mvp = player['is_mvp']
            rating_change = player['rating_change'] or 0
            
            is_winner = team == winner_team
            
            # Откатываем статистику (вычитаем то что было добавлено)
            await db.execute("""
                UPDATE users SET 
                    wins = wins - ?,
                    losses = losses - ?,
                    kills = MAX(0, kills - ?),
                    deaths = MAX(0, deaths - ?),
                    assists = MAX(0, assists - ?),
                    rating = MAX(?, rating - ?),
                    mvp_count = MAX(0, mvp_count - ?)
                WHERE user_id = ?
            """, (
                1 if is_winner else 0,
                0 if is_winner else 1,
                kills,
                deaths,
                assists,
                MIN_RATING,
                rating_change,
                1 if is_mvp else 0,
                user_id
            ))
            
            affected_players.append(user_id)
            rating_reverted[user_id] = -rating_change  # Отрицательное изменение - это возврат
        
        # Помечаем матч как отменённый (сохраняем результаты для истории)
        await db.execute("""
            UPDATE matches SET 
                status = 'cancelled'
            WHERE match_id = ?
        """, (match_id,))
        
        await db.commit()
        
        return {
            'success': True,
            'affected_players': affected_players,
            'rating_reverted': rating_reverted
        }


async def get_user_finished_matches(user_id: int) -> List[Dict[str, Any]]:
    """
    Получить все завершённые (не отменённые) матчи пользователя.
    Используется для отмены матчей при бане.
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = """
            SELECT m.*, mp.team, mp.kills, mp.deaths, mp.assists, mp.is_mvp, mp.rating_change
            FROM matches m
            JOIN match_players mp ON m.match_id = mp.match_id
            WHERE mp.user_id = ? AND m.status = 'finished'
            ORDER BY m.finished_at DESC
        """
        async with db.execute(query, (user_id,)) as cursor:
            rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_all_banned_users() -> List[Dict[str, Any]]:
    """Получить всех забаненных пользователей"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE is_banned = 1"
        ) as cursor:
            rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_user_matches_for_cancellation(user_id: int) -> List[Dict[str, Any]]:
    """
    Получить все матчи пользователя, которые можно/нужно отменить при бане:
    - finished (откатываем рейтинг/статы)
    - active/pending (просто помечаем cancelled, без рейтинга)

    Возвращает список матчей (строки matches.* + status).
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = """
            SELECT DISTINCT m.*
            FROM matches m
            JOIN match_players mp ON m.match_id = mp.match_id
            WHERE mp.user_id = ?
              AND m.status IN ('finished', 'active', 'pending')
            ORDER BY COALESCE(m.finished_at, m.created_at) DESC
        """
        async with db.execute(query, (user_id,)) as cursor:
            rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def cancel_active_or_pending_match(match_id: int) -> Dict[str, Any]:
    """
    Отменить матч в статусе active/pending.
    Рейтинг не трогаем (он ещё не применён), но матч должен отображаться как cancelled в истории.

    Идемпотентно: если уже cancelled — вернёт already_cancelled.
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row

        async with db.execute("SELECT status FROM matches WHERE match_id = ?", (match_id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                return {"success": False, "error": "match_not_found"}
            status = row["status"]

        if status == "cancelled":
            return {"success": False, "error": "already_cancelled"}

        if status not in ("active", "pending"):
            return {"success": False, "error": "match_not_active_or_pending", "status": status}

        await db.execute("DELETE FROM match_ready_checks WHERE match_id = ?", (match_id,))
        # игроков матча НЕ удаляем, иначе матч пропадёт из истории участников
        await db.execute("UPDATE matches SET status = 'cancelled' WHERE match_id = ?", (match_id,))
        await db.commit()

        return {"success": True}


async def cancel_all_user_matches(user_id: int) -> Dict[str, Any]:
    """
    Отменить все матчи пользователя (для бана):
    - finished: через cancel_finished_match (возврат рейтинга/статистики)
    - active/pending: через cancel_active_or_pending_match

    Returns:
        - cancelled_count: int
        - match_ids: List[int]
        - errors: List[str]
    """
    matches = await get_user_matches_for_cancellation(user_id)

    cancelled_count = 0
    cancelled_match_ids = []
    errors = []

    for match in matches:
        match_id = match["match_id"]
        status = match.get("status")

        if status == "finished":
            result = await cancel_finished_match(match_id)
        else:
            result = await cancel_active_or_pending_match(match_id)

        if result.get("success"):
            cancelled_count += 1
            cancelled_match_ids.append(match_id)
        elif result.get("error") != "already_cancelled":
            errors.append(f"Match {match_id}: {result.get('error')}")

    return {"cancelled_count": cancelled_count, "match_ids": cancelled_match_ids, "errors": errors}


async def get_match_players_stats(match_id: int) -> List[Dict[str, Any]]:
    """Получить статистику игроков в матче для отката"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = """
            SELECT mp.*, u.username, u.full_name, u.game_nickname, u.rating
            FROM match_players mp
            JOIN users u ON mp.user_id = u.user_id
            WHERE mp.match_id = ?
        """
        async with db.execute(query, (match_id,)) as cursor:
            rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_all_admins_and_moderators() -> List[Dict[str, Any]]:
    """Получить всех администраторов и модераторов"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = """
            SELECT user_id, username, full_name, is_admin, is_moderator
            FROM users 
            WHERE is_admin = 1 OR is_moderator = 1
        """
        async with db.execute(query) as cursor:
            rows = await cursor.fetchall()
        
        result = [dict(row) for row in rows]
        
        # Также добавляем админов из конфига, если их нет в БД
        from config import ADMIN_IDS, MODERATOR_IDS
        existing_ids = {r['user_id'] for r in result}
        
        for admin_id in ADMIN_IDS:
            if admin_id not in existing_ids:
                result.append({
                    'user_id': admin_id,
                    'username': None,
                    'full_name': None,
                    'is_admin': True,
                    'is_moderator': False
                })
                existing_ids.add(admin_id)
        
        for mod_id in MODERATOR_IDS:
            if mod_id not in existing_ids:
                result.append({
                    'user_id': mod_id,
                    'username': None,
                    'full_name': None,
                    'is_admin': False,
                    'is_moderator': True
                })
                existing_ids.add(mod_id)
        
        return result


# ============ SYSTEM SETTINGS FUNCTIONS ============

async def get_system_setting(key: str) -> Optional[str]:
    """Получить системную настройку по ключу"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            "SELECT value FROM system_settings WHERE key = ?",
            (key,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None


async def set_system_setting(key: str, value: str) -> None:
    """Установить системную настройку"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            INSERT OR REPLACE INTO system_settings (key, value, updated_at)
            VALUES (?, ?, ?)
        """, (key, value, datetime.now()))
        await db.commit()


async def delete_system_setting(key: str) -> None:
    """Удалить системную настройку"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("DELETE FROM system_settings WHERE key = ?", (key,))
        await db.commit()


async def is_registration_closed() -> bool:
    """Проверить, закрыта ли регистрация"""
    value = await get_system_setting("registration_closed_until")
    if not value:
        return False
    
    try:
        closed_until = datetime.fromisoformat(value)
        return datetime.now() < closed_until
    except (ValueError, TypeError):
        return False


async def get_registration_closed_until() -> Optional[datetime]:
    """Получить время до которого закрыта регистрация"""
    value = await get_system_setting("registration_closed_until")
    if not value:
        return None
    
    try:
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None


async def close_registration(until: datetime, reason: str = None) -> None:
    """Закрыть регистрацию до указанного времени"""
    await set_system_setting("registration_closed_until", until.isoformat())
    if reason:
        await set_system_setting("registration_closed_reason", reason)


async def open_registration() -> None:
    """Открыть регистрацию"""
    await delete_system_setting("registration_closed_until")
    await delete_system_setting("registration_closed_reason")


async def get_registration_closed_reason() -> Optional[str]:
    """Получить причину закрытия регистрации"""
    return await get_system_setting("registration_closed_reason")


# ============ MASS BAN FUNCTIONS ============

async def get_users_registered_between(
    from_date: datetime, 
    to_date: datetime,
    include_banned: bool = False
) -> List[Dict[str, Any]]:
    """
    Получить пользователей, зарегистрированных в указанный промежуток времени
    
    Args:
        from_date: Начало периода
        to_date: Конец периода
        include_banned: Включать уже забаненных пользователей
    
    Returns:
        Список пользователей
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        if include_banned:
            query = """
                SELECT * FROM users 
                WHERE registered_at >= ? AND registered_at <= ?
                ORDER BY registered_at DESC
            """
        else:
            query = """
                SELECT * FROM users 
                WHERE registered_at >= ? AND registered_at <= ? AND is_banned = 0
                ORDER BY registered_at DESC
            """
        
        async with db.execute(query, (from_date.isoformat(), to_date.isoformat())) as cursor:
            rows = await cursor.fetchall()
        
        return [dict(row) for row in rows]


async def ban_users_by_ids(user_ids: List[int]) -> int:
    """
    Забанить пользователей по списку ID
    
    Args:
        user_ids: Список ID пользователей для бана
    
    Returns:
        Количество забаненных пользователей
    """
    if not user_ids:
        return 0
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        placeholders = ','.join('?' * len(user_ids))
        cursor = await db.execute(
            f"UPDATE users SET is_banned = 1 WHERE user_id IN ({placeholders}) AND is_banned = 0",
            user_ids
        )
        banned_count = cursor.rowcount
        await db.commit()
        return banned_count


async def ban_users_registered_between(
    from_date: datetime, 
    to_date: datetime,
    exclude_admins: bool = True,
    exclude_moderators: bool = True
) -> Dict[str, Any]:
    """
    Забанить всех пользователей, зарегистрированных в указанный промежуток времени
    
    Args:
        from_date: Начало периода
        to_date: Конец периода
        exclude_admins: Исключить администраторов
        exclude_moderators: Исключить модераторов
    
    Returns:
        Словарь с информацией о результате:
        - banned_count: количество забаненных
        - users: список забаненных пользователей
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        # Строим условие исключения
        exclude_conditions = ["is_banned = 0"]
        if exclude_admins:
            exclude_conditions.append("is_admin = 0")
        if exclude_moderators:
            exclude_conditions.append("is_moderator = 0")
        
        exclude_sql = " AND ".join(exclude_conditions)
        
        # Получаем пользователей для бана
        query = f"""
            SELECT * FROM users 
            WHERE registered_at >= ? AND registered_at <= ? AND {exclude_sql}
            ORDER BY registered_at DESC
        """
        
        async with db.execute(query, (from_date.isoformat(), to_date.isoformat())) as cursor:
            rows = await cursor.fetchall()
        
        users_to_ban = [dict(row) for row in rows]
        
        if not users_to_ban:
            return {'banned_count': 0, 'users': []}
        
        # Баним пользователей
        user_ids = [u['user_id'] for u in users_to_ban]
        placeholders = ','.join('?' * len(user_ids))
        
        await db.execute(
            f"UPDATE users SET is_banned = 1 WHERE user_id IN ({placeholders})",
            user_ids
        )
        await db.commit()
        
        return {
            'banned_count': len(users_to_ban),
            'users': users_to_ban
        }


async def log_blocked_registration_attempt(
    user_id: int,
    username: str = None,
    full_name: str = None,
    ban_applied: bool = True
) -> int:
    """
    Залогировать попытку регистрации при закрытой регистрации.
    
    Args:
        user_id: Telegram ID пользователя
        username: Telegram username
        full_name: Полное имя пользователя
        ban_applied: Был ли применён автоматический бан
    
    Returns:
        ID записи лога
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO blocked_registration_attempts 
            (user_id, username, full_name, ban_applied, attempted_at)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, username, full_name, 1 if ban_applied else 0, datetime.now()))
        log_id = cursor.lastrowid
        await db.commit()
        return log_id


async def get_blocked_registration_attempts(limit: int = 50) -> List[Dict[str, Any]]:
    """
    Получить список попыток регистрации при закрытой регистрации.
    
    Args:
        limit: Максимальное количество записей
    
    Returns:
        Список попыток
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = """
            SELECT * FROM blocked_registration_attempts
            ORDER BY attempted_at DESC
            LIMIT ?
        """
        async with db.execute(query, (limit,)) as cursor:
            rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_blocked_registration_count_today() -> int:
    """Получить количество заблокированных попыток регистрации за сегодня"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        async with db.execute(
            "SELECT COUNT(*) FROM blocked_registration_attempts WHERE attempted_at >= ?",
            (today_start.isoformat(),)
        ) as cursor:
            return (await cursor.fetchone())[0]


async def get_registration_stats(days: int = 7) -> Dict[str, Any]:
    """
    Получить статистику регистраций за последние N дней
    
    Args:
        days: Количество дней для анализа
    
    Returns:
        Словарь со статистикой:
        - total: общее количество за период
        - by_day: словарь {дата: количество}
        - banned: количество забаненных за период
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        from_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        from_date = from_date.replace(day=from_date.day - days + 1)
        
        # Общее количество за период
        async with db.execute(
            "SELECT COUNT(*) FROM users WHERE registered_at >= ?",
            (from_date.isoformat(),)
        ) as cursor:
            total = (await cursor.fetchone())[0]
        
        # Забаненные за период
        async with db.execute(
            "SELECT COUNT(*) FROM users WHERE registered_at >= ? AND is_banned = 1",
            (from_date.isoformat(),)
        ) as cursor:
            banned = (await cursor.fetchone())[0]
        
        # По дням
        by_day = {}
        async with db.execute("""
            SELECT DATE(registered_at) as reg_date, COUNT(*) as count
            FROM users 
            WHERE registered_at >= ?
            GROUP BY DATE(registered_at)
            ORDER BY reg_date
        """, (from_date.isoformat(),)) as cursor:
            rows = await cursor.fetchall()
            for row in rows:
                by_day[row[0]] = row[1]
        
        return {
            'total': total,
            'by_day': by_day,
            'banned': banned,
            'from_date': from_date.isoformat(),
            'days': days
        }
