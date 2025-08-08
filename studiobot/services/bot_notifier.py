import os
import logging

import asyncio

from aiogram import Bot
from aiogram.filters.callback_data import CallbackData
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import config


logger = logging.getLogger(__name__)

bot = Bot(token=config.BOT_TOKEN)

class OrderCallback(CallbackData, prefix='order'):
    verify: str
    user_id: int
    chat_id: int


async def notify_user(chat_id: int, message: str):
    '''Асинхронно уведомляет пользователя'''

    try:
        mssg = await bot.send_message(chat_id, message)

        await asyncio.sleep(2)
        await bot.delete_message(chat_id=chat_id, message_id=mssg.message_id)

    except Exception as e:
        logger.error(f"Ошибка отправки уведомления пользователю {chat_id}: {str(e)}")


async def notify_admin(
    file_path: str = None,
    validation: dict = None,
    expected_amount: float = None,
    user_id: int = None,
    chat_id: int = None,
    message: str = None,
    file_id: str = None
):
    '''Асинхронно уведомляет администратора'''

    try:
        if message:
            # Простое текстовое уведомление
            for admin_id in config.ADMIN_ID:
                await bot.send_message(admin_id, message)
            return

        # Формируем информацию для администратора
        user_info = (
            f"👤 Пользователь: ID {user_id}\n"
            f"💳 Сумма заказа: {expected_amount:.2f}₽\n"
            "Результат автоматической проверки:\n" + 
            "\n".join(validation['details'])
        )

        # Отправляем файл администратору
        for admin_id in config.ADMIN_ID:

            # Создаем клавиатуру для администратора
            keyboard = InlineKeyboardBuilder()

            keyboard.button(text="✅ Принять",
                    callback_data=OrderCallback(verify='accept', user_id=user_id, chat_id=chat_id))
            if validation['valid']:
                keyboard.button(text="❌ Удалить",
                        callback_data=OrderCallback(verify='delete', user_id=user_id, chat_id=chat_id))
            else:
                keyboard.button(text="❌ Отклонить",
                        callback_data=OrderCallback(verify='reject', user_id=user_id, chat_id=chat_id))

            if file_path and os.path.exists(file_path):
                if file_path.endswith('.pdf'):
                    msg = await bot.send_document(
                        admin_id,
                        file_id,
                        caption=user_info + '\n\n❗️ПРОВЕРЬТЕ ЧЕК И ВЫБЕРИТЕ ДЕЙСТВИЕ❗️',
                        reply_markup=keyboard.as_markup()
                    )
                else:
                    msg = await bot.send_photo(
                        admin_id,
                        file_id,
                        caption=user_info + '\n\n❗️ПРОВЕРЬТЕ ЧЕК И ВЫБЕРИТЕ ДЕЙСТВИЕ❗️',
                        reply_markup=keyboard.as_markup()
                    )
            else:
                msg = await bot.send_message(admin_id, user_info)

    except Exception as e:
        logger.error(f"Ошибка уведомления администратора: {str(e)}")
