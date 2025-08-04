# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class Banner(models.Model):
    name = models.CharField(unique=True, max_length=20)
    image = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    created = models.DateTimeField()
    updated = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'banner'


class Cart(models.Model):
    user = models.ForeignKey('User', models.DO_NOTHING, to_field='user_id')
    product = models.ForeignKey('Product', models.DO_NOTHING)
    quantity = models.DecimalField(max_digits=5, decimal_places=2)
    created = models.DateTimeField()
    updated = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'cart'


class Category(models.Model):
    name = models.CharField(unique=True, max_length=20)
    banner = models.CharField(max_length=100, blank=True, null=True)
    parent = models.ForeignKey('self', models.DO_NOTHING, blank=True, null=True)
    created = models.DateTimeField()
    updated = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'category'


class Product(models.Model):
    image = models.TextField()  # This field type is a guess.
    name = models.CharField(max_length=50)
    description = models.TextField()
    price = models.DecimalField(max_digits=5, decimal_places=2)

class Category(models.Model):
    name = models.CharField(unique=True, max_length=20)
    banner = models.CharField(max_length=100, blank=True, null=True)
    parent = models.ForeignKey('self', models.DO_NOTHING, blank=True, null=True)
    created = models.DateTimeField()
    updated = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'category'


    pattern = models.CharField(max_length=20)
    color = models.TextField()  # This field type is a guess.
    gender = models.CharField(max_length=20)
    created = models.DateTimeField()
    updated = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'product'


class User(models.Model):
    user_id = models.BigIntegerField(unique=True)
    first_name = models.CharField(max_length=50, blank=True, null=True)
    last_name = models.CharField(max_length=50, blank=True, null=True)
    user_name = models.CharField(max_length=50, blank=True, null=True)
    phone = models.CharField(max_length=13, blank=True, null=True)
    created = models.DateTimeField()
    updated = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'user'
