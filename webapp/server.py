"""
Telegram Mini App Server для 3FACE
- Чаты с техподдержкой
- История матчей
"""

import ssl
import json
import hashlib
import hmac
import urllib.parse
from datetime import datetime
from aiohttp import web
import aiosqlite
import logging

logger = logging.getLogger(__name__)

# Настройки
DATABASE_PATH = "../database.db"
BOT_TOKEN = None  # Будет установлен при запуске
TEST_MODE = False  # Режим тестирования (без авторизации)

routes = web.RouteTableDef()


def validate_init_data(init_data: str, bot_token: str) -> dict:
    """Валидация данных от Telegram Mini App"""
    if not init_data:
        return None
    
    try:
        # Парсим данные
        parsed = dict(urllib.parse.parse_qsl(init_data))
        
        # Получаем hash
        received_hash = parsed.pop('hash', None)
        if not received_hash:
            return None
        
        # Создаём строку для проверки
        data_check_string = '\n'.join(
            f"{k}={v}" for k, v in sorted(parsed.items())
        )
        
        # Создаём secret key
        secret_key = hmac.new(
            b"WebAppData",
            bot_token.encode(),
            hashlib.sha256
        ).digest()
        
        # Вычисляем hash
        calculated_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256
        ).hexdigest()
        
        if calculated_hash == received_hash:
            # Парсим user
            if 'user' in parsed:
                parsed['user'] = json.loads(parsed['user'])
            return parsed
        
        return None
    except Exception as e:
        logger.error(f"Init data validation error: {e}")
        return None


def get_user_id_from_request(request: web.Request) -> int:
    """Получить user_id из заголовков"""
    init_data = request.headers.get('X-Telegram-Init-Data', '')
    
    # В тестовом режиме возвращаем тестовый user_id
    if TEST_MODE and not init_data:
        return 123456789  # Тестовый пользователь
    
    if not init_data:
        return None
    
    validated = validate_init_data(init_data, BOT_TOKEN)
    if validated and 'user' in validated:
        return validated['user'].get('id')
    
    return None


# ========== API ROUTES ==========

