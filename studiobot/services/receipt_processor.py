import os
import re

import fitz
from pdf2image import convert_from_path
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract

from config import config
from common.constants import PHONE_ENDING


def preprocess_image(img_path: str):

    img = Image.open(img_path)

    if img.mode != 'L':
        img = img.convert('L')

    img = img.filter(ImageFilter.SHARPEN)
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.5)
    processed_path = f"{img_path}_processed.jpg"
    img.save(processed_path)
    print(processed_path)

    return processed_path


def extract_text(file_path: str):

    text = ''

    if file_path.lower().endswith('.pdf'):
        with fitz.open(file_path) as doc:
            for page in doc:
                text += page.get_text() + '\n'

        if len(text.strip()) < 20:
            images = convert_from_path(file_path)

            for img in images:
                temp_path = os.path.join('/tmp', f"temp_{os.path.basename(file_path)}.jpg")
                img.save(temp_path, 'JPEG')
                text += extract_from_image(temp_path) + '\n'
                os.remove(temp_path)

    else:
        text = extract_from_image(file_path)

    return text.strip()


def extract_from_image(img_path: str):

    processed_path = preprocess_image(img_path)

    img = Image.open(processed_path)
    text = pytesseract.image_to_string(
        image=img,
        lang='rus',
        config='--psm 6'
    )
    # reader = easyocr.Reader(['ru', 'en'])
    # result = reader.readtext(processed_path, detail=0, paragraph=True)

    os.remove(processed_path)

    return text.strip()
    # return '\n'.join(result)


def validate_receipt(text: str, expected_amount: float):

    lines = [line.strip() for line in text.split('\n') if line.strip()]

    result = {
        'valid': False,
        'recipient': False,
        'phone': False,
        'amount': False,
        'details': []
    }

    recipient_patterns = [
        r"Светлана\s*Александровна\s*Л",
        r"Светлана\s*Л"
    ]

    for line in lines:
        print('СТРОКА: ' + line)

        for pattern in recipient_patterns:

            if re.search(pattern, line, re.IGNORECASE):
                result['recipient'] = True

        digits = re.sub(r'\D', '', line)
        print(digits)

        if len(digits) >= 7 and digits.endswith(PHONE_ENDING):
            result['phone'] = True

        amount_match = re.search(r"(\d[\d\s]*(?:,\d{2})?)\s*р", line, re.IGNORECASE)

        if amount_match:
            amount_str = amount_match.group(1).replace(' ', '').replace(',', '.')

            try:
                amount_val = float(amount_str)

                if abs(amount_val - expected_amount) < 0.001:
                    result['amount'] = True

            except:
                pass

    result['valid'] = result['recipient'] and result['phone'] and result['amount']

    result['details'] = [
        f"Получатель: {'✅' if result['recipient'] else '❌'}",
        f"Телефон: {'✅' if result['phone'] else '❌'}",
        f"Сумма ({expected_amount:.2f}₽): {'✅' if result['amount'] else '❌'}",
    ]

    return result
