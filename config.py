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


LANG_FLAGS = {
    "uz": "🇺🇿",  # O‘zbek
    "en": "🇺🇸",  # Ingliz (default USA)
    "ru": "🇷🇺",  # Rus
    "id": "🇮🇩",  # Indonez
    "ar": "🇸🇦",  # Arab (Saudiya)
    "tr": "🇹🇷",  # Turk
    "fa": "🇮🇷",  # Fors (Eron)
    "ms": "🇲🇾",  # Malay (Malayziya)
    "fr": "🇫🇷",  # Fransuz
    "es": "🇪🇸",  # Ispan
    "pt": "🇵🇹",  # Portugal (pt-br bo‘lsa ham asosiy qismini olamiz)
    "km": "🇰🇲",  # Khmer/Comoros
    "de": "🇩🇪",  # Nemis
    "am": "🇪🇹",  # Amxar (Efiopiya)
    "kk": "🇰🇿",  # Qozoq
    "uk": "🇺🇦",  # Ukraina
    "ko": "🇰🇷",  # Koreys
    "he": "🇮🇱",  # Ibroniy
    "ro": "🇷🇴",  # Rumin
    "it": "🇮🇹",  # Italyan
    "az": "🇦🇿",  # Ozarbayjon
    "hy": "🇦🇲",  # Arman
    "zh": "🇨🇳",  # Xitoy (oddiy yozuvi uchun)
    "hi": "🇮🇳",  # Hind
    "nl": "🇳🇱",  # Niderland
    "bg": "🇧🇬",  # Bolgar
    "vi": "🇻🇳",  # Vetnam
    "mn": "🇲🇳",  # Mo‘g‘ul
    "nb": "🇳🇴",  # Norveg
    "hr": "🇭🇷",  # Xorvat
    "sv": "🇸🇪",  # Shved
    "be": "🇧🇾",  # Belarus
    "th": "🇹🇭",  # Tailand
    "gu": "🇮🇳",  # Gujarati (Hindiston)
}