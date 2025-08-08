import decimal
from email.mime import image
from sqlalchemy.ext.asyncio import AsyncSession

from aiogram.types import InputMediaPhoto

from common.constants import text_for_order
from database.orm_query import orm_add_to_cart, orm_delete_from_cart, orm_get_banner, orm_get_categories, orm_get_category, orm_get_product, orm_get_products, orm_get_user_carts, orm_get_user_orders, orm_reduce_product_in_cart
from keybds.inline import get_order_btns, get_orders_btns, get_product_btns, get_products_list_btns, get_user_cart_btns, get_user_catalog_btns, get_user_main_btns
from services.storage import Storage
from utils.paginator import Paginator
from utils.service import cart_caption, get_caption


async def main_menu(session, level, menu_name):

    banner = await orm_get_banner(session, menu_name)
    image = InputMediaPhoto(media=banner.image, caption=banner.description)

    kbds = get_user_main_btns(level=level)

    return image, kbds


async def catalog_menu(session, level, menu_name, parent_id):

    if menu_name == 'catalog':
        banner = await orm_get_banner(session, menu_name)
        image = InputMediaPhoto(media=banner.image, caption=banner.description)
    else:
        category = await orm_get_category(session, parent_id)
        image = InputMediaPhoto(media=category.banner, caption=category.name)

    categories = await orm_get_categories(session, parent_id)

    kbds = get_user_catalog_btns(level=level, categories=categories)

    return image, kbds


def product_count(product_list: list):

    btns = dict()
    btns = {
        str(idx): product.id
        for idx, product in enumerate(product_list, start=1)}

    return btns


def pages(paginator: Paginator):

    btns = dict()
    if paginator.has_previous():
        btns['◀️ Пред.'] = 'previous'
    if paginator.has_next():
        btns['След. ▶️'] = 'next'

    return btns


async def products_list_menu(session, level, category, page):

    products = await orm_get_products(session, category_id=category)
    paginator = Paginator(products, page=page, per_page=10)
    product_list = paginator.get_page()

    txt_prdcts_lst = '\n'.join(
                f"{idx}. {product.name} {product.quantity}{product.unit}"
                for idx, product in enumerate(product_list, start=1)
                )
    caption = f"{txt_prdcts_lst}\n\n\nНажмите соответствующую кнопку, чтобы посмотреть товар👇\n\n\
                        Страница {paginator.page} из {paginator.pages}"

    products_btns = product_count(product_list)
    paginations_btns = pages(paginator)

    img_lst = [product.image[0] for product in product_list]
    image = (img_lst, caption)

    kbds = get_products_list_btns(
        level=level,
        category=category,
        page=page,
        products_btns=products_btns,
        paginations_btns=paginations_btns,
    )

    return image, kbds


async def product_menu(session, level, product_id, category, page):

    product = await orm_get_product(session, product_id)

    caption = await get_caption(product)

    image = InputMediaPhoto(media=product.image[0], caption=caption)

    kbds = get_product_btns(
        level=level,
        product_id=product.id,
        category=category,
        page=page,
    )

    return image, kbds


def change_btns(cart):

    btns = dict()

    if cart.product.unit == 'шт':
        if cart.product.quantity > 0:
            btns['➖1шт.'] = 'decrement'
            btns['➕1шт.'] = 'increment'
        else:
            btns['➖1шт.'] = 'decrement'

    if cart.product.unit == 'м':
        if cart.product.quantity <= 0 and cart.quantity <= 1.2:
            btns[''] = ''
        else:
            btns['Изменить метраж'] = 'change_m'

    return btns


