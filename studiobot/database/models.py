from decimal import Decimal, ROUND_HALF_UP
from typing import List

from sqlalchemy import ARRAY, BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey, Index, Numeric, String, Text, event, update, func, text
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, attributes, mapped_column, relationship, validates


class Base(DeclarativeBase):
    created: Mapped[DateTime] = mapped_column(DateTime, default=func.now())
    updated: Mapped[DateTime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())


class Banner(Base):
    __tablename__ = 'banner'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(20), unique=True)
    image: Mapped[str] = mapped_column(String(100), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)


class Category(Base):
    __tablename__ = 'category'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(20), unique=True)
    banner: Mapped[str] = mapped_column(String(100), nullable=True)
    parent_id: Mapped[int] = mapped_column(ForeignKey('category.id'), nullable=True, index=True)

    children: Mapped[List['Category']] = relationship(remote_side=[parent_id], lazy='selectin')


class Product(Base):
    __tablename__ = 'product'
    __table_args__ = (
        CheckConstraint('quantity >= 0', name='check_quantity_positive'),
        # Для полнотекстового поиска по name
        Index('idx_product_name_tsv', 
              text("to_tsvector('russian', name)"), 
              postgresql_using='gin'),
        # Для полнотекстового поиска по description
        Index('idx_product_description_tsv', 
              text("to_tsvector('russian', description)"), 
              postgresql_using='gin'),
        # Для частичного поиска по name
        Index('idx_product_name_trgm', text("name gin_trgm_ops"), postgresql_using='gin'),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    image: Mapped[list[str]] = mapped_column(ARRAY(String(100)), default=list)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(Text)
    price: Mapped[float] = mapped_column(Numeric(7,2), nullable=False)
    quantity: Mapped[float] = mapped_column(Numeric(5,2), nullable=False)
    unit: Mapped[str] = mapped_column(String(10), nullable=False)
    discount: Mapped[str] = mapped_column(String(10), default='0%')
    category_id: Mapped[int] = mapped_column(ForeignKey('category.id', ondelete='CASCADE'), nullable=False)

    category: Mapped['Category'] = relationship(backref='product')
    #   варианты: однотон, принт
    pattern: Mapped[str] = mapped_column(String(20), default='')
    #   для выбора основного оттенка для цвета в названии
    #   (например, в названии "мятный", здесь "зеленый")
    color: Mapped[list[str]] = mapped_column(ARRAY(String(20)), default=list, index=True)
    #   варианты: мужской, женский, детский
    gender: Mapped[str] = mapped_column(String(20), default='')

    @validates('quantity')
    def validate_quantity(self, key, value):
        if value < 0:
            raise ValueError('Количество не может быть отрицательным')
        return value

    @hybrid_property
    def discount_percent(self):
        '''
        Возвращает скидку в процентах для отображения пользователю.
        Если скидка в рублях - конвертирует в проценты от цены.
        '''

        value = Decimal(self.discount[:-1]).quantize(Decimal(0.00), ROUND_HALF_UP)

        if self.discount.endswith('%'):
            return value
        else:  # заканчивается на 'р'
            # Конвертируем рублевую скидку в проценты
            if self.price > 0:
                return (value / self.price) * 100
            return 0.0

    @hybrid_property
    def final_price(self):
        '''Рассчитывает итоговую цену с учётом скидки'''

        value = Decimal(self.discount[:-1]).quantize(Decimal(0.00), ROUND_HALF_UP)

        if self.discount.endswith('%'):
            return self.price * (1 - value / 100)
        else:  # заканчивается на 'р'
            return max(0, self.price - value)

    @hybrid_property
    def discount_display(self) -> str:
        '''Возвращает скидку в формате для отображения (всегда в %)'''
        if self.discount_percent % 1 == 0:
            return f"{self.discount_percent:.0f}%"
        else:
            return f"{self.discount_percent:.2f}%"


class User(Base):
    __tablename__ = 'user'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    first_name: Mapped[str] = mapped_column(String(50), nullable=True)
    last_name: Mapped[str]  = mapped_column(String(50), nullable=True)
    user_name: Mapped[str]  = mapped_column(String(50), nullable=True)
    phone: Mapped[str]  = mapped_column(String(13), nullable=True)


class Cart(Base):
    __tablename__ = 'cart'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('user.user_id', ondelete='CASCADE'), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey('product.id', ondelete='CASCADE'), nullable=False)
    quantity: Mapped[float] = mapped_column(Numeric(5,2), nullable=False)

    user: Mapped['User'] = relationship(backref='cart')
    product: Mapped['Product'] = relationship(backref='cart')


class Order(Base):
    __tablename__ = 'orders'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('user.user_id', ondelete='CASCADE'), nullable=False)
    product: Mapped[str] = mapped_column(String(50), nullable=False)            #   Содержит 'ID//NAME' товара. '//' - разделитель
    quantity: Mapped[str] = mapped_column(String(50), nullable=False)           #   Содержит 'QUANTITY+UNIT' товара. '' - разделитель
    cost: Mapped[float] = mapped_column(Numeric(7,2), nullable=False)

    user: Mapped['User'] = relationship(backref='order')
