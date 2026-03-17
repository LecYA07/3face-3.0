from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from typing import List, Optional
import logging

import database as db
from keyboards import (
    get_ticket_type_keyboard, get_ticket_cancel_keyboard,
    get_ticket_admin_keyboard, get_main_menu_keyboard,
    get_tickets_list_keyboard, get_ticket_detail_keyboard,
    get_user_ticket_keyboard
)
from utils import format_player_name
from config import EMOJI, ADMIN_IDS

router = Router()
logger = logging.getLogger(__name__)


class TicketStates(StatesGroup):
    waiting_for_type = State()
    waiting_for_message = State()
    waiting_for_photo = State()
    waiting_for_reply = State()
    waiting_for_user_reply = State()


TICKET_TYPES = {
    "question": "❓ Вопрос",
    "report": "🚨 Жалоба на игрока",
    "bug": "🐛 Баг/Ошибка",
    "suggestion": "💡 Предложение"
}

TICKET_STATUS_NAMES = {
    "open": "🟢 Открыт",
    "answered": "💬 Отвечен",
    "closed": "🔒 Закрыт"
}


@router.message(F.text == "📩 Тикет")
async def show_ticket_menu(message: Message, state: FSMContext):
    """Показать меню тикетов"""
    user = await db.get_user(message.from_user.id)
    if not user:
        await message.answer(
            f"{EMOJI['warning']} Сначала зарегистрируйтесь командой /start"
        )
        return
    
    # Проверяем, является ли пользователь модератором
    is_mod = await db.is_user_moderator(message.from_user.id)
    
    if is_mod:
        # Показываем меню для модераторов - список тикетов
        await show_tickets_list(message, None)
    else:
        # Обычное меню для пользователей
        # Проверяем активные тикеты пользователя
        user_tickets = await db.get_user_tickets(message.from_user.id, limit=5)
        
        if user_tickets:
            # Показываем список тикетов пользователя
            text = f"📩 *ВАШИ ТИКЕТЫ*\n━━━━━━━━━━━━━━━━━━━━\n\n"
            
            for ticket in user_tickets:
                status = TICKET_STATUS_NAMES.get(ticket['status'], ticket['status'])
                type_name = TICKET_TYPES.get(ticket['ticket_type'], ticket['ticket_type'])
                text += f"📋 *Тикет #{ticket['ticket_id']}*\n"
                text += f"├ Тип: {type_name}\n"
                text += f"├ Статус: {status}\n"
                text += f"└ Сообщение: {ticket['message'][:50]}{'...' if len(ticket['message']) > 50 else ''}\n\n"
            
            text += "Выберите тикет или создайте новый:"
            
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            buttons = []
            for ticket in user_tickets:
                status_emoji = "🟢" if ticket['status'] == 'open' else ("💬" if ticket['status'] == 'answered' else "🔒")
                buttons.append([InlineKeyboardButton(
                    text=f"{status_emoji} Тикет #{ticket['ticket_id']}",
                    callback_data=f"ticket:view_my:{ticket['ticket_id']}"
                )])
            
            buttons.append([InlineKeyboardButton(
                text="➕ Создать новый тикет",
                callback_data="ticket:new"
            )])
            
            await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="Markdown")
        else:
            # Нет тикетов - показываем меню создания
            await message.answer(
                f"📩 *ТИКЕТЫ*\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"Выберите тип обращения:\n\n"
                f"❓ *Вопрос* - задать вопрос администрации\n"
                f"🚨 *Жалоба* - пожаловаться на игрока\n"
                f"🐛 *Баг* - сообщить об ошибке\n"
                f"💡 *Предложение* - предложить идею\n",
                reply_markup=get_ticket_type_keyboard(),
                parse_mode="Markdown"
            )
            await state.set_state(TicketStates.waiting_for_type)