@routes.get('/api/user')
async def get_user(request: web.Request):
    """Получить данные пользователя"""
    user_id = get_user_id_from_request(request)
    if not user_id:
        return web.json_response({'error': 'Unauthorized'}, status=401)
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE user_id = ?", 
            (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return web.json_response(dict(row))
            
            # В тестовом режиме возвращаем мок-данные
            if TEST_MODE:
                return web.json_response({
                    'user_id': user_id,
                    'username': 'testuser',
                    'full_name': 'Test User',
                    'game_nickname': 'TestPlayer',
                    'rating': 1250,
                    'wins': 15,
                    'losses': 10,
                    'kills': 180,
                    'deaths': 120,
                    'assists': 45,
                    'mvp_count': 5
                })
            
            return web.json_response({'error': 'User not found'}, status=404)


@routes.get('/api/matches')
async def get_match_history(request: web.Request):
    """Получить историю матчей пользователя"""
    user_id = get_user_id_from_request(request)
    if not user_id:
        return web.json_response({'error': 'Unauthorized'}, status=401)
    
    limit = int(request.query.get('limit', 20))
    offset = int(request.query.get('offset', 0))
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        # Получаем матчи
        query = """
            SELECT m.*, mp.team, mp.kills, mp.deaths, mp.assists, 
                   mp.is_mvp, mp.rating_change, mp.rating_before
            FROM matches m
            JOIN match_players mp ON m.match_id = mp.match_id
            WHERE mp.user_id = ? AND m.status = 'finished'
            ORDER BY m.finished_at DESC
            LIMIT ? OFFSET ?
        """
        async with db.execute(query, (user_id, limit, offset)) as cursor:
            matches = [dict(row) for row in await cursor.fetchall()]
        
        # Если нет матчей и тестовый режим - возвращаем мок-данные
        if not matches and TEST_MODE:
            return web.json_response({'matches': get_mock_matches()})
        
        # Для каждого матча получаем игроков
        for match in matches:
            async with db.execute(
                """SELECT mp.*, u.username, u.full_name, u.game_nickname
                   FROM match_players mp
                   JOIN users u ON mp.user_id = u.user_id
                   WHERE mp.match_id = ?""",
                (match['match_id'],)
            ) as cursor:
                match['players'] = [dict(row) for row in await cursor.fetchall()]
        
        return web.json_response({'matches': matches})


def get_mock_matches():
    """Мок-данные матчей для тестирования"""
    return [
        {
            'match_id': 1,
            'map_name': '🏜️ Sandstone',
            'team1_score': 13,
            'team2_score': 9,
            'team': 1,
            'winner_team': 1,
            'kills': 22,
            'deaths': 15,
            'assists': 8,
            'is_mvp': 1,
            'rating_change': 30,
            'team1_start_side': '🔴 Атака (T)',
            'team2_start_side': '🔵 Защита (CT)',
            'finished_at': '2026-03-16T18:30:00'
        },
        {
            'match_id': 2,
            'map_name': '🏢 Hanami',
            'team1_score': 8,
            'team2_score': 13,
            'team': 1,
            'winner_team': 2,
            'kills': 14,
            'deaths': 18,
            'assists': 5,
            'is_mvp': 0,
            'rating_change': -20,
            'team1_start_side': '🔵 Защита (CT)',
            'team2_start_side': '🔴 Атака (T)',
            'finished_at': '2026-03-15T20:15:00'
        },
        {
            'match_id': 3,
            'map_name': '🌊 Breeze',
            'team1_score': 13,
            'team2_score': 11,
            'team': 2,
            'winner_team': 1,
            'kills': 18,
            'deaths': 16,
            'assists': 7,
            'is_mvp': 0,
            'rating_change': -20,
            'team1_start_side': '🔴 Атака (T)',
            'team2_start_side': '🔵 Защита (CT)',
            'finished_at': '2026-03-14T19:00:00'
        },
        {
            'match_id': 4,
            'map_name': '🏭 Zone7',
            'team1_score': 13,
            'team2_score': 7,
            'team': 1,
            'winner_team': 1,
            'kills': 25,
            'deaths': 10,
            'assists': 12,
            'is_mvp': 1,
            'rating_change': 35,
            'team1_start_side': '🔵 Защита (CT)',
            'team2_start_side': '🔴 Атака (T)',
            'finished_at': '2026-03-13T21:45:00'
        }
    ]


@routes.get('/api/match/{match_id}')
async def get_match_details(request: web.Request):
    """Получить детали матча"""
    user_id = get_user_id_from_request(request)
    if not user_id:
        return web.json_response({'error': 'Unauthorized'}, status=401)
    
    match_id = int(request.match_info['match_id'])
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        # Получаем матч
        async with db.execute(
            "SELECT * FROM matches WHERE match_id = ?",
            (match_id,)
        ) as cursor:
            match = await cursor.fetchone()
            if not match:
                # В тестовом режиме возвращаем мок-данные
                if TEST_MODE:
                    mock_match = get_mock_match_details(match_id)
                    if mock_match:
                        return web.json_response(mock_match)
                return web.json_response({'error': 'Match not found'}, status=404)
            match = dict(match)
        
        # Получаем игроков
        async with db.execute(
            """SELECT mp.*, u.username, u.full_name, u.game_nickname, u.rating
               FROM match_players mp
               JOIN users u ON mp.user_id = u.user_id
               WHERE mp.match_id = ?""",
            (match_id,)
        ) as cursor:
            match['players'] = [dict(row) for row in await cursor.fetchall()]
        
        return web.json_response(match)


def get_mock_match_details(match_id: int):
    """Мок-данные для деталей матча"""
    matches = {
        1: {
            'match_id': 1,
            'map_name': '🏜️ Sandstone',
            'team1_score': 13,
            'team2_score': 9,
            'team1_start_side': '🔴 Атака (T)',
            'team2_start_side': '🔵 Защита (CT)',
            'winner_team': 1,
            'status': 'finished',
            'finished_at': '2026-03-16T18:30:00',
            'players': [
                {'user_id': 123456789, 'team': 1, 'game_nickname': 'TestPlayer', 'kills': 22, 'deaths': 15, 'assists': 8, 'is_mvp': 1, 'rating_change': 30},
                {'user_id': 2, 'team': 1, 'game_nickname': 'Player2', 'kills': 18, 'deaths': 14, 'assists': 6, 'is_mvp': 0, 'rating_change': 25},
                {'user_id': 3, 'team': 1, 'game_nickname': 'Player3', 'kills': 15, 'deaths': 13, 'assists': 9, 'is_mvp': 0, 'rating_change': 25},
                {'user_id': 4, 'team': 1, 'game_nickname': 'Player4', 'kills': 12, 'deaths': 16, 'assists': 7, 'is_mvp': 0, 'rating_change': 25},
                {'user_id': 5, 'team': 1, 'game_nickname': 'Player5', 'kills': 10, 'deaths': 12, 'assists': 11, 'is_mvp': 0, 'rating_change': 25},
                {'user_id': 6, 'team': 2, 'game_nickname': 'Enemy1', 'kills': 16, 'deaths': 15, 'assists': 5, 'is_mvp': 0, 'rating_change': -20},
                {'user_id': 7, 'team': 2, 'game_nickname': 'Enemy2', 'kills': 14, 'deaths': 16, 'assists': 4, 'is_mvp': 0, 'rating_change': -20},
                {'user_id': 8, 'team': 2, 'game_nickname': 'Enemy3', 'kills': 13, 'deaths': 17, 'assists': 6, 'is_mvp': 0, 'rating_change': -20},
                {'user_id': 9, 'team': 2, 'game_nickname': 'Enemy4', 'kills': 15, 'deaths': 14, 'assists': 3, 'is_mvp': 0, 'rating_change': -20},
                {'user_id': 10, 'team': 2, 'game_nickname': 'Enemy5', 'kills': 12, 'deaths': 15, 'assists': 8, 'is_mvp': 0, 'rating_change': -20}
            ]
        },
        2: {
            'match_id': 2,
            'map_name': '🏢 Hanami',
            'team1_score': 8,
            'team2_score': 13,
            'team1_start_side': '🔵 Защита (CT)',
            'team2_start_side': '🔴 Атака (T)',
            'winner_team': 2,
            'status': 'finished',
            'finished_at': '2026-03-15T20:15:00',
            'players': [
                {'user_id': 123456789, 'team': 1, 'game_nickname': 'TestPlayer', 'kills': 14, 'deaths': 18, 'assists': 5, 'is_mvp': 0, 'rating_change': -20},
                {'user_id': 2, 'team': 1, 'game_nickname': 'Player2', 'kills': 12, 'deaths': 17, 'assists': 4, 'is_mvp': 0, 'rating_change': -20},
                {'user_id': 3, 'team': 1, 'game_nickname': 'Player3', 'kills': 10, 'deaths': 16, 'assists': 6, 'is_mvp': 0, 'rating_change': -20},
                {'user_id': 4, 'team': 1, 'game_nickname': 'Player4', 'kills': 11, 'deaths': 15, 'assists': 3, 'is_mvp': 0, 'rating_change': -20},
                {'user_id': 5, 'team': 1, 'game_nickname': 'Player5', 'kills': 9, 'deaths': 14, 'assists': 7, 'is_mvp': 0, 'rating_change': -20},
                {'user_id': 6, 'team': 2, 'game_nickname': 'Enemy1', 'kills': 20, 'deaths': 11, 'assists': 8, 'is_mvp': 1, 'rating_change': 30},
                {'user_id': 7, 'team': 2, 'game_nickname': 'Enemy2', 'kills': 18, 'deaths': 12, 'assists': 5, 'is_mvp': 0, 'rating_change': 25},
                {'user_id': 8, 'team': 2, 'game_nickname': 'Enemy3', 'kills': 16, 'deaths': 10, 'assists': 6, 'is_mvp': 0, 'rating_change': 25},
                {'user_id': 9, 'team': 2, 'game_nickname': 'Enemy4', 'kills': 14, 'deaths': 12, 'assists': 9, 'is_mvp': 0, 'rating_change': 25},
                {'user_id': 10, 'team': 2, 'game_nickname': 'Enemy5', 'kills': 12, 'deaths': 11, 'assists': 7, 'is_mvp': 0, 'rating_change': 25}
            ]
        },
        3: {
            'match_id': 3,
            'map_name': '🌊 Breeze',
            'team1_score': 13,
            'team2_score': 11,
            'team1_start_side': '🔴 Атака (T)',
            'team2_start_side': '🔵 Защита (CT)',
            'winner_team': 1,
            'status': 'finished',
            'finished_at': '2026-03-14T19:00:00',
            'players': [
                {'user_id': 123456789, 'team': 2, 'game_nickname': 'TestPlayer', 'kills': 18, 'deaths': 16, 'assists': 7, 'is_mvp': 0, 'rating_change': -20},
                {'user_id': 2, 'team': 2, 'game_nickname': 'Player2', 'kills': 16, 'deaths': 15, 'assists': 5, 'is_mvp': 0, 'rating_change': -20},
                {'user_id': 3, 'team': 2, 'game_nickname': 'Player3', 'kills': 14, 'deaths': 14, 'assists': 8, 'is_mvp': 0, 'rating_change': -20},
                {'user_id': 4, 'team': 2, 'game_nickname': 'Player4', 'kills': 13, 'deaths': 16, 'assists': 4, 'is_mvp': 0, 'rating_change': -20},
                {'user_id': 5, 'team': 2, 'game_nickname': 'Player5', 'kills': 11, 'deaths': 15, 'assists': 6, 'is_mvp': 0, 'rating_change': -20},
                {'user_id': 6, 'team': 1, 'game_nickname': 'Enemy1', 'kills': 19, 'deaths': 14, 'assists': 6, 'is_mvp': 1, 'rating_change': 30},
                {'user_id': 7, 'team': 1, 'game_nickname': 'Enemy2', 'kills': 17, 'deaths': 15, 'assists': 5, 'is_mvp': 0, 'rating_change': 25},
                {'user_id': 8, 'team': 1, 'game_nickname': 'Enemy3', 'kills': 15, 'deaths': 14, 'assists': 7, 'is_mvp': 0, 'rating_change': 25},
                {'user_id': 9, 'team': 1, 'game_nickname': 'Enemy4', 'kills': 13, 'deaths': 15, 'assists': 4, 'is_mvp': 0, 'rating_change': 25},
                {'user_id': 10, 'team': 1, 'game_nickname': 'Enemy5', 'kills': 12, 'deaths': 14, 'assists': 8, 'is_mvp': 0, 'rating_change': 25}
            ]
        },
        4: {
            'match_id': 4,
            'map_name': '🏭 Zone7',
            'team1_score': 13,
            'team2_score': 7,
            'team1_start_side': '🔵 Защита (CT)',
            'team2_start_side': '🔴 Атака (T)',
            'winner_team': 1,
            'status': 'finished',
            'finished_at': '2026-03-13T21:45:00',
            'players': [
                {'user_id': 123456789, 'team': 1, 'game_nickname': 'TestPlayer', 'kills': 25, 'deaths': 10, 'assists': 12, 'is_mvp': 1, 'rating_change': 35},
                {'user_id': 2, 'team': 1, 'game_nickname': 'Player2', 'kills': 20, 'deaths': 9, 'assists': 8, 'is_mvp': 0, 'rating_change': 25},
                {'user_id': 3, 'team': 1, 'game_nickname': 'Player3', 'kills': 18, 'deaths': 11, 'assists': 6, 'is_mvp': 0, 'rating_change': 25},
                {'user_id': 4, 'team': 1, 'game_nickname': 'Player4', 'kills': 15, 'deaths': 10, 'assists': 9, 'is_mvp': 0, 'rating_change': 25},
                {'user_id': 5, 'team': 1, 'game_nickname': 'Player5', 'kills': 12, 'deaths': 8, 'assists': 7, 'is_mvp': 0, 'rating_change': 25},
                {'user_id': 6, 'team': 2, 'game_nickname': 'Enemy1', 'kills': 12, 'deaths': 18, 'assists': 4, 'is_mvp': 0, 'rating_change': -20},
                {'user_id': 7, 'team': 2, 'game_nickname': 'Enemy2', 'kills': 10, 'deaths': 19, 'assists': 3, 'is_mvp': 0, 'rating_change': -20},
                {'user_id': 8, 'team': 2, 'game_nickname': 'Enemy3', 'kills': 9, 'deaths': 17, 'assists': 5, 'is_mvp': 0, 'rating_change': -20},
                {'user_id': 9, 'team': 2, 'game_nickname': 'Enemy4', 'kills': 8, 'deaths': 18, 'assists': 6, 'is_mvp': 0, 'rating_change': -20},
                {'user_id': 10, 'team': 2, 'game_nickname': 'Enemy5', 'kills': 9, 'deaths': 18, 'assists': 4, 'is_mvp': 0, 'rating_change': -20}
            ]
        }
    }
    return matches.get(match_id)


# ========== TICKETS (Support Chat) API ==========

@routes.get('/api/tickets')
async def get_tickets(request: web.Request):
    """Получить тикеты пользователя"""
    user_id = get_user_id_from_request(request)
    if not user_id:
        return web.json_response({'error': 'Unauthorized'}, status=401)
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        query = """
            SELECT t.*, u.username as admin_username, u.full_name as admin_name
            FROM tickets t
            LEFT JOIN users u ON t.responded_by = u.user_id
            WHERE t.user_id = ?
            ORDER BY t.created_at DESC
        """
        async with db.execute(query, (user_id,)) as cursor:
            tickets = [dict(row) for row in await cursor.fetchall()]
        
        # Если нет тикетов и тестовый режим - возвращаем мок-данные
        if not tickets and TEST_MODE:
            return web.json_response({'tickets': get_mock_tickets()})
        
        return web.json_response({'tickets': tickets})


def get_mock_tickets():
    """Мок-данные тикетов для тестирования"""
    return [
        {
            'ticket_id': 1,
            'ticket_type': 'question',
            'message': 'Как посмотреть историю всех своих матчей?',
            'status': 'answered',
            'admin_response': 'Вы можете посмотреть историю матчей в приложении (кнопка "📱 Приложение" в главном меню) или с помощью команды /history',
            'admin_name': 'Admin',
            'created_at': '2026-03-15T14:30:00'
        },
        {
            'ticket_id': 2,
            'ticket_type': 'bug',
            'message': 'Иногда кнопка "Готов" не срабатывает с первого раза',
            'status': 'open',
            'admin_response': None,
            'admin_name': None,
            'created_at': '2026-03-16T10:15:00'
        }
    ]


@routes.get('/api/ticket/{ticket_id}')
async def get_ticket(request: web.Request):
    """Получить детали тикета"""
    user_id = get_user_id_from_request(request)
    if not user_id:
        return web.json_response({'error': 'Unauthorized'}, status=401)
    
    ticket_id = int(request.match_info['ticket_id'])
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        async with db.execute(
            """SELECT t.*, u.username as admin_username, u.full_name as admin_name
               FROM tickets t
               LEFT JOIN users u ON t.responded_by = u.user_id
               WHERE t.ticket_id = ? AND t.user_id = ?""",
            (ticket_id, user_id)
        ) as cursor:
            ticket = await cursor.fetchone()
            if not ticket:
                return web.json_response({'error': 'Ticket not found'}, status=404)
            return web.json_response(dict(ticket))


@routes.post('/api/tickets')
async def create_ticket(request: web.Request):
    """Создать новый тикет"""
    user_id = get_user_id_from_request(request)
    if not user_id:
        return web.json_response({'error': 'Unauthorized'}, status=401)
    
    try:
        data = await request.json()
    except:
        return web.json_response({'error': 'Invalid JSON'}, status=400)
    
    ticket_type = data.get('type', 'question')
    message = data.get('message', '').strip()
    
    if len(message) < 10:
        return web.json_response({'error': 'Message too short'}, status=400)
    
    if len(message) > 2000:
        return web.json_response({'error': 'Message too long'}, status=400)
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            """INSERT INTO tickets (user_id, ticket_type, message, status)
               VALUES (?, ?, ?, 'open')""",
            (user_id, ticket_type, message)
        )
        ticket_id = cursor.lastrowid
        await db.commit()
        
        return web.json_response({
            'ticket_id': ticket_id,
            'status': 'created'
        })


