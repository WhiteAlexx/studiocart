from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.orm_query import orm_get_product


class MenuCallback(CallbackData, prefix='menu'):
    level: int
    menu_name: str
    parent_id: int | None = None
    category: int | None = None
    page: int = 1
    product_id: int | None = None


def get_user_main_btns(*, level: int, sizes: tuple[int] = (2,)):
    keyboard = InlineKeyboardBuilder()
    btns = {
        'Заказы 💰': 'orders',
        'Корзина 🛒': 'cart',
        'Товары 🛍': 'catalog',
    }
    for text, menu_name in btns.items():
        if menu_name == 'orders':
            keyboard.add(InlineKeyboardButton(text=text,
                    callback_data=MenuCallback(level=6, menu_name=menu_name).pack()))
        elif menu_name == 'cart':
            keyboard.button(text=text,
                    callback_data=MenuCallback(level=4, menu_name=menu_name).pack())
        elif menu_name == 'catalog':
            keyboard.add(InlineKeyboardButton(text=text,
                    callback_data=MenuCallback(level=level+1, menu_name=menu_name).pack()))
        else:
            keyboard.button(text=text,
                    callback_data=MenuCallback(level=level, menu_name=menu_name))

    return keyboard.adjust(*sizes).as_markup()


def get_user_catalog_btns(*, level: int, categories: list, sizes: tuple[int] = (2,)):
    keyboard = InlineKeyboardBuilder()

    keyboard.button(text='На главную ↖️',
            callback_data=MenuCallback(level=level-1, menu_name='main'))
    keyboard.button(text='Корзина 🛒',
            callback_data=MenuCallback(level=4, menu_name='cart'))

    for cat in categories:
        if not cat.children:
            keyboard.button(text=cat.name,
                    callback_data=MenuCallback(level=level+1, menu_name='products_list', category=cat.id))
        else:
            keyboard.button(text=cat.name,
                    callback_data=MenuCallback(level=level, menu_name=cat.name, parent_id=cat.id))


    return keyboard.adjust(*sizes).as_markup()


def get_products_list_btns(
    *,
    level: int,
    category: int,
    page: int,
    products_btns: dict,
    paginations_btns: dict,
    sizes: tuple[int] = (2, )
):

    keyboard = InlineKeyboardBuilder()

    keyboard.button(text='К категориям ↖️',
            callback_data=MenuCallback(level=level-1, menu_name='catalog'))
    keyboard.button(text='Корзина 🛒',
            callback_data=MenuCallback(level=4, menu_name='cart'))
    keyboard.adjust(*sizes)

    items = list(products_btns.items())
    if len(items) <= 5:
        row_prdcts = [
            InlineKeyboardButton(text=key,
                callback_data=MenuCallback(
                    level=level+1,
                    menu_name='product',
                    category=category,
                    product_id=value,
                    page=page).pack())
            for key, value in items
        ]
        keyboard.row(*row_prdcts)
    else:
        mid = (len(items) + 1) // 2
        first_half = items[:mid]
        second_half = items[mid:]
        row1_prdcts = [
            InlineKeyboardButton(text=key,
                callback_data=MenuCallback(
                    level=level+1,
                    menu_name='product',
                    category=category,
                    product_id=value,
                    page=page).pack())
            for key, value in first_half
        ]
        keyboard.row(*row1_prdcts)
        row2_prdcts = [
            InlineKeyboardButton(text=key,
                callback_data=MenuCallback(
                    level=level+1,
                    menu_name='product',
                    category=category,
                    product_id=value,
                    page=page).pack())
            for key, value in second_half
        ]
        keyboard.row(*row2_prdcts)

    row_pgntns = []
    for text, menu_name in paginations_btns.items():
        if menu_name == 'next':
            menu_name = 'products_list'
            row_pgntns.append(InlineKeyboardButton(text=text,
                        callback_data=MenuCallback(
                            level=level,
                            menu_name=menu_name,
                            category=category,
                            page=page + 1).pack())
            )
        elif menu_name == 'previous':
            menu_name = 'products_list'
            row_pgntns.append(InlineKeyboardButton(text=text,
                        callback_data=MenuCallback(
                            level=level,
                            menu_name=menu_name,
                            category=category,
                            page=page - 1).pack())
            )

    return keyboard.row(*row_pgntns).as_markup()


def get_product_btns(
    *,
    level: int,
    product_id: int,
    category: int,
    page: int,
    sizes: tuple[int] = (2, 1, 2)
):

    keyboard = InlineKeyboardBuilder()

    keyboard.button(text='Назад ↖️',
            callback_data=MenuCallback(level=level-1, menu_name='products_list', category=category, page=page))
    keyboard.button(text='Корзина 🛒',
            callback_data=MenuCallback(level=4, menu_name='cart'))
    keyboard.button(text='В корзину 📥',
                callback_data=MenuCallback(level=level, menu_name='add_to_cart', product_id=product_id, category=category, page=page))
    keyboard.button(text='Посмотреть остальные фото',
                callback_data=MenuCallback(level=level, menu_name='more_photo', product_id=product_id, category=category, page=page))

    return keyboard.adjust(*sizes).as_markup()


