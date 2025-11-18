import os

import psycopg2
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

dbtype = bool(os.getenv("DBTYPE"))
DB_TYPE = "sqlite" if dbtype else "postgres"
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")

DB_CONFIG = {
    "dbname": DB_NAME,
    "user": DB_USER,
    "password": DB_PASSWORD,
    "host": DB_HOST,
    "port": DB_PORT
}
db = psycopg2.connect(
    database=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT)
db.autocommit = True
sql = db.cursor()

ADMIN_ID = ADMINS = [int(admin_id) for admin_id in os.getenv("ADMINS_ID").split(",")]


bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(link_preview_is_disabled=True))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

LANGUAGES = {
    "auto": {"name": "Avto", "flag": "🌐"},
    "uz": {"name": "O‘zbek", "flag": "🇺🇿"},
    "en": {"name": "English", "flag": "🇬🇧"},
    "ru": {"name": "Русский", "flag": "🇷🇺"},
    "tr": {"name": "Türkçe", "flag": "🇹🇷"},
    "ar": {"name": "العربية", "flag": "🇸🇦"},
    "fr": {"name": "Français", "flag": "🇫🇷"},
    "de": {"name": "Deutsch", "flag": "🇩🇪"},
    "zh": {"name": "中文", "flag": "🇨🇳"},
    "ja": {"name": "日本語", "flag": "🇯🇵"},
    "ko": {"name": "한국어", "flag": "🇰🇷"},
    "hi": {"name": "हिन्दी", "flag": "🇮🇳"},
    "id": {"name": "Bahasa Indonesia", "flag": "🇮🇩"},
    "fa": {"name": "فارسی", "flag": "🇮🇷"},
    "es": {"name": "Español", "flag": "🇪🇸"},
    "it": {"name": "Italiano", "flag": "🇮🇹"},
    "kk": {"name": "Qazaqşa", "flag": "🇰🇿"},   # lotin alifbosida
    "ky": {"name": "Кыргызча", "flag": "🇰🇬"}, # faqat kirill
    "az": {"name": "Azərbaycan dili", "flag": "🇦🇿"},
    "tk": {"name": "Türkmençe", "flag": "🇹🇲"},
    "tg": {"name": "Тоҷикӣ", "flag": "🇹🇯"},
    "pl": {"name": "Polski", "flag": "🇵🇱"},
    "pt": {"name": "Português", "flag": "🇵🇹"},
    "am": {"name": "አማርኛ", "flag": "🇪🇹"},
}