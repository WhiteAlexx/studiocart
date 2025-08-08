from os import environ


class Config:
    BOT_TOKEN = '7683870154:AAFVtIjPdNf_HQEnAuxgZJEdUd4Hy_WPzok'
    ADMIN_ID = [844168645]
    REDIS_URL = environ.get('REDIS_URL', 'redis://redis:6379/0')
    CELERY_BROKER = environ.get('CELERY_BROKER', 'redis://redis:6379/1')
    RECEIPTS_DIR = '/usr/src/receipts'

config = Config()
