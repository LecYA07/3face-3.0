"""
Модуль автопроверки результатов матчей через нейросеть
"""

import json
import logging
import base64
from typing import Optional, Dict, Any, List
from openai import AsyncOpenAI
from config import OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL

logger = logging.getLogger(__name__)

# Инициализация клиента OpenAI
client = AsyncOpenAI(
    base_url=OPENAI_BASE_URL,
    api_key=OPENAI_API_KEY,
) if OPENAI_API_KEY else None


def format_players_for_prompt(team1_players: List[Dict], team2_players: List[Dict], 
                               team1_side: str, team2_side: str) -> str:
    """Форматирование информации об игроках для промпта"""
    
    team1_info = []
    for p in team1_players:
        nickname = p.get('game_nickname') or p.get('username') or f"Player_{p['user_id']}"
        team1_info.append(f"  - {nickname} (ID: {p['user_id']})")
    
    team2_info = []
    for p in team2_players:
        nickname = p.get('game_nickname') or p.get('username') or f"Player_{p['user_id']}"
        team2_info.append(f"  - {nickname} (ID: {p['user_id']})")
    
    return f"""
КОМАНДА 1 (стартовая сторона: {team1_side}):
{chr(10).join(team1_info)}

КОМАНДА 2 (стартовая сторона: {team2_side}):
{chr(10).join(team2_info)}
"""


SYSTEM_PROMPT = """Ты - система анализа результатов матчей в игре Standoff 2.
Твоя задача - проанализировать скриншот и определить, является ли он валидным результатом матча.

ПЕРВЫМ ДЕЛОМ ОПРЕДЕЛИ:
- Это скриншот из игры Standoff 2?
- Это экран результатов матча (таблица с игроками, счётом, статистикой)?
- Или это что-то другое (меню, лобби, чат, рандомная картинка, мем, другая игра)?

ПРИЗНАКИ ВАЛИДНОГО СКРИНШОТА РЕЗУЛЬТАТОВ МАТЧА В STANDOFF 2:
1. Таблица с двумя командами (по 5 игроков в каждой для 5x5, по 2 для 2x2)
2. Счёт матча виден (например 13:7, 16:14)
3. У каждого игрока видна статистика K/A/D (убийства/ассисты/смерти) - ВАЖНО: в Standoff 2 формат KAD, не KDA!

НЕВАЛИДНЫЕ СКРИНШОТЫ:
- Рандомные картинки, не связанные с игрой
- Скриншоты из других игр
- Меню игры, лобби, магазин
- Чат, переписки
- Скриншот во время матча (не финальный экран)
- Пустой экран или ошибки

ВАЖНО ПО ИГРЕ И СМЕНЕ СТОРОН:
1. В начале матча команды стартуют на определённых сторонах (Атака/Защита)
2. После 12 раунда (когда одна из команд набирает 12 раундов или суммарно сыграно 12 раундов) КОМАНДЫ МЕНЯЮТСЯ СТОРОНАМИ!
3. Это означает: если Команда 1 начинала за Атаку, то после 12 раунда она играет за Защиту
4. На ФИНАЛЬНОМ экране результатов команды отображаются по их ТЕКУЩЕЙ (конечной) стороне, а не по стартовой!
5. Матч играется до 13 побед (максимальный счёт 13:X или в овертайме больше)
6. На скриншоте видны ники игроков и их статистика в формате K/A/D (убийства/ассисты/смерти)

КРИТИЧЕСКИ ВАЖНО ПО ОПРЕДЕЛЕНИЮ КОМАНД:
- Тебе даны СТАРТОВЫЕ стороны команд (team1_start_side и team2_start_side)
- Если матч длился более 12 раундов (сумма счёта > 12), то на скриншоте команды отображаются на ПРОТИВОПОЛОЖНЫХ сторонах!
- Пример: Команда 1 начинала за Атаку, счёт 13:10 (всего 23 раунда > 12) → на скриншоте Команда 1 будет на стороне Защиты
- При сопоставлении игроков УЧИТЫВАЙ эту смену сторон!

ОПРЕДЕЛЕНИЕ MVP:
В Standoff 2 НЕТ отметки MVP на экране результатов! Ты должен САМОСТОЯТЕЛЬНО определить MVP по статистике.
MVP - это игрок, который принёс наибольший импакт своей команде. Определяется по формуле: kills + assists.
Игрок с наибольшим значением (kills + assists) среди ПОБЕДИВШЕЙ команды становится MVP.
Если счёт ничейный - MVP не определяется (оставь null).

АЛГОРИТМ СОПОСТАВЛЕНИЯ КОМАНД:
1. Посмотри на финальный счёт: team1_score : team2_score
2. Если сумма счёта (team1_score + team2_score) > 12, значит была смена сторон
3. Если смена сторон БЫЛА:
   - Команда, которая начинала за Атаку, на финальном экране будет на стороне Защиты
   - Команда, которая начинала за Защиту, на финальном экране будет на стороне Атаки
4. Если смены сторон НЕ БЫЛО (сумма <= 12):
   - Команды остаются на своих стартовых сторонах
5. Сопоставляй игроков с учётом этой логики!

КРИТИЧЕСКИ ВАЖНО ПО ФОРМАТУ СТАТИСТИКИ:
В Standoff 2 статистика отображается в формате K/A/D (KAD), а НЕ K/D/A (KDA):
- Первое число = Kills (убийства)
- Второе число = Assists (ассисты) 
- Третье число = Deaths (смерти)
Например: 15/3/8 означает 15 убийств, 3 ассиста, 8 смертей.
При заполнении JSON поля deaths и assists - учитывай этот порядок!

Ты должен вернуть ТОЛЬКО валидный JSON без дополнительного текста в формате:
{
    "is_valid_screenshot": true/false,
    "screenshot_type": "match_result" | "invalid" | "other_game" | "random_image" | "game_menu" | "in_match",
    "rejection_reason": "причина отклонения если is_valid_screenshot=false" или null,
    "success": true/false,
    "confidence": 0.0-1.0,
    "team1_score": число или null,
    "team2_score": число или null,
    "winner_team": 1 или 2 или null,
    "mvp_user_id": ID игрока MVP или null,
    "players_stats": [
        {
            "user_id": ID игрока,
            "nickname_on_screenshot": "ник как на скриншоте",
            "kills": число,
            "deaths": число,
            "assists": число,
            "is_mvp": true/false
        }
    ],
    "error_message": "сообщение об ошибке если success=false"
}

ЛОГИКА:
1. Если is_valid_screenshot=false, то success тоже должен быть false
2. rejection_reason должен быть понятным для администратора (на русском языке)
3. Поле confidence показывает уверенность в результате (0.0 - не уверен, 1.0 - полностью уверен)
4. Если скриншот невалидный - confidence должен быть 0

Примеры rejection_reason:
- "Это не скриншот из Standoff 2"
- "Скриншот не содержит результатов матча"
- "Это скриншот из другой игры"
- "Изображение не связано с игрой"
- "Скриншот сделан во время матча, а не после его завершения"
- "Не удалось распознать экран результатов"
"""


