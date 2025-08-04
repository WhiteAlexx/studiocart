import re
from decimal import Decimal, InvalidOperation


async def parse_count(text):

    text_clean = text.strip().lower()

    pattern = r'^\s*([\d,\.]+)\s*(см|м)\s*$'
    match = re.match(pattern, text_clean)
    
    if not match:
        return (False, '<b>❗Введены некорректные данные❗</b>\n\n\
Введите метраж (в см или м, <b><u>например 65см или 0,65м</u></b>):')
    
    num_str, unit = match.group(1), match.group(2)
    
    if unit == 'см':
        try:
            num = int(num_str)
        except ValueError:
            return (False, '<b>❗Некорректное целое число для сантиметров❗</b>\n\n\
Введите метраж (в см или м, <b><u>например 65см или 0,65м</u></b>):')
        
        value_in_m = Decimal(num) / Decimal(100)

    else:
        num_str_clean = num_str.replace(',', '.')
        try:
            value_in_m = Decimal(num_str_clean)
        except InvalidOperation:
            return (False, f"<b>❗Некорректное число: '{num_str}' для метров❗</b>\n\n\
Введите метраж (в см или м, <b><u>например 65см или 0,65м</u></b>):")

    value_in_m = value_in_m.quantize(Decimal('0.00'))

    if value_in_m < Decimal('0.10'):
        return (False, f"<b>❗Значение {value_in_m} м меньше минимального допустимого (0.10 м)❗</b>")
    
    return (True, value_in_m)


async def get_caption(product):
    
    top_text= ''
    if product.unit == 'шт':
        if product.quantity <= 0:
            top_text = '⛔️  ЗАКОНЧИЛСЯ   ⛔️\n\n'
        if product.quantity == 1:
            top_text = '❗❗❗❗❗❗❗\n    ПОСЛЕДНИЙ\n\n'
        if product.quantity == 2:
            top_text = '❗❗❗❗❗❗❗\nОсталось всего 2\n\n'

    residual = ''
    if product.unit == 'м':
        if product.quantity <= 0.15:
            top_text = '⛔️  ЗАКОНЧИЛСЯ   ⛔️\n\n'
        if 0.15 < product.quantity <= 1.2:
            top_text = '❗❗❗❗❗❗❗\nПОСЛЕДНИЙ ОТРЕЗ\n\n'
            residual = f"<i>✂️Отрез {product.quantity}{product.unit}✂️</i>\n\n"
        # if product.quantity == 2:
        #     top_text = '❗❗❗❗❗❗❗\nОсталось всего 2\n\n'

    if product.final_price % 1 == 0:
        price_txt = f"💳Цена {product.final_price:.0f}₽/{product.unit}"
    else:
        price_txt = f"💳Цена {product.final_price:.2f}₽/{product.unit}"

    if residual:
        price = product.quantity * product.final_price
        if price % 1 == 0:
            price_txt = f"💳Цена за отрез {price:.0f}₽"
        else:
            price_txt = f"💳Цена за отрез {price:.2f}₽"

    if product.discount_percent != 0:
        top_text += f"<b><i>🔥🔥🔥СКИДКА {product.discount_display}🔥🔥🔥</i></b>\n\n"

        if product.final_price % 1 == 0:
            price_txt = f"<i><b>💳Цена {product.final_price:.0f}₽/{product.unit}</b></i>"
        else:
            price_txt = f"<i><b>💳Цена {product.final_price:.2f}₽/{product.unit}</b></i>"

        if product.price % 1 == 0:
            price_txt += f" <i>(старая цена <s>{product.price:.0f}₽/{product.unit}</s>)</i>"
        else:
            price_txt += f" <i>(старая цена <s>{product.price:.2f}₽/{product.unit}</s>)</i>"

        if residual:
            price = product.quantity * product.final_price
            if price % 1 == 0:
                price_txt = f"<i><b>💳Цена за отрез {price:.0f}₽</b></i>"
            else:
                price_txt = f"<i><b>💳Цена за отрез {price:.2f}₽</b></i>"

            old_price = product.quantity * product.price
            if old_price % 1 == 0:
                price_txt += f" <i>(старая цена <s>{old_price:.0f}₽/{product.unit}</s>)</i>"
            else:
                price_txt += f" <i>(старая цена <s>{old_price:.2f}₽/{product.unit}</s>)</i>"

    caption = f"<b>{top_text}</b><b>{product.name}</b>\n\n{product.description}\n\n\
{residual}{price_txt}"

    if not residual and product.quantity < 999:
        if product.quantity % 1 == 0:
            caption += f"\n\nВ наличии {product.quantity:.0f}{product.unit}"
        else:
            caption += f"\n\nВ наличии {product.quantity:.2f}{product.unit}"

    return caption


async def cart_caption(carts, cart):


    cart_price = round(cart.quantity * cart.product.final_price, 2)
    if cart_price % 1 == 0:
        cart_price_txt = f"{cart_price:.0f}"
    else:
        cart_price_txt = f"{cart_price:.2f}"

    total_price = round(sum(cart.quantity * cart.product.final_price for cart in carts), 2)
    if total_price % 1 == 0:
        total_price_txt = f"{total_price:.0f}"
    else:
        total_price_txt = f"{total_price:.2f}"

    if cart.product.final_price % 1 == 0:
        final_price_txt = f"{cart.product.final_price:.0f}"
    else:
        final_price_txt = f"{cart.product.final_price:.2f}"

    if cart.quantity % 1 == 0:
        quantity_txt = f"{cart.quantity:.0f}"
    else:
        quantity_txt = f"{cart.quantity:.2f}"

    residual = ''
    if cart.product.unit == 'м' and cart.product.quantity <= 0.1 and cart.quantity <= 1.2:
        residual = '<i>У вас последний отрез в корзине</i>\n'

    caption = f"<b>{cart.product.name}</b>\n{residual}\
{final_price_txt}₽ x {quantity_txt}{cart.product.unit} = {cart_price_txt}₽\n\n\
Общая стоимость товаров в корзине {total_price_txt}₽\n\n"
    
    return caption