async def show_tickets_list(message_or_callback, filter_status: str = None):
    """Показать список тикетов для модераторов"""
    tickets = await db.get_all_tickets(status=filter_status, limit=20)
    
    text = f"📩 *ВСЕ ТИКЕТЫ*\n━━━━━━━━━━━━━━━━━━━━\n\n"
    
    if not tickets:
        text += "Нет тикетов"
        if filter_status:
            text += f" со статусом '{TICKET_STATUS_NAMES.get(filter_status, filter_status)}'"
        text += ".\n"
    else:
        for ticket in tickets[:15]:  # Показываем максимум 15
            status = TICKET_STATUS_NAMES.get(ticket['status'], ticket['status'])
            type_name = TICKET_TYPES.get(ticket['ticket_type'], ticket['ticket_type'])
            user_name = ticket.get('game_nickname') or ticket.get('username') or ticket.get('full_name', 'Неизвестно')
            
            text += f"📋 *#{ticket['ticket_id']}* | {status}\n"
            text += f"├ 👤 {user_name}\n"
            text += f"├ 📝 {type_name}\n"
            
            if ticket.get('responder_name') or ticket.get('responder_username'):
                responder = ticket.get('responder_username') or ticket.get('responder_name', '')
                text += f"├ 💬 Ответил: @{responder}\n"
            
            text += f"└ {ticket['message'][:40]}{'...' if len(ticket['message']) > 40 else ''}\n\n"
    
    # Статистика
    stats = await db.get_ticket_stats()
    text += f"\n📊 *Статистика:*\n"
    text += f"├ 🟢 Открытых: {stats['open']}\n"
    text += f"├ 💬 Отвеченных: {stats['answered']}\n"
    text += f"└ 🔒 Закрытых: {stats['closed']}\n"
    
    # Добавляем кнопки для просмотра конкретных тикетов
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    buttons = []
    
    # Кнопки с тикетами (только открытые и отвеченные для быстрого доступа)
    active_tickets = [t for t in tickets if t['status'] in ('open', 'answered')][:5]
    for ticket in active_tickets:
        status_emoji = "🟢" if ticket['status'] == 'open' else "💬"
        user_name = ticket.get('game_nickname') or ticket.get('username') or 'Неизвестно'
        buttons.append([InlineKeyboardButton(
            text=f"{status_emoji} #{ticket['ticket_id']} - {user_name[:15]}",
            callback_data=f"ticket:detail:{ticket['ticket_id']}"
        )])
    
    # Добавляем фильтры
    filter_buttons = []
    filter_buttons.append(InlineKeyboardButton(
        text="📂 Все" + (" ✓" if filter_status is None else ""),
        callback_data="tickets:filter:all"
    ))
    filter_buttons.append(InlineKeyboardButton(
        text="🟢 Открытые" + (" ✓" if filter_status == "open" else ""),
        callback_data="tickets:filter:open"
    ))
    buttons.append(filter_buttons)
    
    filter_buttons2 = []
    filter_buttons2.append(InlineKeyboardButton(
        text="💬 Отвеченные" + (" ✓" if filter_status == "answered" else ""),
        callback_data="tickets:filter:answered"
    ))
    filter_buttons2.append(InlineKeyboardButton(
        text="🔒 Закрытые" + (" ✓" if filter_status == "closed" else ""),
        callback_data="tickets:filter:closed"
    ))
    buttons.append(filter_buttons2)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    if isinstance(message_or_callback, CallbackQuery):
        try:
            await message_or_callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
        except Exception:
            await message_or_callback.message.answer(text, reply_markup=keyboard, parse_mode="Markdown")
    else:
        await message_or_callback.answer(text, reply_markup=keyboard, parse_mode="Markdown")


@router.callback_query(F.data.startswith("tickets:filter:"))
async def filter_tickets(callback: CallbackQuery):
    """Фильтрация тикетов"""
    if not await db.is_user_moderator(callback.from_user.id):
        await callback.answer("У вас нет прав!", show_alert=True)
        return
    
    filter_type = callback.data.split(":")[2]
    filter_status = None if filter_type == "all" else filter_type
    
    await show_tickets_list(callback, filter_status)
    await callback.answer()


@router.callback_query(F.data == "tickets:back")
async def back_to_tickets_list(callback: CallbackQuery):
    """Вернуться к списку тикетов"""
    if not await db.is_user_moderator(callback.from_user.id):
        await callback.answer("У вас нет прав!", show_alert=True)
        return
    
    await show_tickets_list(callback, None)
    await callback.answer()


