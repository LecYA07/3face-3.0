import random
import re
from typing import List, Dict, Any, Tuple
from config import (
    EMOJI, SIDES, MAPS, BASE_RATING_WIN, BASE_RATING_LOSE, 
    RATING_MVP_BONUS, RATING_DIFF_MULTIPLIER, MAX_PARTY_SIZE
)


def escape_markdown(text: str) -> str:
    """
    Экранировать спецсимволы Markdown для безопасного отображения.
    Для Markdown (не MarkdownV2) экранируем: _ * [ ] ( ) ~
    """
    if not text:
        return text
    # Экранируем основные спецсимволы Markdown
    escape_chars = ['_', '*', '[', ']', '`']
    for char in escape_chars:
        text = text.replace(char, '\\' + char)
    return text


def calculate_team_rating(players: List[Dict[str, Any]]) -> int:
    """Рассчитать средний рейтинг команды"""
    if not players:
        return 0
    total_rating = sum(player.get('rating', 1000) for player in players)
    return total_rating // len(players)


def calculate_rating_change(winner_team_rating: int, loser_team_rating: int, 
                           is_winner: bool, is_mvp: bool = False) -> int:
    """
    Рассчитать изменение рейтинга на основе разницы рейтингов команд.
    
    Если победили более сильную команду - больше очков
    Если проиграли более слабой команде - больше потеря
    """
    rating_diff = winner_team_rating - loser_team_rating
    
    if is_winner:
        base = BASE_RATING_WIN
        modifier = int(-rating_diff * RATING_DIFF_MULTIPLIER)
        change = max(10, base + modifier)
    else:
        base = BASE_RATING_LOSE
        modifier = int(rating_diff * RATING_DIFF_MULTIPLIER)
        change = max(10, base - modifier)
        change = -change
    
    if is_mvp:
        change += RATING_MVP_BONUS
    
    return change


