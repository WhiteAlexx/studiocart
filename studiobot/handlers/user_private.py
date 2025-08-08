import asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from aiogram import F, Bot, types, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from common.constants import order_alert
from database.orm_query import orm_add_to_cart, orm_add_user, orm_change_cart, orm_create_orders, orm_get_product
from filters.chat_types import ChatTypeFilter
from handlers.user_menu_prcssng import get_menu_content, product_menu
from keybds.inline import MenuCallback, get_callback_btns
from services.storage import Storage
from tasks.celery_tasks import process_receipt
from utils.file_utils import download_file
from utils.service import parse_count


user_private_router = Router()
user_private_router.message.filter(ChatTypeFilter(['private']))


@user_private_router.message(CommandStart())
async def start_cmd(message: types.Message, session: AsyncSession):

    user = message.from_user
    await orm_add_user(
        session,
        user_id=user.id,
        first_name=user.first_name,
        last_name=user.last_name,
        user_name=user.username,
    )

    media, reply_markup = await get_menu_content(session, level=0, menu_name='main')

    await message.answer_photo(media.media, caption=media.caption, reply_markup=reply_markup)


class Quant(StatesGroup):
    add_quant = State()
    cng_quant = State()

    message_id: int | None
    chat_id: int | None
    messages_ids: list[int] = []
    product = None
    callback_data = None


@user_private_router.callback_query(MenuCallback.filter(F.menu_name=='add_to_cart'))
async def add_to_cart(callback: types.CallbackQuery, callback_data: MenuCallback, state: FSMContext, session: AsyncSession):

    Quant.message_id=callback.message.message_id
    Quant.chat_id=callback.message.chat.id

    user_id = callback.from_user.id
    product = await orm_get_product(session, product_id=callback_data.product_id)
    if product.unit == 'шт':
        try:
            await orm_add_to_cart(
                session, user_id=user_id, product_id=callback_data.product_id, quantity=1
            )
            await callback.answer('Товар добавлен в корзину')
        except ValueError:
            await callback.answer('❗Нельзя заказать больше наличия❗', show_alert=True)
    else:
        if product.quantity <= 0:
            await callback.answer('❗Товар кончился❗', show_alert=True)
        elif product.quantity <= 1.2:
            try:
                await orm_add_to_cart(
                    session, user_id=user_id, product_id=callback_data.product_id, quantity=product.quantity
                )
                await callback.answer('Товар добавлен в корзину')
            except ValueError:
                await callback.answer('❗Нельзя заказать больше наличия❗', show_alert=True)
        else:
            mssg = await callback.message.answer(
'Введите метраж (в см или м, <b><u>например 65см или 0,65м</u></b>):'
            )
            await callback.answer()
            Quant.messages_ids.append(mssg.message_id)
            Quant.product = product
            Quant.callback_data = callback_data
            await state.set_state(Quant.add_quant)

    media, reply_markup = await get_menu_content(
        session,
        level=callback_data.level,
        menu_name=callback_data.menu_name,
        parent_id=callback_data.parent_id,
        category=callback_data.category,
        page=callback_data.page,
        product_id=callback_data.product_id,
        user_id=callback.from_user.id
    )

    await callback.message.edit_media(media=media, reply_markup=reply_markup)


@user_private_router.message(Quant.add_quant, F.text)
async def get_add_count(message: types.Message, state: FSMContext, session: AsyncSession, bot: Bot):

    Quant.messages_ids.append(message.message_id)

    success, result = await parse_count(message.text)

    if success:
        user_id = message.from_user.id
        product = Quant.product

        if result > product.quantity:
            mssg = await message.answer('<b>❗Нельзя заказать больше наличия❗</b>')
            Quant.messages_ids.append(mssg.message_id)
        else:
            await orm_add_to_cart(session, user_id=user_id, product_id=product.id, quantity=result)

            await state.clear()
            await bot.delete_messages(chat_id=message.chat.id, message_ids=Quant.messages_ids)
            Quant.messages_ids.clear()
            Quant.product = None

            mssg = await message.answer(text='Товар добавлен в корзину')
            await asyncio.sleep(1.5)
            await bot.delete_message(chat_id=message.chat.id, message_id=mssg.message_id)

            data = Quant.callback_data
            media, reply_markup = await get_menu_content(
                session,
                level=data.level,
                menu_name=data.menu_name,
                parent_id=data.parent_id,
                category=data.category,
                page=data.page,
                product_id=data.product_id,
                user_id=message.from_user.id
            )

            await bot.edit_message_media(
                media=media, chat_id=Quant.chat_id, message_id=Quant.message_id, reply_markup=reply_markup
            )
    else:
        mssg = await message.answer(result)
        Quant.messages_ids.append(mssg.message_id)


@user_private_router.callback_query(MenuCallback.filter(F.menu_name=='change_m'))
async def get_change_count(callback: types.CallbackQuery, callback_data: MenuCallback, state: FSMContext, session: AsyncSession):

    Quant.message_id=callback.message.message_id
    Quant.chat_id=callback.message.chat.id

    product = await orm_get_product(session, product_id=callback_data.product_id)

    mssg = await callback.message.answer('Введите новый метраж (в см или м, <b><u>например 65см или 0,65м</u></b>):')

    await callback.answer()
    Quant.messages_ids.append(mssg.message_id)
    Quant.product = product
    Quant.callback_data = callback_data
    await state.set_state(Quant.cng_quant)