@router.callback_query(F.data.startswith("ticket:detail:"))
async def show_ticket_detail(callback: CallbackQuery):
    """Показать детали тикета (для модераторов)"""
    if not await db.is_user_moderator(callback.from_user.id):
        await callback.answer("У вас нет прав!", show_alert=True)
        return
    
    ticket_id = int(callback.data.split(":")[2])
    ticket = await db.get_ticket(ticket_id)
    
    if not ticket:
        await callback.answer("Тикет не найден!", show_alert=True)
        return
    
    user = await db.get_user(ticket['user_id'])
    user_name = format_player_name(user) if user else f"ID: {ticket['user_id']}"
    type_name = TICKET_TYPES.get(ticket['ticket_type'], ticket['ticket_type'])
    status = TICKET_STATUS_NAMES.get(ticket['status'], ticket['status'])
    
    text = f"📋 *ТИКЕТ #{ticket_id}*\n━━━━━━━━━━━━━━━━━━━━\n\n"
    text += f"👤 *От:* {user_name}\n"
    text += f"📝 *Тип:* {type_name}\n"
    text += f"📊 *Статус:* {status}\n"
    text += f"📅 *Создан:* {ticket['created_at']}\n\n"
    text += f"💬 *Сообщение:*\n{ticket['message']}\n"
    
    if ticket.get('admin_response'):
        responder = await db.get_user(ticket['responded_by']) if ticket.get('responded_by') else None
        responder_name = format_player_name(responder) if responder else "Администратор"
        text += f"\n\n✉️ *Ответ от {responder_name}:*\n{ticket['admin_response']}"
    
    has_photo = bool(ticket.get('photo_file_id'))
    
    await callback.message.edit_text(
        text,
        reply_markup=get_ticket_detail_keyboard(ticket_id, ticket['status'], has_photo),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("ticket:history:"))
async def show_ticket_history(callback: CallbackQuery):
    """Показать историю сообщений тикета (для модераторов)"""
    if not await db.is_user_moderator(callback.from_user.id):
        await callback.answer("У вас нет прав!", show_alert=True)
        return
    
    ticket_id = int(callback.data.split(":")[2])
    ticket = await db.get_ticket(ticket_id)
    
    if not ticket:
        await callback.answer("Тикет не найден!", show_alert=True)
        return
    
    messages = await db.get_ticket_messages(ticket_id)
    
    text = f"📜 *ИСТОРИЯ ТИКЕТА #{ticket_id}*\n━━━━━━━━━━━━━━━━━━━━\n\n"
    
    # Первое сообщение (создание тикета)
    user = await db.get_user(ticket['user_id'])
    user_name = format_player_name(user) if user else "Пользователь"
    text += f"👤 *{user_name}* (создание):\n{ticket['message'][:300]}{'...' if len(ticket['message']) > 300 else ''}\n\n"
    
    # История сообщений
    for msg in messages:
        msg_user_name = msg.get('game_nickname') or msg.get('username') or msg.get('full_name', 'Неизвестно')
        role = "👑 Модератор" if msg['is_admin'] else "👤 Пользователь"
        text += f"{role} *{msg_user_name}*:\n{msg['message'][:200]}{'...' if len(msg['message']) > 200 else ''}\n"
        if msg.get('photo_file_id'):
            text += "📷 [Фото прикреплено]\n"
        text += "\n"
    
    if not messages and not ticket.get('admin_response'):
        text += "_Нет дополнительных сообщений_\n"
    elif ticket.get('admin_response') and not messages:
        # Старый формат ответа (до внедрения истории)
        responder = await db.get_user(ticket['responded_by']) if ticket.get('responded_by') else None
        responder_name = format_player_name(responder) if responder else "Модератор"
        text += f"👑 *{responder_name}* (ответ):\n{ticket['admin_response']}\n"
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад к тикету", callback_data=f"ticket:detail:{ticket_id}")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data.startswith("ticket:my_history:"))
async def show_my_ticket_history(callback: CallbackQuery):
    """Показать историю своего тикета (для пользователей)"""
    ticket_id = int(callback.data.split(":")[2])
    ticket = await db.get_ticket(ticket_id)
    
    if not ticket:
        await callback.answer("Тикет не найден!", show_alert=True)
        return
    
    # Проверяем, что это тикет пользователя
    if ticket['user_id'] != callback.from_user.id:
        await callback.answer("Это не ваш тикет!", show_alert=True)
        return
    
    messages = await db.get_ticket_messages(ticket_id)
    
    text = f"📜 *ИСТОРИЯ ТИКЕТА #{ticket_id}*\n━━━━━━━━━━━━━━━━━━━━\n\n"
    
    # Первое сообщение
    text += f"👤 *Вы* (создание):\n{ticket['message'][:300]}{'...' if len(ticket['message']) > 300 else ''}\n\n"
    
    # История сообщений
    for msg in messages:
        role = "👑 Модератор" if msg['is_admin'] else "👤 Вы"
        text += f"{role}:\n{msg['message'][:200]}{'...' if len(msg['message']) > 200 else ''}\n"
        if msg.get('photo_file_id'):
            text += "📷 [Фото прикреплено]\n"
        text += "\n"
    
    if not messages and ticket.get('admin_response'):
        text += f"👑 *Модератор* (ответ):\n{ticket['admin_response']}\n"
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data=f"ticket:view_my:{ticket_id}")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data.startswith("ticket:view_my:"))
async def view_my_ticket(callback: CallbackQuery):
    """Просмотр своего тикета"""
    ticket_id = int(callback.data.split(":")[2])
    ticket = await db.get_ticket(ticket_id)
    
    if not ticket:
        await callback.answer("Тикет не найден!", show_alert=True)
        return
    
    if ticket['user_id'] != callback.from_user.id:
        await callback.answer("Это не ваш тикет!", show_alert=True)
        return
    
    type_name = TICKET_TYPES.get(ticket['ticket_type'], ticket['ticket_type'])
    status = TICKET_STATUS_NAMES.get(ticket['status'], ticket['status'])
    
    text = f"📋 *ТИКЕТ #{ticket_id}*\n━━━━━━━━━━━━━━━━━━━━\n\n"
    text += f"📝 *Тип:* {type_name}\n"
    text += f"📊 *Статус:* {status}\n\n"
    text += f"💬 *Ваше сообщение:*\n{ticket['message']}\n"
    
    if ticket.get('admin_response'):
        text += f"\n\n✉️ *Ответ модератора:*\n{ticket['admin_response']}"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_user_ticket_keyboard(ticket_id, ticket['status']),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data == "ticket:new")
