import re

from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.html import format_html
import requests


class Base(models.Model):

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)


class Banner(Base):
    name = models.CharField(unique=True, max_length=20)
    image = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'banner'


class Category(Base):
    name = models.CharField(unique=True, max_length=20, verbose_name='Название')
    banner = models.CharField(max_length=100, blank=True, null=True, verbose_name='Баннер')
    parent = models.ForeignKey('self', models.PROTECT, blank=True, null=True, verbose_name='Родитель')

    class Meta:
        managed = False
        db_table = 'category'
        verbose_name = 'Категорию'
        verbose_name_plural = 'Категории'
        indexes = [
            models.Index(fields=['name', 'parent']),
        ]

    def __str__(self):
        return self.get_full_path()

    def get_full_path(self):
        path = [self.name]
        curr_parent = self.parent
        while curr_parent:
            path.insert(0, curr_parent.name)
            curr_parent = curr_parent.parent
        return ' > '.join(path)



class Product(Base):
    image = ArrayField(models.CharField(max_length=100), default=list, verbose_name='TELEGRAM FILE ID',
        help_text='Автоматически заполняется при сохранении')
    name = models.CharField(max_length=50, verbose_name='Название')
    description = models.TextField(verbose_name='Описание')
    price = models.DecimalField(default=0, max_digits=7, decimal_places=2, verbose_name='Цена')
    quantity = models.DecimalField(default=0, max_digits=5, decimal_places=2, verbose_name='Остаток')
    unit = models.CharField(max_length=10, verbose_name='Единицы измерения',
        choices=(('м', 'м'),
                ('шт', 'шт'),),)
    discount = models.CharField(max_length=10, default='0%', verbose_name='Скидка',
        help_text='В процентах или рублях. Число с % или р без пробела. Примеры: 10% или 100р')
    category = models.ForeignKey(Category, models.DO_NOTHING)

    pattern = models.CharField(max_length=20, verbose_name='Паттерн', blank=True, null=True,
        choices=(('Однотон', 'Однотон'),
                ('Принт', 'Принт'),),)
    color = ArrayField(models.CharField(max_length=20), default=list, blank=True, null=True,
        verbose_name='Оттенок',
        help_text='Для выбора основного оттенка для цвета в названии\n\
(например, в названии "мятный", здесь "зеленый")')
    gender = models.CharField(max_length=20, verbose_name='Признак', blank=True, null=True,
        choices=(('Мужской', 'Мужской'),
                ('Женский', 'Женский'),
                ('Детский', 'Детский'),),)

    class Meta:
        managed = False
        db_table = 'product'
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'
        indexes = []

    def __str__(self):
        return f"{self.category.name} > {self.name}"

    def clean(self):
        if len(self.image) < 1:
            raise ValidationError({
                'image': 'Должно быть хотя бы одно изображение'
            })
        if len(self.image) > 10:
            raise ValidationError({
                'image': 'Не более 10 изображений'
            })

        if self.price < 0:
            raise ValidationError({
                'price': 'Цена не может быть меньше 0'
            })
        if self.quantity < 0:
            raise ValidationError({
                'quantity': 'Количество не может быть меньше 0'
            })

        discount_pattern = r'^(\d+)(%|р)$'
        match = re.match(discount_pattern, self.discount)
        if not match:
            raise ValidationError({
                'discount': 'Неверный формат. Примеры: 10% или 100р'
            })

        value = int(match.group(1))
        unit = match.group(2)

        if unit == '%' and value > 100:
            raise ValidationError({
                'discount': 'Скидка не может превышать 100%'
            })
        if unit == 'р' and value > self.price:
            raise ValidationError({
                'discount': 'Скидка не может превышать цену'
            })

    def image_previews(self):
        return format_html(
            '<div stile="display: flex; flex-wrap: wrap; gap: 10px;">{}</div',
            ''.join([
                f'<img src="https://api.telegram.org/file/bot{settings.TELEGRAM_BOT_TOKEN}/{self.get_file_path(file_id)}" \
                    widyh="100" stile="border: 1px solid #ddd; border-radius: 4px;">'
                for file_id in self.image[:10]
            ])
        )
    image_previews.short_description = 'Изображения'

    def get_file_path(self, file_id):
        #   !   !   ! К Э Ш И Р О В А Т Ь !   !   !
        try:
            response = requests.get(
                f"https://api/telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/getFile?file_id={file_id}",
                timeout=5
            )
            if response.status_code == 200:
                return response.json()['result']['file_path']
        except:
            return f"path/to/{file_id}.jpg"


class ProductImageUpload(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='upload')
    image = models.ImageField(upload_to='product_uploads', verbose_name='Новое изображение')

    class Meta:
        verbose_name = 'Загружаемое изображение'
        verbose_name_plural = 'Загружаемые изображения'

    def __str__(self):
        return f"Изображение для {self.product.name}"