def get_user_cart_btns(
    *,
    level: int,
    page: int | None,
    paginations_btns: dict | None,
    change_btns: dict | None,
    product_id: int | None,
    sizes: tuple[int] = (3, )
):

    keyboard = InlineKeyboardBuilder()

    if page:
        keyboard.button(text='Удалить ❌',
                callback_data=MenuCallback(level=level, menu_name='delete', product_id=product_id, page=page))

        row_change = []
        for text, menu_name in change_btns.items():
            row_change.append(InlineKeyboardButton(text=text,
                callback_data=MenuCallback(
                    level=level, menu_name=menu_name, product_id=product_id, page=page).pack()))

        keyboard.row(*row_change).adjust(*sizes)

        row_pgntns = []
        for text, menu_name in paginations_btns.items():
            if menu_name == 'next':
                row_pgntns.append(InlineKeyboardButton(text=text,
                    callback_data=MenuCallback(
                        level=level, menu_name=menu_name, page=page + 1).pack()))
            elif menu_name == 'previous':
                row_pgntns.append(InlineKeyboardButton(text=text,
                    callback_data=MenuCallback(
                        level=level, menu_name=menu_name, page=page - 1).pack()))

        keyboard.row(*row_pgntns)

        row_bttm = [
            InlineKeyboardButton(text='На главную 🏠',
                    callback_data=MenuCallback(level=0, menu_name='main').pack()),
            InlineKeyboardButton(text='Оплатить',
                    callback_data=MenuCallback(level=5, menu_name='order').pack()),
        ]

        return keyboard.row(*row_bttm).as_markup()

    else:
        keyboard.button(text='На главную 🏠',
                    callback_data=MenuCallback(level=0, menu_name='main'))

        return keyboard.adjust(*sizes).as_markup()


def get_order_btns(
    *,
    level: int,
    page: int | None,
    paginations_btns: dict | None,
    sizes: tuple[int] = (2, )
):
    
    keyboard = InlineKeyboardBuilder()

    if page:

        keyboard.button(text='Корзина 🛒',
                callback_data=MenuCallback(level=4, menu_name='cart'))
        keyboard.button(text='Удалить корзину ❌',
                callback_data=MenuCallback(level=level, menu_name='delete_carts', page=page))
        keyboard.button(text='На главную 🏠',
                        callback_data=MenuCallback(level=0, menu_name='main'))
        keyboard.button(text='Подтвердить оплату 💸',
                callback_data=MenuCallback(level=level, menu_name='payment'))

        keyboard.adjust(*sizes)

        row_pgntns = []
        for text, menu_name in paginations_btns.items():
            if menu_name == 'next':
                row_pgntns.append(InlineKeyboardButton(text=text,
                    callback_data=MenuCallback(
                        level=level, menu_name=menu_name, page=page + 1).pack()))
            elif menu_name == 'previous':
                row_pgntns.append(InlineKeyboardButton(text=text,
                    callback_data=MenuCallback(
                        level=level, menu_name=menu_name, page=page - 1).pack()))

        return keyboard.row(*row_pgntns).as_markup()

    else:
        keyboard.button(text='На главную 🏠',
                    callback_data=MenuCallback(level=0, menu_name='main'))

        return keyboard.adjust(*sizes).as_markup()


def get_orders_btns(
    *,
    level: int,
    page: int | None,
    paginations_btns: dict | None,
    sizes: tuple[int] = (1, )
):
    
    keyboard = InlineKeyboardBuilder()

    if page:

        keyboard.button(text='На главную 🏠',
                        callback_data=MenuCallback(level=0, menu_name='main'))

        keyboard.adjust(*sizes)

        row_pgntns = []
        for text, menu_name in paginations_btns.items():
            if menu_name == 'next':
                row_pgntns.append(InlineKeyboardButton(text=text,
                    callback_data=MenuCallback(
                        level=level, menu_name=menu_name, page=page + 1).pack()))
            elif menu_name == 'previous':
                row_pgntns.append(InlineKeyboardButton(text=text,
                    callback_data=MenuCallback(
                        level=level, menu_name=menu_name, page=page - 1).pack()))

        return keyboard.row(*row_pgntns).as_markup()

    else:
        keyboard.button(text='На главную 🏠',
                    callback_data=MenuCallback(level=0, menu_name='main'))

        return keyboard.adjust(*sizes).as_markup()







def get_callback_btns(
    *,
    btns: dict[str, str],
    sizes: tuple[int] = (2,)
):
    keyboard = InlineKeyboardBuilder()
    for text, data in btns.items():
        keyboard.add(InlineKeyboardButton(text=text, callback_data=data))
    return keyboard.adjust(*sizes).as_markup()

def get_url_btns(
    *,
    btns: dict[str, str],
    sizes: tuple[int] = (2,)
):
    keyboard = InlineKeyboardBuilder()
    for text, url in btns.items():
        keyboard.add(InlineKeyboardButton(text=text, url=url))
    return keyboard.adjust(*sizes).as_markup()

#Создать микс из CallBack и URL кнопок
def get_inlineMix_btns(
    *,
    btns: dict[str, str],
    sizes: tuple[int] = (2,)
):
    keyboard = InlineKeyboardBuilder()
    for text, value in btns.items():
        if '://' in value:
            keyboard.add(InlineKeyboardButton(text=text, url=value))
        else:
            keyboard.add(InlineKeyboardButton(text=text, callback_data=value))
    return keyboard.adjust(*sizes).as_markup()
