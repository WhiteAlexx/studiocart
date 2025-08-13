import decimal
from itertools import groupby
import pickle
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from database.models import Banner, Cart, Category, Order, Product, User
from database.redis_cli import redis_client


############### Работа с баннерами (информационными страницами) ###############

async def orm_add_banner_description(session: AsyncSession, data: dict):
    #Добавляем новый или изменяем существующий по именам
    #пунктов меню: main, about, cart, shipping, payment, catalog
    query = select(Banner)
    result = await session.execute(query)
    if result.first():
        return
    session.add_all([Banner(name=name, description=description) for name, description in data.items()]) 
    await session.commit()

async def orm_change_banner_image(session: AsyncSession, name: str, image: str):
    query = update(Banner).where(Banner.name == name).values(image=image)
    await session.execute(query)
    await session.commit()

async def orm_get_banner(session: AsyncSession, page: str):
    query = select(Banner).where(Banner.name == page)
    result = await session.execute(query)
    return result.scalar()

async def orm_get_info_pages(session: AsyncSession):
    query = select(Banner)
    result = await session.execute(query)
    return result.scalars().all()

async def orm_neo_banner(session: AsyncSession, data: dict):
    obj = Banner(
        name=data['name'],
        image=data['image'],
        description=data['description'],
    )
    session.add(obj)
    await session.commit()


############################ Категории ######################################

async def orm_get_categories(session: AsyncSession, parent_id: int | None = None):
    query = select(Category).where(Category.parent_id == parent_id).options(selectinload(Category.children))
    result = await session.execute(query)
    return result.scalars().all()

async def orm_get_category(session: AsyncSession, category_id: int):
    query = select(Category).where(Category.id == category_id)
    result = await session.execute(query)
    return result.scalar()

async def orm_create_categories(session: AsyncSession, categories: list):
    query = select(Category)
    result = await session.execute(query)
    if result.first():
        return
    session.add_all([Category(name=name) for name in categories]) 
    await session.commit()

##################### Работа с юзерами #####################################

async def orm_add_user(
    session: AsyncSession,
    user_id: int,
    first_name: str | None = None,
    last_name: str | None = None,
    user_name: str | None = None,
):
    query = select(User).where(User.user_id == user_id)
    result = await session.execute(query)
    if result.first() is None:
        session.add(
            User(user_id=user_id, first_name=first_name, last_name=last_name, user_name=user_name)
        )
    await session.commit()

async def orm_get_users(session: AsyncSession):
    query = select(User)
    result = await session.execute(query)
    return result.scalars().all()

#######################################################################################################

async def orm_get_products(session: AsyncSession, category_id):
    query = (select(Product)
                                    .where(Product.category_id == int(category_id))
                                    .where(Product.quantity > 0)
                                    .order_by(Product.id))
    result = await session.execute(query)
    return result.scalars().all()

async def orm_all_products(session: AsyncSession, category_id):
    query = select(Product).where(Product.category_id == int(category_id))
    result = await session.execute(query)
    return result.scalars().all()

async def orm_get_product(session: AsyncSession, product_id: int):
    query = select(Product).where(Product.id == product_id)
    result = await session.execute(query)
    return result.scalar()

async def orm_decrement_product_quant(session: AsyncSession, product_id: int, quantity: int | decimal.Decimal):
    query = select(Product).where(Product.id == product_id)
    product = await session.execute(query)
    product = product.scalar()
    product.quantity -= quantity
    return product

async def orm_increment_product_quant(session: AsyncSession, product_id: int, quantity: int | decimal.Decimal):
    query = select(Product).where(Product.id == product_id)
    product = await session.execute(query)
    product = product.scalar()
    product.quantity += quantity
    return product

######################## Работа с корзинами #######################################

async def orm_add_to_cart(session: AsyncSession, user_id: int, product_id: int, quantity: int | decimal.Decimal):
    query = select(Cart).where(Cart.user_id == user_id, Cart.product_id == product_id)
    cart = await session.execute(query)
    cart = cart.scalar()
    if cart:
        cart.quantity += quantity
        await orm_decrement_product_quant(session, product_id, quantity)
        await session.commit()
        return cart
    else:
        session.add(Cart(user_id=user_id, product_id=product_id, quantity=quantity))
        await orm_decrement_product_quant(session, product_id, quantity)
        await session.commit()