async def create_new_ticket(callback: CallbackQuery, state: FSMContext):
    """Создать новый тикет"""
    await callback.message.edit_text(
        f"📩 *НОВЫЙ ТИКЕТ*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Выберите тип обращения:\n\n"
        f"❓ *Вопрос* - задать вопрос администрации\n"
        f"🚨 *Жалоба* - пожаловаться на игрока\n"
        f"🐛 *Баг* - сообщить об ошибке\n"
        f"💡 *Предложение* - предложить идею\n",
        reply_markup=get_ticket_type_keyboard(),
        parse_mode="Markdown"
    )
    await state.set_state(TicketStates.waiting_for_type)
    await callback.answer()


@router.callback_query(F.data.startswith("ticket:type:"))
async def select_ticket_type(callback: CallbackQuery, state: FSMContext):
    """Выбор типа тикета"""
    ticket_type = callback.data.split(":")[2]
    
    if ticket_type not in TICKET_TYPES:
        await callback.answer("Неизвестный тип тикета!", show_alert=True)
        return
    
    await state.update_data(ticket_type=ticket_type)
    await state.set_state(TicketStates.waiting_for_message)
    
    type_name = TICKET_TYPES[ticket_type]
    
    await callback.message.edit_text(
        f"📩 *{type_name}*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Опишите вашу проблему или вопрос подробно.\n\n"
        f"💡 *Советы:*\n"
        f"• Опишите ситуацию максимально подробно\n"
        f"• Укажите ники игроков, если это жалоба\n"
        f"• Укажите время, когда произошла проблема\n\n"
        f"📷 Вы можете отправить *текст* или *фото с подписью*:",
        reply_markup=get_ticket_cancel_keyboard(),
        parse_mode="Markdown"
    )


@router.callback_query(F.data == "ticket:cancel")
async def cancel_ticket(callback: CallbackQuery, state: FSMContext):
    """Отмена создания тикета"""
    await state.clear()
    await callback.message.edit_text(
        f"{EMOJI['check']} Создание тикета отменено.",
        parse_mode="Markdown"
    )
    await callback.answer("Отменено")


