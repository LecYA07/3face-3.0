import aiosqlite
from config import DATABASE_PATH, DEFAULT_RATING, MIN_RATING
from typing import Optional, List, Dict, Any
from datetime import datetime


async def init_db():
    """Инициализация базы данных"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
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
                platform TEXT DEFAULT 'pc',
                rating INTEGER,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
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


# ============ MATCHMAKING QUEUE FUNCTIONS ============

async def join_queue(user_id: int, platform: str, rating: int, party_id: int = None, game_format: str = "5x5") -> bool:
    """Добавить игрока в очередь поиска"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        try:
            await db.execute("""
                INSERT OR REPLACE INTO matchmaking_queue (user_id, platform, rating, party_id, game_format, joined_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, platform, rating, party_id, game_format, datetime.now()))
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
    """Получить активное лобби пользователя"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        query = """
            SELECT lp.lobby_id FROM lobby_players lp
            JOIN lobbies l ON lp.lobby_id = l.lobby_id
            WHERE lp.user_id = ? AND l.status = 'waiting'
        """
        async with db.execute(query, (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None


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


async def get_user_match_history(user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    """Получить историю матчей пользователя"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
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