# ========== STATIC FILES ==========

import os

# Определяем базовый путь к webapp
WEBAPP_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(WEBAPP_DIR, 'static')


@routes.get('/')
async def index(request: web.Request):
    """Главная страница Mini App"""
    return web.FileResponse(os.path.join(STATIC_DIR, 'index.html'))


@routes.get('/matches')
async def matches_page(request: web.Request):
    """Страница истории матчей"""
    return web.FileResponse(os.path.join(STATIC_DIR, 'index.html'))


@routes.get('/support')
async def support_page(request: web.Request):
    """Страница поддержки"""
    return web.FileResponse(os.path.join(STATIC_DIR, 'index.html'))


def create_app(bot_token: str, db_path: str = "database.db", test_mode: bool = False) -> web.Application:
    """Создать приложение"""
    global BOT_TOKEN, DATABASE_PATH, TEST_MODE
    BOT_TOKEN = bot_token
    DATABASE_PATH = db_path
    TEST_MODE = test_mode or (bot_token == "test_token")
    
    if TEST_MODE:
        logger.info("🧪 Running in TEST MODE - authentication disabled")
    
    app = web.Application()
    app.add_routes(routes)
    app.router.add_static('/static', STATIC_DIR)
    
    return app


def create_ssl_context(cert_path: str, key_path: str) -> ssl.SSLContext:
    """Создать SSL контекст"""
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_context.load_cert_chain(cert_path, key_path)
    return ssl_context


async def run_webapp(bot_token: str, host: str = "0.0.0.0", port: int = 443,
                     cert_path: str = None, key_path: str = None,
                     db_path: str = "database.db"):
    """Запустить веб-приложение"""
    app = create_app(bot_token, db_path)
    
    ssl_context = None
    if cert_path and key_path:
        ssl_context = create_ssl_context(cert_path, key_path)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    site = web.TCPSite(runner, host, port, ssl_context=ssl_context)
    await site.start()
    
    logger.info(f"Mini App server started on {'https' if ssl_context else 'http'}://{host}:{port}")
    
    return runner