async def analyze_match_screenshot(
    image_base64: str,
    team1_players: List[Dict],
    team2_players: List[Dict],
    team1_side: str,
    team2_side: str,
    map_name: str
) -> Dict[str, Any]:
    """
    Анализ скриншота матча с помощью нейросети
    
    Args:
        image_base64: Изображение в base64
        team1_players: Список игроков команды 1
        team2_players: Список игроков команды 2
        team1_side: Стартовая сторона команды 1 (Атака/Защита)
        team2_side: Стартовая сторона команды 2
        map_name: Название карты
        
    Returns:
        Dict с результатами анализа
    """
    
    if not client:
        logger.error("OpenAI client not initialized - API key missing")
        return {
            "success": False,
            "error_message": "API ключ не настроен",
            "confidence": 0
        }
    
    players_info = format_players_for_prompt(team1_players, team2_players, team1_side, team2_side)
    
    user_prompt = f"""Проанализируй скриншот результатов матча на карте {map_name}.

Данные матча:
{players_info}

Найди на скриншоте:
1. Финальный счёт (команда 1 : команда 2)
2. Какая команда победила
3. Статистику каждого игрока (K/A/D - убийства/ассисты/смерти, именно в таком порядке в Standoff 2!)
4. Определи MVP матча самостоятельно: игрок из ПОБЕДИВШЕЙ команды с наибольшим (kills + assists)

Сопоставь ники на скриншоте с игроками из списка выше.
Верни результат в JSON формате."""

    try:
        response = await client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": user_prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=2000,
            temperature=0.1  # Низкая температура для более точных результатов
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # Пытаемся извлечь JSON из ответа
        # Иногда модель оборачивает JSON в ```json ... ```
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0].strip()
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0].strip()
        
        result = json.loads(result_text)
        
        # Устанавливаем значения по умолчанию для параметров, которые не были найдены
        result.setdefault('is_valid_screenshot', True)
        result.setdefault('screenshot_type', 'match_result')
        result.setdefault('rejection_reason', None)
        result.setdefault('success', False)
        result.setdefault('confidence', 0)
        result.setdefault('team1_score', 0)
        result.setdefault('team2_score', 0)
        result.setdefault('winner_team', None)
        result.setdefault('mvp_user_id', None)
        result.setdefault('players_stats', [])
        result.setdefault('error_message', None)
        
        # Обрабатываем статистику игроков - устанавливаем 0 для отсутствующих значений
        if result.get('players_stats'):
            for player_stat in result['players_stats']:
                player_stat.setdefault('user_id', None)
                player_stat.setdefault('nickname_on_screenshot', 'Unknown')
                player_stat.setdefault('kills', 0)
                player_stat.setdefault('deaths', 0)
                player_stat.setdefault('assists', 0)
                player_stat.setdefault('is_mvp', False)
        
        # Если MVP не определён нейронкой, определяем по статистике (kills + assists)
        if result.get('players_stats') and not result.get('mvp_user_id'):
            # Проверяем, есть ли уже отмеченный MVP
            has_mvp_marked = any(ps.get('is_mvp') for ps in result['players_stats'])
            
            if not has_mvp_marked:
                # Находим игрока с лучшей статистикой (kills + assists)
                best_player = None
                best_score = -1
                
                for player_stat in result['players_stats']:
                    kills = player_stat.get('kills', 0) or 0
                    assists = player_stat.get('assists', 0) or 0
                    score = kills + assists
                    
                    if score > best_score:
                        best_score = score
                        best_player = player_stat
                
                # Отмечаем лучшего игрока как MVP
                if best_player and best_player.get('user_id'):
                    best_player['is_mvp'] = True
                    result['mvp_user_id'] = best_player['user_id']
                    logger.info(f"MVP auto-determined by stats: user_id={best_player['user_id']}, score={best_score} (kills+assists)")
        
        logger.info(f"AI analysis result: success={result.get('success')}, confidence={result.get('confidence')}")
        
        return result
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse AI response as JSON: {e}")
        return {
            "success": False,
            "error_message": f"Ошибка парсинга ответа AI: {str(e)}",
            "confidence": 0,
            "raw_response": result_text if 'result_text' in locals() else None
        }
    except Exception as e:
        logger.error(f"AI analysis error: {e}")
        return {
            "success": False,
            "error_message": f"Ошибка AI: {str(e)}",
            "confidence": 0
        }