@router.message(TicketStates.waiting_for_message, F.photo)
async def process_ticket_photo(message: Message, state: FSMContext):
    """Обработка фото тикета"""
    photo_file_id = message.photo[-1].file_id
    ticket_text = message.caption.strip() if message.caption else ""
    
    if len(ticket_text) < 10:
        await message.answer(
            f"{EMOJI['warning']} Подпись к фото слишком короткая! "
            f"Опишите проблему подробнее (минимум 10 символов).",
            parse_mode="Markdown"
        )
        return
    
    if len(ticket_text) > 2000:
        await message.answer(
            f"{EMOJI['warning']} Подпись слишком длинная! Максимум 2000 символов.",
            parse_mode="Markdown"
        )
        return
    
    data = await state.get_data()
    ticket_type = data.get('ticket_type', 'question')
    
    ticket_id = await db.create_ticket(
        user_id=message.from_user.id,
        ticket_type=ticket_type,
        message=ticket_text,
        photo_file_id=photo_file_id
    )
    
    await state.clear()
    
    type_name = TICKET_TYPES.get(ticket_type, "Вопрос")
    
    await message.answer(
        f"{EMOJI['check']} *Тикет #{ticket_id} создан!*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📋 *Тип:* {type_name}\n"
        f"📷 *Фото:* прикреплено\n"
        f"📝 *Сообщение:*\n{ticket_text[:200]}{'...' if len(ticket_text) > 200 else ''}\n\n"
        f"{EMOJI['clock']} Ожидайте ответа от администрации.\n"
        f"Вам придёт уведомление, когда на тикет ответят.",
        reply_markup=get_main_menu_keyboard(is_admin=message.from_user.id in ADMIN_IDS),
        parse_mode="Markdown"
    )
    
    await notify_admins_new_ticket(message.bot, ticket_id, message.from_user.id, ticket_type, ticket_text, photo_file_id)


@router.message(TicketStates.waiting_for_message, F.text)
async def process_ticket_message(message: Message, state: FSMContext):
    """Обработка текста тикета"""
    ticket_text = message.text.strip()
    
    if len(ticket_text) < 10:
        await message.answer(
            f"{EMOJI['warning']} Сообщение слишком короткое! Минимум 10 символов.",
            parse_mode="Markdown"
        )
        return
    
    if len(ticket_text) > 2000:
        await message.answer(
            f"{EMOJI['warning']} Сообщение слишком длинное! Максимум 2000 символов.",
            parse_mode="Markdown"
        )
        return
    
    data = await state.get_data()
    ticket_type = data.get('ticket_type', 'question')
    
    ticket_id = await db.create_ticket(
        user_id=message.from_user.id,
        ticket_type=ticket_type,
        message=ticket_text
    )
    
    await state.clear()
    
    type_name = TICKET_TYPES.get(ticket_type, "Вопрос")
    
    await message.answer(
        f"{EMOJI['check']} *Тикет #{ticket_id} создан!*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📋 *Тип:* {type_name}\n"
        f"📝 *Сообщение:*\n{ticket_text[:200]}{'...' if len(ticket_text) > 200 else ''}\n\n"
        f"{EMOJI['clock']} Ожидайте ответа от администрации.",
        reply_markup=get_main_menu_keyboard(is_admin=message.from_user.id in ADMIN_IDS),
        parse_mode="Markdown"
    )
    
    await notify_admins_new_ticket(message.bot, ticket_id, message.from_user.id, ticket_type, ticket_text)


async def notify_admins_new_ticket(bot: Bot, ticket_id: int, user_id: int, ticket_type: str, message_text: str, photo_file_id: str = None):
    """Уведомить администраторов о новом тикете"""
    from config import ADMIN_IDS, MODERATOR_IDS
    
    user = await db.get_user(user_id)
    user_name = format_player_name(user) if user else f"ID: {user_id}"
    type_name = TICKET_TYPES.get(ticket_type, "Вопрос")
    
    notification_text = (
        f"📩 *НОВЫЙ ТИКЕТ #{ticket_id}*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 *От:* {user_name}\n"
        f"📋 *Тип:* {type_name}\n"
    )
    
    if photo_file_id:
        notification_text += f"📷 *Фото:* прикреплено\n"
    
    notification_text += f"\n📝 *Сообщение:*\n{message_text[:500]}{'...' if len(message_text) > 500 else ''}"
    
    admin_ids = set(ADMIN_IDS + MODERATOR_IDS)
    
    for admin_id in admin_ids:
        try:
            if photo_file_id:
                await bot.send_photo(
                    admin_id,
                    photo=photo_file_id,
                    caption=notification_text,
                    reply_markup=get_ticket_admin_keyboard(ticket_id, has_photo=True),
                    parse_mode="Markdown"
                )
            else:
                await bot.send_message(
                    admin_id,
                    notification_text,
                    reply_markup=get_ticket_admin_keyboard(ticket_id, has_photo=False),
                    parse_mode="Markdown"
                )
        except Exception as e:
            logger.warning(f"Failed to notify admin {admin_id} about new ticket: {e}")


