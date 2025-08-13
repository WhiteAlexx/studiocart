import asyncio
from os import environ

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from database.engine import create_db, drop_db, session_maker, create_table_orders
from handlers.admin_private import admin_router
from handlers.user_private import user_private_router
from handlers.user_group import user_group_router
from middlewares.db import DataBaseSession


bot = Bot(token='7683870154:AAFVtIjPdNf_HQEnAuxgZJEdUd4Hy_WPzok',
          default=DefaultBotProperties(parse_mode=ParseMode.HTML)
          )
bot.my_admins_list = [844168645]

dp = Dispatcher()

dp.include_routers(
    admin_router,
    user_private_router,
    user_group_router,
)


async def on_startup(bot):
    run_param = False
    if run_param:
        await drop_db()
    await create_db()
    # await add_user_name_column()


async def on_shutdown(bot):
    print('БОТ ОТДЫХАЕТ')


async def main():

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    dp.update.middleware(DataBaseSession(session_pool=session_maker))

    print('БОТ СТАРТОВАЛ')
    await bot.delete_webhook(drop_pending_updates=True)
    # await bot.delete_my_commands(scope=types.BotCommandScopeAllPrivateChats())
    # await bot.set_my_commands(commands=private, scope=types.BotCommandScopeAllPrivateChats())
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


asyncio.run(main())