async def carts(session, level, menu_name, page, user_id, product_id):

    if menu_name == 'delete':
        await orm_delete_from_cart(session, user_id, product_id)
        if page > 1: page -= 1

    elif menu_name == 'decrement':
        is_cart = await orm_reduce_product_in_cart(session, user_id, product_id, quantity=1)
        if page > 1 and not is_cart: page -= 1
    elif menu_name == 'increment':
        try:
            await orm_add_to_cart(session, user_id, product_id, quantity=1)
        except ValueError:
            menu_name = 'value_error'

    carts = await orm_get_user_carts(session, user_id)

    if not carts:
        banner = await orm_get_banner(session, 'cart')
        image = InputMediaPhoto(media=banner.image, caption=f"<b>{banner.description}</b>")

        kbds = get_user_cart_btns(
            level=level,
            page=None,
            paginations_btns=None,
            change_btns=None,
            product_id=None
        )

    else:
        paginator = Paginator(carts, page=page)

        cart = paginator.get_page()[0]

        caption = await cart_caption(carts, cart)

        image = InputMediaPhoto(
            media = cart.product.image[0],
            caption=caption + f"Товар {paginator.page} из {paginator.pages} в корзине."
        )

        kbds = get_user_cart_btns(
            level=level,
            page=page,
            paginations_btns=pages(paginator),
            change_btns=change_btns(cart),
            product_id=cart.product.id
        )

    return image, kbds


async def order(session, level, menu_name, user_id, page):

    carts = await orm_get_user_carts(session, user_id=user_id)

    if menu_name == 'delete_carts':
        for cart in carts:
            await orm_delete_from_cart(session, user_id, cart.product_id)

    if not carts:
        banner = await orm_get_banner(session, 'cart')
        image = InputMediaPhoto(media=banner.image, caption=f"<b>{banner.description}</b>")

        kbds = get_order_btns(
            level=level,
            page=None,
            paginations_btns=None,
        )

    else:

        paginator = Paginator(carts, page=page, per_page=20)
        cart_list = paginator.get_page()

        txt_carts_lst = '\n'.join(
                    f"{idx}. {cart.product.name} {cart.quantity}{cart.product.unit}"
                    for idx, cart in enumerate(cart_list, start=1)
                    )
        total_price = round(sum(cart.quantity * cart.product.final_price for cart in carts), 2)

        Storage.save_state(user_id, {'order_amount': float(total_price)})

        caption = f"{txt_carts_lst}\n\n<b>К оплате {total_price}{text_for_order}</b>\n\
                            Страница {paginator.page} из {paginator.pages}"

        paginations_btns = pages(paginator)

        banner = await orm_get_banner(session, menu_name)
        image = InputMediaPhoto(media=banner.image, caption=caption)

        kbds = get_order_btns(
            level=level,
            page=page,
            paginations_btns=paginations_btns,
        )

    return image, kbds


async def orders(session, level, menu_name, user_id, page):

    grouped_orders = await orm_get_user_orders(session, user_id)
    banner = await orm_get_banner(session, 'order')

    if not grouped_orders:
        image = InputMediaPhoto(media=banner.image, caption=f"<b>{banner.description}</b>")

        kbds = get_orders_btns(
            level=level,
            page=None,
            paginations_btns=None,
        )

    else:
        paginator = Paginator(grouped_orders, page=page)

        orders = paginator.get_page()[0]

        cost = orders[0].cost
        date = orders[0].created.strftime('%d.%m.%Y %H:%M')

        txt_orders_lst = '\n'.join(
                    f"{idx}. {order.product.split('//', 1)[1]} - {order.quantity}"
                    for idx, order in enumerate(orders, start=1)
                    )

        caption = f"<b><u>Заказ на сумму {cost}₽</u>\n<i>от {date}</i>:</b>\n\n{txt_orders_lst}\n\n\n"

        image = InputMediaPhoto(
            media = banner.image,
            caption=caption + f"            Заказ {paginator.page} из {paginator.pages}"
        )

        paginations_btns = pages(paginator)

        kbds = get_orders_btns(
            level=level,
            page=page,
            paginations_btns=paginations_btns,
        )

    return image, kbds


async def get_menu_content(

    session: AsyncSession,
    level: int,
    menu_name: str,
    parent_id: int | None = None,
    category: int | None = None,
    page: int | None = None,
    product_id: int | None = None,
    user_id: int | None = None,
    
):

    if level == 0:
        return await main_menu(session, level, menu_name)
    if level == 1:
        return await catalog_menu(session, level, menu_name, parent_id)
    if level == 2:
        return await products_list_menu(session, level, category, page)
    if level == 3:
        return await product_menu(session, level, product_id, category, page)
    if level == 4:
        return await carts(session, level, menu_name, page, user_id, product_id)
    if level == 5:
        return await order(session, level, menu_name, user_id, page)
    if level == 6:
        return await orders(session, level, menu_name, user_id, page)