async def orm_change_cart(session: AsyncSession, user_id: int, product_id: int, quantity: int | decimal.Decimal):
    query = (select(Cart).where(Cart.user_id == user_id, Cart.product_id == product_id).options(selectinload(Cart.product)))
    cart = await session.execute(query)
    cart = cart.scalar()

    if not cart:
        return
    else:
        old_quantity = cart.quantity
        diff = quantity - old_quantity
        if diff == 0:
            return

        if diff > 0:
            cart.product.quantity -= diff
        else:
            cart.product.quantity += abs(diff)

        cart.quantity = quantity
        await session.commit()
        return cart


async def orm_reduce_product_in_cart(session: AsyncSession, user_id: int, product_id: int, quantity: int | decimal.Decimal):
    query = select(Cart).where(Cart.user_id == user_id, Cart.product_id == product_id)
    cart = await session.execute(query)
    cart = cart.scalar()

    if not cart:
        return
    if cart.quantity > 1:
        await orm_increment_product_quant(session, product_id, quantity=quantity)
        cart.quantity -= quantity
        await session.commit()
        return True
    else:
        await orm_delete_from_cart(session, user_id, product_id)
        await session.commit()
        return False


async def orm_delete_from_cart(session: AsyncSession, user_id: int, product_id: int):
    query = select(Cart).where(Cart.user_id == user_id, Cart.product_id == product_id)
    cart = await session.execute(query)
    cart = cart.scalar()
    await orm_increment_product_quant(session, product_id, quantity=cart.quantity)

    await session.delete(cart)
    await session.commit()


async def orm_get_user_carts(session: AsyncSession, user_id):
    query = select(Cart).filter(Cart.user_id == user_id).options(selectinload(Cart.product)).order_by(Cart.id)
    result = await session.execute(query)
    return result.scalars().all()


async def orm_delete_all_carts(session: AsyncSession):
    query = select(Cart)#.options(selectinload(Cart.product)).options(selectinload(Cart.user))
    result = await session.execute(query)
    carts = result.scalars().all()

    users_ids = set()

    for cart in carts:
        users_ids.add(cart.user_id)
        await orm_increment_product_quant(session, product_id=cart.product_id, quantity=cart.quantity)
        await session.delete(cart)

    await session.commit()
    return users_ids

###################################################################################################

async def orm_create_orders(session: AsyncSession, user_id):
    query = select(Cart).filter(Cart.user_id == user_id).options(selectinload(Cart.product))
    result = await session.execute(query)
    carts = result.scalars().all()

    total_price = round(sum(cart.quantity * cart.product.final_price for cart in carts), 2)

    orders = [
        Order(
            user_id=user_id,
            product=f"{cart.product.id}//{cart.product.name}",
            quantity=f"{cart.quantity}{cart.product.unit}",
            cost=total_price,
        )
        for cart in carts
    ]

    session.add_all(orders)
    await session.execute(delete(Cart).where(Cart.user_id == user_id))
    await session.commit()


async def orm_get_user_orders(session: AsyncSession, user_id):

    cache_key = f"orders:{user_id}"

    if cached_data := redis_client.get(cache_key):
        grouped_orders = pickle.loads(cached_data)

    else:
        query = select(Order).where(Order.user_id == user_id).order_by(Order.created.desc(), Order.cost)
        result = await session.execute(query)
        orders = result.scalars().all()

        grouped_orders = []
        for key, group in groupby(orders, key=lambda o: (o.created, o.cost)):
            grouped_orders.append(list(group))

        redis_client.set(cache_key, pickle.dumps(grouped_orders), ex=300)

    return grouped_orders


async def orm_delete_orders(session: AsyncSession, user_id, cost):
    await session.execute(delete(Order).where(Order.user_id == user_id, Order.cost == cost))
    await session.commit()
