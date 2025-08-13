from sqlalchemy.ext.asyncio import AsyncSession

from aiogram import F, Bot, Router, types
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database.models import Product
from database.orm_query import orm_change_banner_image, orm_create_orders, orm_delete_orders, orm_get_info_pages, orm_neo_banner
from filters.chat_types import ChatTypeFilter, IsAdmin
from keybds.reply import get_keyboard
from services.bot_notifier import OrderCallback, notify_user
from services.storage import Storage


admin_router = Router()
admin_router.message.filter(ChatTypeFilter(['private']), IsAdmin())


SERVICE_KB = get_keyboard(
    'Добавить/изменить баннер', 'Новый баннер',
    # 'chat',
    # request_chat=2,   ### порядковый номер кнопки по счёту от 0
    placeholder='Выберите действие',
    sizes=(2, ),
)

@admin_router.message(F.chat_shared)
async def get_chat(message: types.Message, bot: Bot):
    '''Позволяет выбрать чат и получить его id.'''

    await bot.send_message(chat_id=844168645, text=str(message.chat_shared.chat_id))

@admin_router.message(Command('сервис'))
async def banner_menu(message: types.Message):
    '''Первое, что нужно сделать при первом запуске бота.\n
    Меню позволяет прикрепить изображения для страниц.\n
    Возвращает Reply кнопки с командами 'Добавить/изменить баннер', 'Новый баннер'.'''
    await message.answer('Что хотите сделать?', reply_markup=SERVICE_KB)

################# Микро FSM для загрузки/изменения баннеров ############################

class AddBanner(StatesGroup):
    image = State()

# Отправляем перечень информационных страниц бота и становимся в состояние отправки photo
@admin_router.message(StateFilter(None), F.text == 'Добавить/изменить баннер')
async def add_banner_0(message: types.Message, state: FSMContext, session: AsyncSession):
    pages_names = [page.name for page in await orm_get_info_pages(session)]
    await message.answer(f"Отправьте фото баннера.\nВ описании укажите для какой страницы:\
                         \n{', '.join(pages_names)}")
    await state.set_state(AddBanner.image)

# Добавляем/изменяем изображение в таблице (там уже есть записанные страницы по именам:
# main, catalog, about
@admin_router.message(AddBanner.image, F.photo)
async def add_banner_1(message: types.Message, state: FSMContext, session: AsyncSession):
    image_id = message.photo[-1].file_id
    for_page = message.caption.strip().lower()
    pages_names = [page.name for page in await orm_get_info_pages(session)]
    if for_page not in pages_names:
        await message.answer(f"Введите нормальное название страницы, например:\
                         \n{', '.join(pages_names)}")
        return
    await orm_change_banner_image(session, for_page, image_id,)
    await message.answer('Баннер добавлен/изменен.')
    await state.clear()

# ловим некоррекный ввод
@admin_router.message(AddBanner.image)
async def add_banner_2(message: types.Message):
    await message.answer('Отправьте фото баннера или отмена')

################# Микро FSM для добавлеения новых баннеров ############################

class NeoBanner(StatesGroup):
    name = State()
    image = State()
    description = State()

    messages_ids: list[int] = []

@admin_router.message(StateFilter(None), F.text == 'Новый баннер')
async def neo_banner_0(message: types.Message, state: FSMContext, session: AsyncSession):
    '''Встаём в состояние ожидания image'''
    NeoBanner.messages_ids.append(message.message_id)
    pages_names = [page.name for page in await orm_get_info_pages(session)]

    mssg = await message.answer(f"Занятые имена:\n{', '.join(pages_names)}\n\
Отправьте изображение баннера с названием в подписи из списка\nstart, neo_product, categories, neo_category, users, orders", 
                                        reply_markup=types.ReplyKeyboardRemove()
                                        )
    NeoBanner.messages_ids.append(mssg.message_id)

    await state.set_state(NeoBanner.image)

