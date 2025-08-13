import asyncio
import os

from PIL import Image

from aiogram import Bot
from aiogram.types import FSInputFile

from database.redis_cli import redis_client
from config import config
from services.bot_notifier import notify_admin


async def download_file(bot: Bot, file_id: str, dest: str, file_name: str = None, user_id: int = None):
    '''
    Скачивает файл и возвращает путь
    '''

    dest_path = ''

    if dest == 'receipts':
        dest_path = os.path.join(config.RECEIPTS_DIR, f"{user_id}_{file_name}")
        os.makedirs(config.RECEIPTS_DIR, exist_ok=True)
    elif dest == 'collage':
        dest_path = os.path.join(config.COLLAGE_DIR, f"{file_id}.jpg")

    try:
        await bot.download(file=file_id, destination=dest_path)

        return dest_path

    except Exception as e:
        await notify_admin(message=f"ПРИ ЗАГРУЗКЕ: {str(e)}")


ROWS_LAYOUT = {
    2: [1, 1],
    3: [2, 1],
    4: [2, 2],
    5: [3, 2],
    6: [2, 2, 2],
    7: [3, 2, 2],
    8: [3, 3, 2],
    9: [3, 3, 3]
}
BORDER_SIZE = 5


async def create_collage(bot: Bot, image_paths, collage_path, collage_key):

    # Проверка кеша Redis
    if cached_file_id := redis_client.get(collage_key):
        return cached_file_id.decode()

    n = len(image_paths)
    layout = ROWS_LAYOUT[n]
    row_height = 2400 // len(layout)
    
    # Асинхронная обработка одного изображения
    async def process_image(img_path, inner_width, inner_height):
        # Используем to_thread для CPU-bound операций
        return await asyncio.to_thread(
            _process_image_sync, 
            img_path, 
            inner_width, 
            inner_height
        )
    
    # Синхронная обработка изображения
    def _process_image_sync(img_path, inner_width, inner_height):
        with Image.open(img_path) as img:
            width_ratio = inner_width / img.width
            height_ratio = inner_height / img.height
            ratio = max(width_ratio, height_ratio)
            new_width = int(img.width * ratio)
            new_height = int(img.height * ratio)
            img = img.resize((new_width, new_height), Image.LANCZOS)
            left = (new_width - inner_width) // 2
            top = (new_height - inner_height) // 2
            return img.crop((left, top, left + inner_width, top + inner_height))
    
    # Параллельная обработка изображений
    tasks = []
    img_index = 0
    
    # Сначала определяем размеры для каждого изображения
    for row_idx, cols_in_row in enumerate(layout):
        col_width = 1800 // cols_in_row
        inner_width = col_width - 2 * BORDER_SIZE
        inner_height = row_height - 2 * BORDER_SIZE
        
        for _ in range(cols_in_row):
            tasks.append(process_image(
                image_paths[img_index], 
                inner_width,
                inner_height
            ))
            img_index += 1
    
    # Выполняем все задачи параллельно
    processed_images = await asyncio.gather(*tasks)
    
    # Создаем коллаж
    collage = Image.new('RGB', (1800, 2400), (255, 255, 255))
    img_index = 0
    
    for row_idx, cols_in_row in enumerate(layout):
        col_width = 1800 // cols_in_row
        y_offset = row_idx * row_height
        
        for col_idx in range(cols_in_row):
            x_offset = col_idx * col_width
            paste_x = x_offset + BORDER_SIZE
            paste_y = y_offset + BORDER_SIZE
            
            collage.paste(processed_images[img_index], (paste_x, paste_y))
            
            # Удаляем исходный файл
            if os.path.exists(image_paths[img_index]):
                os.remove(image_paths[img_index])
            
            img_index += 1
    
    collage.save(collage_path, quality=95)

    # Отправляем коллаж и получаем file_id
    try:
        mssg = await bot.send_photo(chat_id=config.COLLAGE_CHAT_ID, photo=FSInputFile(collage_path))

        redis_client.set(collage_key, mssg.photo[-1].file_id, ex=7*24*3600)  # Кеш на 7 дней

        await bot.delete_message(chat_id=config.COLLAGE_CHAT_ID, message_id=mssg.message_id)

        if os.path.exists(collage_path):
            os.remove(collage_path)

        return mssg.photo[-1].file_id

    except Exception as e:
        await notify_admin(message=f"ПРИ КОЛЛАЖЕ {str(e)}")