def balance_teams(players: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Разделить игроков на две сбалансированные команды."""
    parties = {}
    solo_players = []
    
    for player in players:
        party_id = player.get('party_id')
        if party_id:
            if party_id not in parties:
                parties[party_id] = []
            parties[party_id].append(player)
        else:
            solo_players.append(player)
    
    team1 = []
    team2 = []
    
    party_list = list(parties.values())
    party_list.sort(key=lambda p: sum(player.get('rating', 1000) for player in p), reverse=True)
    
    for party in party_list:
        team1_rating = calculate_team_rating(team1)
        team2_rating = calculate_team_rating(team2)
        
        if team1_rating <= team2_rating and len(team1) + len(party) <= 5:
            team1.extend(party)
        elif len(team2) + len(party) <= 5:
            team2.extend(party)
        elif len(team1) + len(party) <= 5:
            team1.extend(party)
    
    solo_players.sort(key=lambda p: p.get('rating', 1000), reverse=True)
    
    for player in solo_players:
        team1_rating = calculate_team_rating(team1) if team1 else 0
        team2_rating = calculate_team_rating(team2) if team2 else 0
        
        if len(team1) < 5 and (team1_rating <= team2_rating or len(team2) >= 5):
            team1.append(player)
        elif len(team2) < 5:
            team2.append(player)
        else:
            team1.append(player)
    
    return team1, team2


def can_match_players(players: List[Dict[str, Any]], max_rating_diff: int = 300) -> bool:
    """Проверить, можно ли создать сбалансированный матч из этих игроков"""
    if len(players) < 10:
        return False
    ratings = [p.get('rating', 1000) for p in players]
    return max(ratings) - min(ratings) <= max_rating_diff


def find_best_match_group(queue_players: List[Dict[str, Any]], 
                          max_rating_diff: int = 300) -> List[Dict[str, Any]]:
    """Найти лучшую группу из 10 игроков для матча."""
    if len(queue_players) < 10:
        return []
    
    parties = {}
    solo_players = []
    
    for player in queue_players:
        party_id = player.get('party_id')
        if party_id:
            if party_id not in parties:
                parties[party_id] = []
            parties[party_id].append(player)
        else:
            solo_players.append(player)
    
    solo_players.sort(key=lambda p: p.get('rating', 1000))
    selected = []
    
    for party_players in parties.values():
        if len(selected) + len(party_players) <= 10:
            selected.extend(party_players)
    
    remaining_slots = 10 - len(selected)
    if remaining_slots > 0 and len(solo_players) >= remaining_slots:
        if selected:
            avg_rating = sum(p.get('rating', 1000) for p in selected) // len(selected)
            solo_players.sort(key=lambda p: abs(p.get('rating', 1000) - avg_rating))
        selected.extend(solo_players[:remaining_slots])
    
    if len(selected) == 10:
        ratings = [p.get('rating', 1000) for p in selected]
        if max(ratings) - min(ratings) <= max_rating_diff:
            return selected
    
    return []


def assign_sides() -> Tuple[str, str]:
    """Случайно назначить стороны командам"""
    if random.choice([True, False]):
        return SIDES[0], SIDES[1]
    return SIDES[1], SIDES[0]


def get_random_map() -> str:
    """Получить случайную карту"""
    return random.choice(MAPS)


def determine_host(players: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Определить хостера матча.
    Хостер - игрок с наибольшим рейтингом, при равенстве - с большим количеством игр.
    """
    if not players:
        return {}
    
    def player_score(player):
        rating = player.get('rating', 1000)
        wins = player.get('wins', 0)
        losses = player.get('losses', 0)
        total_games = wins + losses
        return rating * 1000 + total_games
    
    return max(players, key=player_score)


def format_player_name(player: Dict[str, Any], with_link: bool = False) -> str:
    """
    Форматировать имя игрока
    
    Args:
        player: данные игрока
        with_link: если True, создаёт кликабельную ссылку на Telegram профиль
    """
    username = player.get('username')
    full_name = player.get('full_name', 'Игрок')
    game_nickname = player.get('game_nickname')
    user_id = player.get('user_id')
    
    # Экранируем спецсимволы в именах
    display_name = escape_markdown(game_nickname or full_name)
    
    if with_link and username:
        return f"[{display_name}](https://t.me/{username})"
    elif with_link and user_id:
        return f"[{display_name}](tg://user?id={user_id})"
    elif username:
        # Экранируем username тоже
        safe_username = escape_markdown(username)
        return f"@{safe_username}"
    
    return display_name


def format_player_stats(player: Dict[str, Any]) -> str:
    """Форматировать статистику игрока"""
    wins = player.get('wins', 0)
    losses = player.get('losses', 0)
    total_games = wins + losses
    winrate = (wins / total_games * 100) if total_games > 0 else 0
    
    kills = player.get('kills', 0)
    deaths = player.get('deaths', 0)
    kd = kills / deaths if deaths > 0 else kills
    
    return (
        f"\n{EMOJI['chart']} *Статистика:*\n"
        f"├ {EMOJI['trophy']} Рейтинг: *{player.get('rating', 1000)}*\n"
        f"├ {EMOJI['sword']} Победы: *{wins}*\n"
        f"├ {EMOJI['shield']} Поражения: *{losses}*\n"
        f"├ {EMOJI['target']} Винрейт: *{winrate:.1f}%*\n"
        f"├ {EMOJI['fire']} K/D: *{kd:.2f}*\n"
        f"├ {EMOJI['medal']} MVP: *{player.get('mvp_count', 0)}*\n"
        f"└ {EMOJI['game']} Всего игр: *{total_games}*\n"
    )


def format_lobby_info(lobby: Dict[str, Any], players: List[Dict[str, Any]], creator_name: str) -> str:
    """Форматировать информацию о лобби"""
    platform_emoji = "🖥️" if lobby['platform'] == 'pc' else "📱"
    player_count = len(players)
    
    players_list = ""
    for i, player in enumerate(players, 1):
        name = format_player_name(player, with_link=True)
        rating = player.get('rating', 1000)
        party_marker = f" {EMOJI['link']}" if player.get('party_id') else ""
        players_list += f"  {i}. {name} [{rating}]{party_marker}\n"
    
    if not players_list:
        players_list = "  Пока никого нет\n"
    
    return (
        f"\n{EMOJI['users']} *ЛОББИ #{lobby['lobby_id']}*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{EMOJI['crown']} Создатель: {creator_name}\n"
        f"{platform_emoji} Платформа: *{lobby['platform'].upper()}*\n"
        f"{EMOJI['users']} Игроки: *{player_count}/10*\n\n"
        f"{EMOJI['target']} *Участники:*\n"
        f"{players_list}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
    )


def format_match_info(match: Dict[str, Any], team1: List[Dict[str, Any]], 
                      team2: List[Dict[str, Any]]) -> str:
    """Форматировать информацию о матче"""
    team1_rating = match.get('team1_avg_rating') or calculate_team_rating(team1)
    team2_rating = match.get('team2_avg_rating') or calculate_team_rating(team2)
    
    all_players = team1 + team2
    host = determine_host(all_players)
    host_name = format_player_name(host, with_link=True) if host else "Не определён"
    host_game_id = host.get('game_id', 'Не указан') if host else "Не указан"
    
    team1_players = ""
    for player in team1:
        name = format_player_name(player, with_link=True)
        rating = player.get('rating', 1000)
        is_host = " 🎖️" if host and player.get('user_id') == host.get('user_id') else ""
        team1_players += f"  • {name} [{rating}]{is_host}\n"
    
    team2_players = ""
    for player in team2:
        name = format_player_name(player, with_link=True)
        rating = player.get('rating', 1000)
        is_host = " 🎖️" if host and player.get('user_id') == host.get('user_id') else ""
        team2_players += f"  • {name} [{rating}]{is_host}\n"
    
    status_emoji = EMOJI['green'] if match['status'] == 'active' else EMOJI['yellow']
    
    return (
        f"\n{EMOJI['sword']} *МАТЧ #{match['match_id']}*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{status_emoji} Статус: *{match['status'].upper()}*\n"
        f"{EMOJI['map']} Карта: *{match['map_name']}*\n\n"
        f"🎖️ *ХОСТЕР:* {host_name}\n"
        f"🆔 *ID хостера:* `{host_game_id}`\n\n"
        f"{EMOJI['red']} *КОМАНДА 1* (Avg: {team1_rating})\n"
        f"Сторона: {match['team1_start_side']}\n"
        f"{team1_players}\n"
        f"{EMOJI['blue']} *КОМАНДА 2* (Avg: {team2_rating})\n"
        f"Сторона: {match['team2_start_side']}\n"
        f"{team2_players}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{EMOJI['info']} *Примечание:* Стороны меняются после 12 раунда!\n"
    )


def format_match_result(match: Dict[str, Any], team1: List[Dict[str, Any]], 
                        team2: List[Dict[str, Any]]) -> str:
    """Форматировать результаты матча"""
    team1_rating = match.get('team1_avg_rating') or calculate_team_rating(team1)
    team2_rating = match.get('team2_avg_rating') or calculate_team_rating(team2)
    
    winner_emoji = EMOJI['trophy']
    
    team1_result = f"{EMOJI['red']} *КОМАНДА 1*"
    team2_result = f"{EMOJI['blue']} *КОМАНДА 2*"
    
    if match['winner_team'] == 1:
        team1_result = f"{winner_emoji} {team1_result} - ПОБЕДА!"
        team2_result = f"{EMOJI['cross']} {team2_result} - Поражение"
    else:
        team1_result = f"{EMOJI['cross']} {team1_result} - Поражение"
        team2_result = f"{winner_emoji} {team2_result} - ПОБЕДА!"
    
    team1_players = ""
    for player in team1:
        name = format_player_name(player, with_link=True)
        kills = player.get('kills', 0)
        deaths = player.get('deaths', 0)
        assists = player.get('assists', 0)
        rating_change = player.get('rating_change', 0)
        mvp = f" {EMOJI['star']}" if player.get('is_mvp') else ""
        sign = "+" if rating_change >= 0 else ""
        team1_players += f"  • {name}{mvp} | K/D/A: {kills}/{deaths}/{assists} | {sign}{rating_change}\n"
    
    team2_players = ""
    for player in team2:
        name = format_player_name(player, with_link=True)
        kills = player.get('kills', 0)
        deaths = player.get('deaths', 0)
        assists = player.get('assists', 0)
        rating_change = player.get('rating_change', 0)
        mvp = f" {EMOJI['star']}" if player.get('is_mvp') else ""
        sign = "+" if rating_change >= 0 else ""
        team2_players += f"  • {name}{mvp} | K/D/A: {kills}/{deaths}/{assists} | {sign}{rating_change}\n"
    
    return (
        f"\n{EMOJI['trophy']} *РЕЗУЛЬТАТЫ МАТЧА #{match['match_id']}*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{EMOJI['map']} Карта: *{match['map_name']}*\n"
        f"{EMOJI['target']} Счёт: *{match['team1_score']} : {match['team2_score']}*\n\n"
        f"{team1_result}\n"
        f"Средний рейтинг: {team1_rating}\n"
        f"{team1_players}\n"
        f"{team2_result}\n"
        f"Средний рейтинг: {team2_rating}\n"
        f"{team2_players}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
    )


def format_top_players(players: List[Dict[str, Any]], title: str = "ТОП ИГРОКОВ") -> str:
    """Форматировать топ игроков"""
    if not players:
        return f"{EMOJI['trophy']} *{title}*\n\nПока нет игроков в рейтинге."
    
    result = f"{EMOJI['trophy']} *{title}*\n━━━━━━━━━━━━━━━━━━━━\n\n"
    
    medals = ["🥇", "🥈", "🥉"]
    
    for i, player in enumerate(players, 1):
        name = format_player_name(player, with_link=True)
        rating = player.get('rating', 1000)
        wins = player.get('wins', 0)
        losses = player.get('losses', 0)
        
        if i <= 3:
            medal = medals[i-1]
        else:
            medal = f"{i}."
        
        result += f"{medal} {name}\n"
        result += f"    {EMOJI['star']} Рейтинг: *{rating}* | W/L: {wins}/{losses}\n\n"
    
    return result


def format_rules() -> str:
    """Форматировать правила"""
    return (
        f"\n{EMOJI['info']} *ПРАВИЛА 3FACE*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{EMOJI['target']} *Общие правила:*\n"
        f"1. Уважайте других игроков\n"
        f"2. Читерство и использование багов запрещено\n"
        f"3. Намеренный слив матчей запрещён\n"
        f"4. Оскорбления и токсичное поведение запрещены\n\n"
        f"{EMOJI['game']} *Правила матчей:*\n"
        f"1. Матчи проводятся в формате 5х5\n"
        f"2. После окончания матча отправьте скриншот результатов\n"
        f"3. Модераторы проверят и подтвердят результат\n"
        f"4. Стороны меняются после 15 раунда\n\n"
        f"🖥️📱 *Правила платформ:*\n"
        f"• Игрокам ПК *запрещено* играть против мобильных игроков\n"
        f"• Мобильные игроки могут сменить платформу на ПК в настройках\n"
        f"• После смены платформы на ПК, вы будете играть против ПК игроков\n"
        f"• Это сделано для честной игры!\n\n"
        f"{EMOJI['chart']} *Рейтинговая система:*\n"
        f"• Победа: +25 рейтинга (базово)\n"
        f"• Поражение: -20 рейтинга (базово)\n"
        f"• MVP матча: +10 дополнительно\n"
        f"• Получаемый рейтинг также зависит от силы противника!\n\n"
        f"{EMOJI['users']} *Пати (группы до {MAX_PARTY_SIZE} человек):*\n"
        f"• Создайте пати, чтобы играть с друзьями\n"
        f"• Игроки в пати всегда в одной команде\n"
        f"• Максимум {MAX_PARTY_SIZE} человек в пати\n\n"
        f"📩 *Поддержка:*\n"
        f"• Нажмите кнопку «Тикет» для связи с администрацией\n"
        f"• Можно задать вопрос, отправить жалобу или предложение\n\n"
        f"{EMOJI['warning']} *Наказания:*\n"
        f"• Нарушение правил - предупреждение\n"
        f"• Повторные нарушения - временный бан\n"
        f"• Серьёзные нарушения - перманентный бан\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{EMOJI['fire']} Удачной игры!\n"
    )


def format_welcome_message(user_name: str) -> str:
    """Форматировать приветственное сообщение"""
    safe_name = escape_markdown(user_name)
    return (
        f"\n{EMOJI['party']} *Добро пожаловать в 3FACE, {safe_name}!*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{EMOJI['game']} 3FACE - это система для организации\n"
        f"матчей с друзьями в формате 5х5.\n\n"
        f"{EMOJI['star']} *Возможности:*\n"
        f"• Поиск матча по кнопке \"Найти игру\"\n"
        f"• Создание лобби для игры с друзьями\n"
        f"• Автоматический баланс команд по рейтингу\n"
        f"• Система пати для игры вместе\n"
        f"• Рейтинговая система\n"
        f"• Топ игроков\n\n"
        f"{EMOJI['target']} *Как начать:*\n"
        f"1. Нажмите \"{EMOJI['search']} Найти игру\"\n"
        f"2. Дождитесь подбора 10 игроков\n"
        f"3. Бот автоматически создаст матч!\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{EMOJI['info']} Используйте кнопки меню для навигации\n"
    )


def format_party_info(party: Dict[str, Any], members: List[Dict[str, Any]], 
                      leader_name: str) -> str:
    """Форматировать информацию о пати"""
    members_list = ""
    for i, member in enumerate(members, 1):
        name = format_player_name(member, with_link=True)
        rating = member.get('rating', 1000)
        is_leader = " 👑" if member.get('user_id') == party.get('leader_id') else ""
        members_list += f"  {i}. {name}{is_leader} [{rating}]\n"
    
    avg_rating = calculate_team_rating(members)
    
    return (
        f"\n{EMOJI['party']} *ПАТИ*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{EMOJI['crown']} Лидер: {leader_name}\n"
        f"{EMOJI['users']} Участники: *{len(members)}/{MAX_PARTY_SIZE}*\n"
        f"{EMOJI['star']} Средний рейтинг: *{avg_rating}*\n\n"
        f"{EMOJI['target']} *Состав:*\n"
        f"{members_list}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{EMOJI['info']} Пригласите друзей, чтобы играть вместе!\n"
    )


def format_history_entry(match: Dict[str, Any], user_team: int) -> str:
    """Форматировать запись из истории матчей"""
    is_winner = match.get('winner_team') == user_team
    result = f"{EMOJI['check']} Победа" if is_winner else f"{EMOJI['cross']} Поражение"
    
    kills = match.get('kills', 0)
    deaths = match.get('deaths', 0)
    assists = match.get('assists', 0)
    rating_change = match.get('rating_change', 0)
    sign = "+" if rating_change >= 0 else ""
    
    mvp = f" {EMOJI['star']}" if match.get('is_mvp') else ""
    
    return (
        f"\n{EMOJI['game']} Матч #{match['match_id']}{mvp}\n"
        f"├ {EMOJI['map']} {match['map_name']}\n"
        f"├ {result} ({match['team1_score']}:{match['team2_score']})\n"
        f"├ K/D/A: {kills}/{deaths}/{assists}\n"
        f"└ Рейтинг: {sign}{rating_change}\n"
    )


def format_queue_status(queue_count: int, platform: str) -> str:
    """Форматировать статус очереди"""
    from config import PLATFORMS
    platform_name = PLATFORMS.get(platform, platform)
    
    return (
        f"\n{EMOJI['search']} *ПОИСК ИГРЫ*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{EMOJI['queue']} В очереди: *{queue_count}* игроков\n"
        f"{platform_name}\n\n"
        f"{EMOJI['info']} Для матча нужно *10* игроков\n"
        f"{EMOJI['clock']} Подбор по рейтингу...\n"
    )
