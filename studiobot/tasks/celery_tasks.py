import os
import json

import asyncio
from celery import Celery
from sqlalchemy.ext.asyncio import AsyncSession

from config import config
from database.engine import session_maker
from database.orm_query import orm_create_orders
from services.bot_notifier import notify_admin, notify_user
from services.receipt_processor import extract_text, validate_receipt
from services.storage import Storage


celery = Celery('tasks', broker=config.CELERY_BROKER)
celery.conf.update(
    task_serializer='json',
    result_serializer='json',
    task_track_started=True,
    task_ignore_result=True,
    task_always_eager=False,
    broker_connection_retry_on_startup=True,
)

event_loop = None

def get_or_create_eventloop():

    global event_loop
    if event_loop is None:
        event_loop = asyncio.new_event_loop()
    return event_loop


async def async_create_order(session: AsyncSession, user_id: int):

    try:
        await orm_create_orders(session, user_id)
        return True

    except Exception as e:
        print(str(e))
        return False


async def async_process_receipt(file_path: str, user_id: int, chat_id: int, expected_amount: float, file_id: str):

    try:
        receipt_text = extract_text(file_path)
        print(receipt_text)

        validation = validate_receipt(receipt_text, expected_amount)
        print(validation)

        async with session_maker() as session:

            if validation['valid']:
                success = await async_create_order(session, user_id)

                if success:
                    await notify_user(
                        chat_id,
                        '✅ Платёж подтверждён.\nЗаказ принят в обработку.'
                    )
                    await notify_admin(
                        file_path=file_path,
                        validation=validation,
                        expected_amount=expected_amount,
                        user_id=user_id,
                        chat_id=chat_id,
                        file_id=file_id,
                    )

                else:
                    await notify_user(
                        chat_id,
                        '⚠️ Произошла ошибка при создании заказа.\n'
                        'Администратор уже уведомлён, ожидайте связи в ближайшее время.'
                    )
                    await notify_admin(
                        user_id=user_id,
                        chat_id=chat_id,
                        message='❌ Ошибка создания заказа после успешной оплаты\n'
                        f"Пользователь: {user_id}\nСумма: {expected_amount:2f}₽"
                    )

            else:
                verification_id = f"verify_{user_id}_{os.path.basename(file_path)}"
                Storage.save_verification(verification_id, {
                    'user_id': user_id,
                    'chat_id': chat_id,
                    'file_path': file_path,
                    'expected_amount': expected_amount,
                    'validation': json.dumps(validation)
                })
                
                try:
                    await notify_user(
                        chat_id,
                        '🔍 Чек отправлен на дополнительную проверку.\n\n⏳ Ожидайте подтверждение администратора.\n\n\
‼️ Пожалуйста, не меняйте состав корзины до окончания проверки ‼️'
                    )
                    await notify_admin(
                        file_path=file_path,
                        validation=validation,
                        expected_amount=expected_amount,
                        user_id=user_id,
                        chat_id=chat_id,
                        file_id=file_id,
                    )

                except Exception as e:
                    print(str(e))
                    await notify_user(
                        chat_id,
                        '⚠️ Произошла ошибка при обработке чека.\n'
                        'Администратор уже уведомлён, ожидайте связи в ближайшее время.'
                    )
                    await notify_admin(
                        user_id=user_id,
                        chat_id=chat_id,
                        message=f"❌ Ошибка обработки чека.\nПользователь: {user_id}"
                    )

    except Exception as e:
        print(str(e))
        await notify_user(
            chat_id,
            '⚠️ Произошла критическая ошибка при обработке чека.\n'
            'Администратор уже уведомлён, ожидайте связи в ближайшее время.'
        )
        await notify_admin(
            user_id=user_id,
            chat_id=chat_id,
            message=f"🔥 Критическая ошибка обработки чека.\nПользователь: {user_id}"
        )

    # finally:
    #     try:
    #         if os.path.exists(file_path):
    #             os.remove(file_path)
    #     except:
    #         pass


@celery.task(name='process_receipt')
def process_receipt(file_path: str, expected_amount: float, user_id: int, chat_id: int, file_id: str):

    loop = get_or_create_eventloop()

    if loop.is_closed():
        global event_loop
        event_loop = asyncio.new_event_loop()
        loop = event_loop
        asyncio.set_event_loop(loop)

    if not loop.is_running():
        loop.run_until_complete(
            async_process_receipt(file_path, user_id, chat_id, expected_amount, file_id)
        )
    else:
        asyncio.run_coroutine_threadsafe(
            async_process_receipt(file_path, user_id, chat_id, expected_amount, file_id),
            loop
        )

    # asyncio.run(async_process_receipt(file_path, user_id, chat_id, expected_amount, file_id))