async def download_and_encode_photo(bot, file_id: str) -> Optional[str]:
    """
    Скачать фото из Telegram и конвертировать в base64
    
    Args:
        bot: Экземпляр бота
        file_id: ID файла в Telegram
        
    Returns:
        Base64 строка или None при ошибке
    """
    try:
        # Получаем информацию о файле
        file = await bot.get_file(file_id)
        
        # В aiogram 3.x download_file возвращает BytesIO
        file_data = await bot.download_file(file.file_path)
        
        # Читаем данные в bytes
        # file_data уже является BytesIO объектом
        if hasattr(file_data, 'read'):
            image_bytes = file_data.read()
        elif hasattr(file_data, 'getvalue'):
            image_bytes = file_data.getvalue()
        else:
            # Если это уже bytes
            image_bytes = file_data
        
        # Конвертируем в base64
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        
        logger.info(f"Successfully downloaded and encoded photo: {len(image_bytes)} bytes")
        return image_base64
        
    except Exception as e:
        logger.error(f"Failed to download and encode photo: {e}", exc_info=True)
        return None


def format_ai_result_for_admin(ai_result: Dict[str, Any], match_info: Dict, 
                                team1_players: List[Dict], team2_players: List[Dict]) -> str:
    """
    Форматирование результата AI анализа для отправки администратору
    """
    from utils import escape_markdown
    
    # Создаём словарь для быстрого поиска игроков по user_id
    all_players = team1_players + team2_players
    players_by_id = {p['user_id']: p for p in all_players}
    
    def format_player_link(player: Dict) -> str:
        """Форматировать ссылку на игрока"""
        username = player.get('username')
        game_nickname = player.get('game_nickname')
        full_name = player.get('full_name', 'Игрок')
        user_id = player.get('user_id')
        
        display_name = escape_markdown(game_nickname or full_name)
        
        if username:
            return f"[{display_name}](https://t.me/{username})"
        elif user_id:
            return f"[{display_name}](tg://user?id={user_id})"
        return display_name
    
    # Проверяем, является ли скриншот невалидным
    if ai_result.get('is_valid_screenshot') == False:
        screenshot_type = ai_result.get('screenshot_type', 'invalid')
        type_descriptions = {
            'invalid': '❓ Невалидное изображение',
            'other_game': '🎮 Скриншот из другой игры',
            'random_image': '🖼️ Случайное изображение',
            'game_menu': '📋 Меню игры (не результат)',
            'in_match': '⏳ Скриншот во время матча'
        }
        type_text = type_descriptions.get(screenshot_type, '❓ Неизвестный тип')
        rejection_reason = ai_result.get('rejection_reason', 'Скриншот не является результатом матча')
        
        return (
            "🤖 *AI АНАЛИЗ: НЕВАЛИДНЫЙ СКРИНШОТ*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🚫 *Тип изображения:* {type_text}\n\n"
            f"📝 *Причина отклонения:*\n{rejection_reason}\n\n"
            f"⚠️ *Рекомендация:* Отклонить заявку и запросить корректный скриншот результатов матча.\n\n"
            f"Вы можете:\n"
            f"• ❌ Отклонить заявку\n"
            f"• ⚙️ Провести ручную проверку (если считаете AI неправым)"
        )
    
    if not ai_result.get('success'):
        error_msg = ai_result.get('error_message', 'Неизвестная ошибка')
        return (
            "🤖 *AI АНАЛИЗ НЕ УДАЛСЯ*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"❌ Причина: {error_msg}\n\n"
            f"Требуется ручная проверка результатов."
        )
    
    confidence_emoji = "🟢" if ai_result.get('confidence', 0) >= 0.8 else "🟡" if ai_result.get('confidence', 0) >= 0.5 else "🔴"
    confidence_percent = int(ai_result.get('confidence', 0) * 100)
    
    team1_score = ai_result.get('team1_score', '?')
    team2_score = ai_result.get('team2_score', '?')
    winner_team = ai_result.get('winner_team')
    winner_text = f"Команда {winner_team}" if winner_team else "Не определён"
    
    # Формируем статистику игроков с ссылками на профили
    players_stats_text = ""
    if ai_result.get('players_stats'):
        players_stats_text = "\n\n📊 *Статистика игроков:*\n"
        for ps in ai_result['players_stats']:
            mvp_mark = " ⭐" if ps.get('is_mvp') else ""
            nickname_on_screenshot = ps.get('nickname_on_screenshot', 'Unknown')
            kills = ps.get('kills', 0)
            deaths = ps.get('deaths', 0)
            assists = ps.get('assists', 0)
            
            # Пытаемся найти игрока по user_id и сделать ссылку
            # Выводим в формате K/A/D как в Standoff 2
            user_id = ps.get('user_id')
            if user_id and user_id in players_by_id:
                player = players_by_id[user_id]
                player_link = format_player_link(player)
                players_stats_text += f"  • {player_link}: {kills}/{assists}/{deaths}{mvp_mark}\n"
            else:
                # Если не нашли игрока, показываем просто ник со скриншота
                safe_nickname = escape_markdown(nickname_on_screenshot)
                players_stats_text += f"  • {safe_nickname}: {kills}/{assists}/{deaths}{mvp_mark}\n"
    
    mvp_text = "Не определён"
    if ai_result.get('mvp_user_id'):
        # Ищем игрока по ID и делаем ссылку
        mvp_user_id = ai_result['mvp_user_id']
        if mvp_user_id in players_by_id:
            mvp_player = players_by_id[mvp_user_id]
            mvp_text = format_player_link(mvp_player)
        else:
            mvp_text = f"ID: {mvp_user_id}"
    
    return (
        f"🤖 *РЕЗУЛЬТАТ AI АНАЛИЗА*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{confidence_emoji} Уверенность: *{confidence_percent}%*\n\n"
        f"🗺️ Карта: *{match_info.get('map_name', 'Неизвестно')}*\n"
        f"🏆 Счёт: *{team1_score} : {team2_score}*\n"
        f"👑 Победитель: *{winner_text}*\n"
        f"⭐ MVP: {mvp_text}"
        f"{players_stats_text}\n\n"
        f"⚠️ *Проверьте результаты и подтвердите или отредактируйте*"
    )


def is_valid_match_screenshot(ai_result: Dict[str, Any]) -> bool:
    """Проверить, является ли скриншот валидным результатом матча"""
    return ai_result.get('is_valid_screenshot', True) and ai_result.get('success', False)
