#!/usr/bin/env python3
"""
Скрипт для запуска Mini App сервера отдельно от бота.
Используется для тестирования в браузере.

Запуск:
    python run_webapp.py

По умолчанию запускается на http://localhost:8080
"""

import asyncio
import argparse
import logging
from aiohttp import web

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    parser = argparse.ArgumentParser(description='Run 3FACE Mini App server')
    parser.add_argument('--host', default='127.0.0.1', help='Host to bind (default: 127.0.0.1)')
    parser.add_argument('--port', type=int, default=8080, help='Port to bind (default: 8080)')
    parser.add_argument('--ssl', action='store_true', help='Enable SSL (requires certs)')
    parser.add_argument('--test', action='store_true', help='Enable test mode (no auth required)')
    args = parser.parse_args()
    
    # Импортируем после парсинга аргументов
    from webapp.server import create_app, create_ssl_context
    from config import BOT_TOKEN, SSL_CERT_PATH, SSL_KEY_PATH, DATABASE_PATH
    
    # Определяем тестовый режим
    is_test_mode = args.test or not BOT_TOKEN or BOT_TOKEN == "test_token" or BOT_TOKEN == "your_bot_token_here"
    
    if args.test:
        logger.info("🧪 Test mode enabled via --test flag")
    
    # Создаём приложение с тестовым режимом
    app = create_app(
        bot_token=BOT_TOKEN or "test_token",
        db_path=DATABASE_PATH,
        test_mode=is_test_mode
    )
    
    # SSL контекст если нужен
    ssl_context = None
    if args.ssl:
        try:
            ssl_context = create_ssl_context(SSL_CERT_PATH, SSL_KEY_PATH)
            logger.info("SSL enabled")
        except Exception as e:
            logger.warning(f"SSL not available: {e}")
    
    # Запускаем сервер
    runner = web.AppRunner(app)
    await runner.setup()
    
    site = web.TCPSite(runner, args.host, args.port, ssl_context=ssl_context)
    await site.start()
    
    protocol = "https" if ssl_context else "http"
    logger.info(f"")
    logger.info(f"🚀 Mini App server started!")
    logger.info(f"")
    logger.info(f"   Open in browser: {protocol}://{args.host}:{args.port}")
    logger.info(f"")
    logger.info(f"   Press Ctrl+C to stop")
    logger.info(f"")
    
    # Ждём бесконечно
    try:
        while True:
            await asyncio.sleep(3600)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())