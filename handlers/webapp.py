"""
Обработчики для команды /lobby и WebApp интеграции
"""

from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
import logging

import database as db
from utils import format_match_info, format_player_name
from config import EMOJI

router = Router()
logger = logging.getLogger(__name__)


@router.message(Command("lobby"))
async def cmd_lobby(message: Message):
    """
    Команда /lobby - показывает пример игрового лобби.
    Используется для демонстрации того, как выглядит состав команд.
    """
    user = await db.get_user(message.from_user.id)
    if not user:
        await message.answer(
            f"{EMOJI['warning']} Сначала зарегистрируйтесь командой /start"
        )
        return
    
    # Проверяем, есть ли у пользователя активный матч
    active_match = await db.get_user_active_match(message.from_user.id)
    
    if active_match:
        # Показываем реальный активный матч
        team1 = await db.get_match_players(active_match['match_id'], team=1)
        team2 = await db.get_match_players(active_match['match_id'], team=2)
        
        await message.answer(
            f"{EMOJI['sword']} *ВАШ АКТИВНЫЙ МАТЧ*\n" +
            format_match_info(active_match, team1, team2),
            parse_mode="Markdown"
        )
    else:
        # Показываем демо-лобби
        demo_text = generate_demo_lobby()
        await message.answer(demo_text, parse_mode="HTML")


def generate_demo_lobby() -> str:
    """Генерирует демонстрационное лобби"""
    
    demo_lobby = f"""
{EMOJI['sword']} <b>ДЕМО: ИГРОВОЕ ЛОББИ</b>
━━━━━━━━━━━━━━━━━━━━

{EMOJI['green']} Статус: <b>ACTIVE</b>
{EMOJI['map']} Карта: <b>🏜️ Sandstone</b>

🎖️ <b>ХОСТЕР:</b> @pro_player
🆔 <b>ID хостера:</b> <code>123456789</code>

{EMOJI['red']} <b>КОМАНДА 1</b> (Avg: 1250)
Сторона: 🔴 Атака (T)
  • @player_1 [1350] 🎖️
  • @player_2 [1280]
  • @player_3 [1200]
  • @player_4 [1180]
  • @player_5 [1240]

{EMOJI['blue']} <b>КОМАНДА 2</b> (Avg: 1230)
Сторона: 🔵 Защита (CT)
  • @player_6 [1300]
  • @player_7 [1250]
  • @player_8 [1200]
  • @player_9 [1180]
  • @player_10 [1220]

━━━━━━━━━━━━━━━━━━━━

{EMOJI['info']} <b>Примечание:</b> Стороны меняются после 12 раунда!

━━━━━━━━━━━━━━━━━━━━
{EMOJI['target']} <b>Это демонстрация игрового лобби.</b>
Для участия в реальном матче используйте кнопку «Найти игру»!
"""
    return demo_lobby


@router.message(Command("match"))
async def cmd_match(message: Message):
    """
    Команда /match <id> - показывает информацию о матче по ID
    """
    user = await db.get_user(message.from_user.id)
    if not user:
        await message.answer(
            f"{EMOJI['warning']} Сначала зарегистрируйтесь командой /start"
        )
        return
    
    # Парсим ID матча
    args = message.text.split()
    if len(args) < 2:
        # Показываем активный матч пользователя если есть
        active_match = await db.get_user_active_match(message.from_user.id)
        if active_match:
            team1 = await db.get_match_players(active_match['match_id'], team=1)
            team2 = await db.get_match_players(active_match['match_id'], team=2)
            
            await message.answer(
                format_match_info(active_match, team1, team2),
                parse_mode="Markdown"
            )
        else:
            await message.answer(
                f"{EMOJI['info']} Использование: /match <ID матча>\n\n"
                f"Пример: `/match 123`\n\n"
                f"У вас нет активного матча.",
                parse_mode="Markdown"
            )
        return
    
    try:
        match_id = int(args[1])
    except ValueError:
        await message.answer(
            f"{EMOJI['warning']} Неверный формат ID матча!"
        )
        return
    
    # Получаем матч
    match = await db.get_match(match_id)
    if not match:
        await message.answer(
            f"{EMOJI['warning']} Матч #{match_id} не найден!"
        )
        return
    
    team1 = await db.get_match_players(match_id, team=1)
    team2 = await db.get_match_players(match_id, team=2)
    
    if match['status'] == 'finished':
        from utils import format_match_result
        await message.answer(
            format_match_result(match, team1, team2),
            parse_mode="Markdown"
        )
    else:
        await message.answer(
            format_match_info(match, team1, team2),
            parse_mode="Markdown"
        )


@router.message(Command("history"))
async def cmd_history(message: Message):
    """
    Команда /history - показывает последние матчи пользователя
    """
    user = await db.get_user(message.from_user.id)
    if not user:
        await message.answer(
            f"{EMOJI['warning']} Сначала зарегистрируйтесь командой /start"
        )
        return
    
    # Получаем историю матчей
    history = await db.get_user_match_history(message.from_user.id, limit=5)
    
    if not history:
        await message.answer(
            f"{EMOJI['info']} У вас пока нет завершённых матчей.\n\n"
            f"Начните играть с помощью кнопки «Найти игру»!"
        )
        return
    
    from utils import format_history_entry
    
    text = f"{EMOJI['chart']} *ИСТОРИЯ МАТЧЕЙ*\n━━━━━━━━━━━━━━━━━━━━\n"
    
    for match in history:
        text += format_history_entry(match, match['team'])
    
    text += f"\n━━━━━━━━━━━━━━━━━━━━\n"
    text += f"{EMOJI['info']} Используйте приложение для полной истории!"
    
    await message.answer(text, parse_mode="Markdown")