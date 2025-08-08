import os

from aiogram import Bot
from aiogram.types import File

from config import config
from services.bot_notifier import notify_admin


async def download_file(bot: Bot, file_id: str, file_name: str, user_id: int):
    '''
    Скачивает файл и возвращает путь
    '''

    try:
        os.makedirs('/usr/src/receipts', exist_ok=True)
        dest_path = f"/usr/src/receipts/{user_id}_{file_name}"

        await bot.download(file_id, destination=dest_path)

        return dest_path

    except Exception as e:
        await notify_admin(message=f"ПРИ ЗАГРУЗКЕ: {str(e)}")