@router.callback_query(F.data.startswith("ticket:photo:"))
async def view_ticket_photo(callback: CallbackQuery):
    """Посмотреть фото тикета"""
    ticket_id = int(callback.data.split(":")[2])
    
    if not await db.is_user_moderator(callback.from_user.id):
        await callback.answer("У вас нет прав!", show_alert=True)
        return
    
    ticket = await db.get_ticket(ticket_id)
    if not ticket:
        await callback.answer("Тикет не найден!", show_alert=True)
        return
    
    if not ticket.get('photo_file_id'):
        await callback.answer("К этому тикету не прикреплено фото!", show_alert=True)
        return
    
    user = await db.get_user(ticket['user_id'])
    user_name = format_player_name(user) if user else f"ID: {ticket['user_id']}"
    type_name = TICKET_TYPES.get(ticket['ticket_type'], "Вопрос")
    
    await callback.message.answer_photo(
        photo=ticket['photo_file_id'],
        caption=(
            f"📷 *Фото из тикета #{ticket_id}*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👤 *От:* {user_name}\n"
            f"📋 *Тип:* {type_name}\n\n"
            f"📝 *Сообщение:*\n{ticket['message'][:500]}{'...' if len(ticket['message']) > 500 else ''}"
        ),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("ticket:reply:"))
