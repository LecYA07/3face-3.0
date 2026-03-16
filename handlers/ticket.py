from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from typing import List, Optional
import logging

import database as db
from keyboards import (
    get_ticket_type_keyboard, get_ticket_cancel_keyboard,
    get_ticket_admin_keyboard, get_main_menu_keyboard
)
from utils import format_player_name
from config import EMOJI

router = Router()
logger = logging.getLogger(__name__)


class TicketStates(StatesGroup):
    waiting_for_type = State()
    waiting_for_message = State()
    waiting_for_photo = State()
    waiting_for_reply = State()


TICKET_TYPES = {
    "question": "❓ Вопрос",
    "report": "🚨 Жалоба на игрока",
    "bug": "🐛 Баг/Ошибка",
    "suggestion": "💡 Предложение"
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
    # Получаем file_id самого большого размера фото
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
            f"{EMOJI['warning']} Подпись слишком длинная! "
            f"Максимум 2000 символов.",
            parse_mode="Markdown"
        )
        return
    
    data = await state.get_data()
    ticket_type = data.get('ticket_type', 'question')
    
    # Создаём тикет в базе данных с фото
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
        reply_markup=get_main_menu_keyboard(),
        parse_mode="Markdown"
    )
    
    # Уведомляем администраторов о новом тикете
    await notify_admins_new_ticket(message.bot, ticket_id, message.from_user.id, ticket_type, ticket_text, photo_file_id)


@router.message(TicketStates.waiting_for_message, F.text)
async def process_ticket_message(message: Message, state: FSMContext):
    """Обработка текста тикета"""
    ticket_text = message.text.strip()
    
    if len(ticket_text) < 10:
        await message.answer(
            f"{EMOJI['warning']} Сообщение слишком короткое! "
            f"Опишите проблему подробнее (минимум 10 символов).",
            parse_mode="Markdown"
        )
        return
    
    if len(ticket_text) > 2000:
        await message.answer(
            f"{EMOJI['warning']} Сообщение слишком длинное! "
            f"Максимум 2000 символов.",
            parse_mode="Markdown"
        )
        return
    
    data = await state.get_data()
    ticket_type = data.get('ticket_type', 'question')
    
    # Создаём тикет в базе данных
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
        f"{EMOJI['clock']} Ожидайте ответа от администрации.\n"
        f"Вам придёт уведомление, когда на тикет ответят.",
        reply_markup=get_main_menu_keyboard(),
        parse_mode="Markdown"
    )
    
    # Уведомляем администраторов о новом тикете
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
    
    # Объединяем админов и модераторов
    admin_ids = set(ADMIN_IDS + MODERATOR_IDS)
    
    for admin_id in admin_ids:
        try:
            if photo_file_id:
                # Отправляем фото с подписью
                await bot.send_photo(
                    admin_id,
                    photo=photo_file_id,
                    caption=notification_text,
                    reply_markup=get_ticket_admin_keyboard(ticket_id, has_photo=True),
                    parse_mode="Markdown"
                )
            else:
                # Отправляем только текст
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
    
    # Проверяем права
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
    
    # Отправляем фото
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
    """Начать ответ на тикет"""
    ticket_id = int(callback.data.split(":")[2])
    
    # Проверяем права
    if not await db.is_user_moderator(callback.from_user.id):
        await callback.answer("У вас нет прав для ответа на тикеты!", show_alert=True)
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
    """Обработка ответа на тикет"""
    reply_text = message.text.strip()
    
    if len(reply_text) < 5:
        await message.answer(
            f"{EMOJI['warning']} Ответ слишком короткий!",
            parse_mode="Markdown"
        )
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
    
    # Сохраняем ответ
    await db.respond_to_ticket(ticket_id, reply_text, message.from_user.id)
    
    await state.clear()
    
    await message.answer(
        f"{EMOJI['check']} *Ответ на тикет #{ticket_id} отправлен!*",
        parse_mode="Markdown"
    )
    
    # Уведомляем пользователя
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
            f"💬 *Ответ от {admin_name}:*\n{reply_text}",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.warning(f"Failed to notify user about ticket reply: {e}")


@router.callback_query(F.data.startswith("ticket:close:"))
async def close_ticket_handler(callback: CallbackQuery):
    """Закрыть тикет"""
    ticket_id = int(callback.data.split(":")[2])
    
    # Проверяем права
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
    
    # Определяем, текстовое это сообщение или фото
    if callback.message.photo:
        # Сообщение с фото - редактируем caption
        current_caption = callback.message.caption or ""
        await callback.message.edit_caption(
            caption=current_caption + f"\n\n{EMOJI['check']} *Тикет закрыт*",
            parse_mode="Markdown"
        )
    else:
        # Текстовое сообщение
        current_text = callback.message.text or ""
        await callback.message.edit_text(
            current_text + f"\n\n{EMOJI['check']} *Тикет закрыт*",
            parse_mode="Markdown"
        )
    await callback.answer("Тикет закрыт!")
    
    # Уведомляем пользователя
    try:
        await callback.bot.send_message(
            ticket['user_id'],
            f"📩 *Тикет #{ticket_id} закрыт*\n\n"
            f"Ваше обращение было рассмотрено и закрыто.\n"
            f"Если у вас остались вопросы, создайте новый тикет.",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.warning(f"Failed to notify user about ticket close: {e}")