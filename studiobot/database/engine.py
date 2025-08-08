from os import environ

import asyncpg

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from common.constants import categories, description_for_info_pages
from database.models import Base
from database.orm_query import orm_add_banner_description, orm_create_categories


engine = create_async_engine('postgresql+asyncpg://bot:bot@db:5432/bot', echo=True)
# engine = create_async_engine('postgresql+asyncpg://bot:bot@localhost:5432/bot', echo=True)

session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


async def create_table_orders():
    conn = await asyncpg.connect(
        user='bot',
        password='bot',
        database='bot',
        host='localhost',
    )
    try:
        await conn.execute('''
            CREATE TABLE orders (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                product VARCHAR(50) NOT NULL,
                quantity NUMERIC(5,2) NOT NULL,
                cost NUMERIC(7,2) NOT NULL,
                FOREIGN KEY (user_id) REFERENCES "user" (user_id) ON DELETE CASCADE
            );
        ''')
        print('Таблица orders успешно добавлена!')
    except Exception as e:
        print(f"ОШИБКА: {e}")
    finally:
        await conn.close()


async def create_db():
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
        await conn.run_sync(Base.metadata.create_all)
        
    async with session_maker() as session:
        await orm_create_categories(session, categories)
        await orm_add_banner_description(session, description_for_info_pages)


async def drop_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