async def start_ticket_reply(callback: CallbackQuery, state: FSMContext):
    """Начать ответ на тикет (модератор)"""
    ticket_id = int(callback.data.split(":")[2])
    
    if not await db.is_user_moderator(callback.from_user.id):
        await callback.answer("У вас нет прав!", show_alert=True)
        return
    
    ticket = await db.get_ticket(ticket_id)
    if not ticket:
        await callback.answer("Тикет не найден!", show_alert=True)
        return
    
    if ticket['status'] == 'closed':
        await callback.answer("Тикет уже закрыт!", show_alert=True)
        return
    
    await state.update_data(reply_ticket_id=ticket_id)
    await state.set_state(TicketStates.waiting_for_reply)
    
    await callback.message.answer(
        f"💬 *Ответ на тикет #{ticket_id}*\n\n"
        f"Введите ваш ответ пользователю:",
        reply_markup=get_ticket_cancel_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.message(TicketStates.waiting_for_reply)
async def process_ticket_reply(message: Message, state: FSMContext):
    """Обработка ответа на тикет (модератор)"""
    reply_text = message.text.strip()
    
    if len(reply_text) < 5:
        await message.answer(f"{EMOJI['warning']} Ответ слишком короткий!", parse_mode="Markdown")
        return
    
    data = await state.get_data()
    ticket_id = data.get('reply_ticket_id')
    
    if not ticket_id:
        await state.clear()
        await message.answer(f"{EMOJI['warning']} Ошибка: тикет не найден.")
        return
    
    ticket = await db.get_ticket(ticket_id)
    if not ticket:
        await state.clear()
        await message.answer(f"{EMOJI['warning']} Тикет не найден!")
        return
    
    await db.respond_to_ticket(ticket_id, reply_text, message.from_user.id)
    await state.clear()
    
    await message.answer(
        f"{EMOJI['check']} *Ответ на тикет #{ticket_id} отправлен!*",
        parse_mode="Markdown"
    )
    
    try:
        type_name = TICKET_TYPES.get(ticket['ticket_type'], "Вопрос")
        admin = await db.get_user(message.from_user.id)
        admin_name = format_player_name(admin) if admin else "Администратор"
        
        await message.bot.send_message(
            ticket['user_id'],
            f"📩 *Ответ на ваш тикет #{ticket_id}*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📋 *Тип:* {type_name}\n"
            f"📝 *Ваш вопрос:*\n{ticket['message'][:200]}{'...' if len(ticket['message']) > 200 else ''}\n\n"
            f"💬 *Ответ от {admin_name}:*\n{reply_text}\n\n"
            f"Вы можете продолжить диалог, нажав кнопку ниже:",
            reply_markup=get_user_ticket_keyboard(ticket_id, 'answered'),
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.warning(f"Failed to notify user about ticket reply: {e}")


@router.callback_query(F.data.startswith("ticket:user_reply:"))
async def start_user_reply(callback: CallbackQuery, state: FSMContext):
    """Начать ответ от пользователя"""
    ticket_id = int(callback.data.split(":")[2])
    
    ticket = await db.get_ticket(ticket_id)
    if not ticket:
        await callback.answer("Тикет не найден!", show_alert=True)
        return
    
    if ticket['user_id'] != callback.from_user.id:
        await callback.answer("Это не ваш тикет!", show_alert=True)
        return
    
    if ticket['status'] == 'closed':
        await callback.answer("Тикет закрыт!", show_alert=True)
        return
    
    await state.update_data(user_reply_ticket_id=ticket_id)
    await state.set_state(TicketStates.waiting_for_user_reply)
    
    await callback.message.answer(
        f"💬 *Дополнение к тикету #{ticket_id}*\n\n"
        f"Напишите ваше сообщение:",
        reply_markup=get_ticket_cancel_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.message(TicketStates.waiting_for_user_reply)
async def process_user_reply(message: Message, state: FSMContext):
    """Обработка ответа от пользователя"""
    reply_text = message.text.strip() if message.text else ""
    photo_file_id = message.photo[-1].file_id if message.photo else None
    
    if message.photo and message.caption:
        reply_text = message.caption.strip()
    
    if len(reply_text) < 5:
        await message.answer(f"{EMOJI['warning']} Сообщение слишком короткое!", parse_mode="Markdown")
        return
    
    data = await state.get_data()
    ticket_id = data.get('user_reply_ticket_id')
    
    if not ticket_id:
        await state.clear()
        await message.answer(f"{EMOJI['warning']} Ошибка: тикет не найден.")
        return
    
    ticket = await db.get_ticket(ticket_id)
    if not ticket:
        await state.clear()
        await message.answer(f"{EMOJI['warning']} Тикет не найден!")
        return
    
    # Добавляем сообщение в историю
    await db.add_ticket_message(ticket_id, message.from_user.id, reply_text, is_admin=False, photo_file_id=photo_file_id)
    
    # Переоткрываем тикет если он был отвечен
    if ticket['status'] == 'answered':
        await db.reopen_ticket(ticket_id)
    
    await state.clear()
    
    await message.answer(
        f"{EMOJI['check']} *Сообщение добавлено к тикету #{ticket_id}!*\n\n"
        f"Модераторы получат уведомление.",
        parse_mode="Markdown"
    )
    
    # Уведомляем модераторов
    from config import ADMIN_IDS, MODERATOR_IDS
    
    user = await db.get_user(message.from_user.id)
    user_name = format_player_name(user) if user else f"ID: {message.from_user.id}"
    
    notification_text = (
        f"📩 *НОВОЕ СООБЩЕНИЕ В ТИКЕТЕ #{ticket_id}*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 *От:* {user_name}\n\n"
        f"💬 *Сообщение:*\n{reply_text[:500]}{'...' if len(reply_text) > 500 else ''}"
    )
    
    admin_ids = set(ADMIN_IDS + MODERATOR_IDS)
    
    for admin_id in admin_ids:
        try:
            await message.bot.send_message(
                admin_id,
                notification_text,
                reply_markup=get_ticket_admin_keyboard(ticket_id, has_photo=bool(photo_file_id)),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.warning(f"Failed to notify admin {admin_id}: {e}")


@router.callback_query(F.data.startswith("ticket:close:"))
async def close_ticket_handler(callback: CallbackQuery):
    """Закрыть тикет"""
    ticket_id = int(callback.data.split(":")[2])
    
    if not await db.is_user_moderator(callback.from_user.id):
        await callback.answer("У вас нет прав!", show_alert=True)
        return
    
    ticket = await db.get_ticket(ticket_id)
    if not ticket:
        await callback.answer("Тикет не найден!", show_alert=True)
        return
    
    if ticket['status'] == 'closed':
        await callback.answer("Тикет уже закрыт!", show_alert=True)
        return
    
    await db.close_ticket(ticket_id, callback.from_user.id)
    
    if callback.message.photo:
        current_caption = callback.message.caption or ""
        await callback.message.edit_caption(
            caption=current_caption + f"\n\n{EMOJI['check']} *Тикет закрыт*",
            parse_mode="Markdown"
        )
    else:
        current_text = callback.message.text or ""
        await callback.message.edit_text(
            current_text + f"\n\n{EMOJI['check']} *Тикет закрыт*",
            parse_mode="Markdown"
        )
    await callback.answer("Тикет закрыт!")
    
    # Уведомляем пользователя о закрытии тикета
    try:
        admin = await db.get_user(callback.from_user.id)
        admin_name = format_player_name(admin) if admin else "Модератор"
        
        await callback.bot.send_message(
            ticket['user_id'],
            f"🔒 *Ваш тикет #{ticket_id} закрыт*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Тикет закрыт модератором {admin_name}.\n\n"
            f"Если у вас остались вопросы, вы можете создать новый тикет.",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.warning(f"Failed to notify user about ticket close: {e}")


@router.callback_query(F.data.startswith("ticket:reopen:"))
async def reopen_ticket_handler(callback: CallbackQuery):
    """Переоткрыть тикет"""
    ticket_id = int(callback.data.split(":")[2])
    
    if not await db.is_user_moderator(callback.from_user.id):
        await callback.answer("У вас нет прав!", show_alert=True)
        return
    
    ticket = await db.get_ticket(ticket_id)
    if not ticket:
        await callback.answer("Тикет не найден!", show_alert=True)
        return
    
    if ticket['status'] != 'closed':
        await callback.answer("Тикет не закрыт!", show_alert=True)
        return
    
    await db.reopen_ticket(ticket_id)
    
    await callback.message.edit_text(
        f"📋 *ТИКЕТ #{ticket_id} ПЕРЕОТКРЫТ*\n\n"
        f"Тикет снова доступен для обработки.",
        reply_markup=get_ticket_detail_keyboard(ticket_id, 'open', bool(ticket.get('photo_file_id'))),
        parse_mode="Markdown"
    )
    await callback.answer("Тикет переоткрыт!")


# ============ КОМАНДЫ ДЛЯ БЫСТРОГО ДОСТУПА ============

@router.message(F.text == "/tickets")
async def tickets_command(message: Message):
    """Команда для быстрого доступа к тикетам (для модераторов)"""
    if not await db.is_user_moderator(message.from_user.id):
        await message.answer(f"{EMOJI['lock']} Эта команда доступна только модераторам.")
        return
    
    await show_tickets_list(message, None)


@router.message(F.text.startswith("/ticket "))
async def ticket_by_id_command(message: Message):
    """Команда для просмотра тикета по ID"""
    if not await db.is_user_moderator(message.from_user.id):
        await message.answer(f"{EMOJI['lock']} Эта команда доступна только модераторам.")
        return
    
    try:
        ticket_id = int(message.text.split()[1])
    except (IndexError, ValueError):
        await message.answer(f"{EMOJI['warning']} Укажите номер тикета: /ticket 123")
        return
    
    ticket = await db.get_ticket(ticket_id)
    if not ticket:
        await message.answer(f"{EMOJI['warning']} Тикет #{ticket_id} не найден!")
        return
    
    user = await db.get_user(ticket['user_id'])
    user_name = format_player_name(user) if user else f"ID: {ticket['user_id']}"
    type_name = TICKET_TYPES.get(ticket['ticket_type'], ticket['ticket_type'])
    status = TICKET_STATUS_NAMES.get(ticket['status'], ticket['status'])
    
    text = f"📋 *ТИКЕТ #{ticket_id}*\n━━━━━━━━━━━━━━━━━━━━\n\n"
    text += f"👤 *От:* {user_name}\n"
    text += f"📝 *Тип:* {type_name}\n"
    text += f"📊 *Статус:* {status}\n"
    text += f"📅 *Создан:* {ticket['created_at']}\n\n"
    text += f"💬 *Сообщение:*\n{ticket['message']}\n"
    
    if ticket.get('admin_response'):
        responder = await db.get_user(ticket['responded_by']) if ticket.get('responded_by') else None
        responder_name = format_player_name(responder) if responder else "Администратор"
        text += f"\n\n✉️ *Ответ от {responder_name}:*\n{ticket['admin_response']}"
    
    has_photo = bool(ticket.get('photo_file_id'))
    
    await message.answer(
        text,
        reply_markup=get_ticket_detail_keyboard(ticket_id, ticket['status'], has_photo),
        parse_mode="Markdown"
    )