@admin_router.message(NeoBanner.image, F.photo)
async def neo_banner_image(message: types.Message, state: FSMContext):
    '''Ловим значение image и name и встаём в состояние ожидания description'''
    image_id = message.photo[-1].file_id
    name_mssg = message.caption.strip().lower()
    name_list = ['start', 'neo_product', 'categories', 'neo_category', 'users', 'orders']
    if name_mssg in name_list:
        NeoBanner.messages_ids.append(message.message_id)
        await state.update_data(name=name_mssg)
        await state.update_data(image=image_id)
        mssg = await message.answer('Отправьте описание баннера')
        NeoBanner.messages_ids.append(mssg.message_id)
        await state.set_state(NeoBanner.description)
    else:
        mssg = await message.answer('Неверное название баннера!\n\n\
Отправьте изображение баннера с названием в подписи из списка\nstart, neo_product, categories, neo_category, users, orders')
        NeoBanner.messages_ids.append(mssg.message_id)
        await message.delete()
    
@admin_router.message(NeoBanner.image)
async def uncorrect_banner_image(message: types.Message):
    '''Хендлер для отлова некорректного ввода для состояния image'''
    mssg = await message.answer('Получены недопустимые данные!\n\n\
Отправьте изображение баннера с названием в подписи из списка\nstart, neo_product, categories, neo_category, users, orders')
    NeoBanner.messages_ids.append(mssg.message_id)
    await message.delete()

@admin_router.message(NeoBanner.description, F.text)
async def neo_banner_description(message: types.Message, state: FSMContext, session: AsyncSession, bot: Bot):
    '''Ловим значение description и записываем новый баннер в БД'''
    await state.update_data(description=message.text)
    NeoBanner.messages_ids.append(message.message_id)
    data = await state.get_data()
    try:
        await orm_neo_banner(session, data)
        await message.answer(f"Новый баннер {data['name']} добавлен", reply_markup=SERVICE_KB)
    except Exception as err:
        await message.answer(
            f"Ошибка:\n{str(err)}\nОбратись к программисту, он опять денег хочет",
            reply_markup=SERVICE_KB)
    await state.clear()
    await bot.delete_messages(chat_id=message.chat.id, message_ids=NeoBanner.messages_ids)
    NeoBanner.messages_ids.clear()

@admin_router.message(NeoBanner.description)
async def uncorrect_banner_description(message: types.Message):
    '''Хендлер для отлова некорректного ввода для состояния description'''
    mssg = await message.answer('Отправьте описание баннера')
    NeoBanner.messages_ids.append(mssg.message_id)
    await message.delete()


@admin_router.callback_query(OrderCallback.filter())
async def handle_admin_decision(callback: types.CallbackQuery, callback_data: OrderCallback, session: AsyncSession):
    '''Обработчик решения администратора'''
    user_state = Storage.get_state(callback_data.user_id)
    expected_amount = user_state.get('order_amount')

    if callback_data.verify == 'accept':
        try:
            await orm_create_orders(session, callback_data.user_id)
            await notify_user(
                callback_data.chat_id,
                f"✅ Администратор подтвердил платёж\n\nВаш заказ на сумму {expected_amount:2f}₽ принят."
            )
        except Exception as e:
            await callback.answer(str(e), show_alert=True)

    elif callback_data.verify == 'reject':
        await notify_user(
            callback_data.chat_id,
            '❌ Администратор отклонил чек.\n\nПожалуйста, проверьте правильность чека и отправьте его снова.'
        )

    elif callback_data.verify == 'delete':
        try:
            await orm_delete_orders(session, callback_data.user_id, expected_amount)
            await notify_user(
                callback_data.chat_id,
                '❌ Администратор удалил заказ.\n\nПожалуйста, не мухлюйте с чеками!'
            )
        except Exception as e:
            await callback.answer(str(e), show_alert=True)

    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)