@user_private_router.message(Quant.cng_quant, F.text)
async def get_cng_count(message: types.Message, state: FSMContext, session: AsyncSession, bot: Bot):

    Quant.messages_ids.append(message.message_id)

    success, result = await parse_count(message.text)

    if success:
        user_id = message.from_user.id
        product = Quant.product

        try:
            await orm_change_cart(session, user_id=user_id, product_id=product.id, quantity=result)

            await state.clear()
            await bot.delete_messages(chat_id=message.chat.id, message_ids=Quant.messages_ids)
            Quant.messages_ids.clear()
            Quant.product = None

            mssg = await message.answer(text='Количество товара в корзине изменено')
            await asyncio.sleep(1.5)
            await bot.delete_message(chat_id=message.chat.id, message_id=mssg.message_id)

            data = Quant.callback_data
            media, reply_markup = await get_menu_content(
                session,
                level=data.level,
                menu_name=data.menu_name,
                parent_id=data.parent_id,
                category=data.category,
                page=data.page,
                product_id=data.product_id,
                user_id=message.from_user.id
            )

            await bot.edit_message_media(
                media=media, chat_id=Quant.chat_id, message_id=Quant.message_id, reply_markup=reply_markup
            )

        except ValueError:
            mssg = await message.answer(text='<b>❗Нельзя заказать больше наличия❗</b>')
            await asyncio.sleep(1.5)
            await bot.delete_message(chat_id=message.chat.id, message_id=mssg.message_id)

    else:
        mssg = await message.answer(result)
        Quant.messages_ids.append(mssg.message_id)


@user_private_router.message(Quant.add_quant)
@user_private_router.message(Quant.cng_quant)
async def uncorrect_count(message: types.Message, state: FSMContext):
    mssg = await message.answer('<b>❗Введены некорректные данные❗</b>\n\n\
Введите метраж (в см или м, <b><u>например 65см или 0,65м</u></b>):')
    Quant.messages_ids.append(mssg.message_id)
    await message.delete()


class Payment(StatesGroup):
    pay_mess = State()

    message_id: int | None
    chat_id: int | None
    callback_data = None


@user_private_router.callback_query(MenuCallback.filter(F.menu_name=='payment'))
async def payment(callback: types.CallbackQuery, callback_data: MenuCallback, state: FSMContext, session: AsyncSession):

    Payment.message_id=callback.message.message_id
    Payment.chat_id=callback.message.chat.id
    Payment.callback_data = callback_data

    await callback.answer('❗Отправьте скриншот чека или pdf-файл❗', show_alert=True)
    await state.set_state(Payment.pay_mess)


@user_private_router.message(Payment.pay_mess, (F.document) | (F.photo))
async def send_pay_mess(message: types.Message, state: FSMContext, session: AsyncSession, bot: Bot):

    if message.document:
        file_id = message.document.file_id
        file_name = message.document.file_name
    elif message.photo:
        file_id = message.photo[-1].file_id
        file_name = f"{message.photo[-1].file_unique_id}.jpg"
    else:
        mssg = await message.answer('❗Отправьте скриншот чека или pdf-файл❗')
        await asyncio.sleep(2)
        await message.delete()
        await asyncio.sleep(2)
        await bot.delete_message(chat_id=message.chat.id, message_id=mssg.message_id)
        return

    file_path = await download_file(bot, file_id, file_name, message.from_user.id)

    user_state = Storage.get_state(message.from_user.id)

    mssg = await message.answer('🔍 Начинаем проверку чека...\n\n⏳ Ожидайте уведомление, когда проверка будет завершена')

    process_receipt.delay(
        file_path=file_path,
        expected_amount=user_state.get('order_amount'),
        user_id=message.from_user.id,
        chat_id=message.chat.id,
        file_id=file_id,
    )

    Storage.save_state(message.from_user.id, {
        **user_state,
        'processing': True,
        'processing_file': file_path,
    })

    media, reply_markup = await get_menu_content(
        session,
        level=0,
        menu_name='main',
    )

    await bot.edit_message_media(
        media=media, chat_id=Payment.chat_id, message_id=Payment.message_id, reply_markup=reply_markup
    )

    await asyncio.sleep(2)
    await bot.delete_message(chat_id=message.chat.id, message_id=mssg.message_id)

    if message.document:
        await bot.send_document(
            document=message.document.file_id, caption='Новый заказ', chat_id=-1002146117897
        )
    if message.photo:
        await bot.send_photo(
            photo=message.photo[-1].file_id, caption='Новый заказ', chat_id=-1002146117897
        )

    await message.delete()
    await state.clear()

@user_private_router.message(Payment.pay_mess)
async def unsend_pay_mess(message: types.Message, state: FSMContext, bot: Bot):

    mssg = await message.answer('❗Отправьте скриншот чека или pdf-файл❗')
    await asyncio.sleep(2)
    await message.delete()
    await asyncio.sleep(2)
    await bot.delete_message(chat_id=message.chat.id, message_id=mssg.message_id)



@user_private_router.callback_query(MenuCallback.filter())
async def user_menu(callback: types.CallbackQuery, callback_data: MenuCallback, session: AsyncSession):

    if callback_data.menu_name == 'value_error':
        await callback.answer('❗Нельзя заказать больше наличия❗', show_alert=True)

    if callback_data.menu_name == 'order':
        await callback.answer(order_alert, show_alert=True)

    media, reply_markup = await get_menu_content(
        session,
        level=callback_data.level,
        menu_name=callback_data.menu_name,
        parent_id=callback_data.parent_id,
        category=callback_data.category,
        page=callback_data.page,
        product_id=callback_data.product_id,
        user_id=callback.from_user.id
    )

    if isinstance(media, tuple):
        img_lst, caption = media

        for img in img_lst:
            await callback.message.edit_media(media=types.InputMediaPhoto(media=img, caption=caption), reply_markup=reply_markup)
            await callback.answer('Ожидайте...⏳')
            await asyncio.sleep(0.1)

    else:
        await callback.message.edit_media(media=media, reply_markup=reply_markup)
        await callback.answer()
        await callback.message.edi
