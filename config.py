import os

import psycopg2
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

dbtype = os.getenv("DBTYPE", "postgres").lower()
DB_TYPE = "postgres" if dbtype == "postgres" else "sqlite"

if DB_TYPE == "postgres":
    # PostgreSQL configuration
    DB_NAME = os.getenv("DB_NAME", "tarjimon4")
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "parol")
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")

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
    print(f"[DB] Using PostgreSQL database: {DB_NAME}")
    
else:
    # SQLite support (fallback)
    import sqlite3
    DB_NAME = os.getenv("DB_NAME", "tarjimon4.db")
    db = sqlite3.connect(DB_NAME, check_same_thread=False)
    db.row_factory = sqlite3.Row
    cursor = db.cursor()
    
    import re as _re

    class SQLiteCursor:
        def __init__(self, cursor):
            self.cursor = cursor

        def _convert(self, query):
            # %s -> ?
            q = query.replace('%s', '?')
            # RETURNING ... -> remove
            q = _re.split(r'\bRETURNING\b', q, flags=_re.IGNORECASE)[0].strip()
            # SERIAL PRIMARY KEY -> INTEGER PRIMARY KEY AUTOINCREMENT
            q = _re.sub(r'\bSERIAL\b', 'INTEGER', q, flags=_re.IGNORECASE)
            # BIGINT, SMALLINT -> INTEGER
            q = _re.sub(r'\bBIGINT\b', 'INTEGER', q, flags=_re.IGNORECASE)
            q = _re.sub(r'\bSMALLINT\b', 'INTEGER', q, flags=_re.IGNORECASE)
            # DECIMAL(...) / NUMERIC(...) -> REAL
            q = _re.sub(r'\bDECIMAL\s*\([^)]*\)', 'REAL', q, flags=_re.IGNORECASE)
            q = _re.sub(r'\bNUMERIC\s*\([^)]*\)', 'REAL', q, flags=_re.IGNORECASE)
            # VARCHAR(...) -> TEXT
            q = _re.sub(r'\bVARCHAR\s*\([^)]*\)', 'TEXT', q, flags=_re.IGNORECASE)
            # TIMESTAMP / TIMESTAMPTZ -> TEXT
            q = _re.sub(r'\bTIMESTAMPTZ\b', 'TEXT', q, flags=_re.IGNORECASE)
            q = _re.sub(r'\bTIMESTAMP\b', 'TEXT', q, flags=_re.IGNORECASE)
            # BOOLEAN -> INTEGER
            q = _re.sub(r'\bBOOLEAN\b', 'INTEGER', q, flags=_re.IGNORECASE)
            # JSONB / JSON -> TEXT
            q = _re.sub(r'\bJSONB\b', 'TEXT', q, flags=_re.IGNORECASE)
            q = _re.sub(r'\bJSON\b', 'TEXT', q, flags=_re.IGNORECASE)
            # now() -> CURRENT_TIMESTAMP
            q = _re.sub(r'\bnow\(\)', 'CURRENT_TIMESTAMP', q, flags=_re.IGNORECASE)
            # DEFAULT '...'::jsonb  or  DEFAULT '{}'::text  -> DEFAULT '{}'
            q = _re.sub(r"::\w+", '', q)
            # CONSTRAINT ... FOREIGN KEY ... REFERENCES ... -> remove (SQLite has limited FK support)
            q = _re.sub(
                r',?\s*CONSTRAINT\s+\w+\s+FOREIGN\s+KEY\s*\([^)]*\)\s*REFERENCES\s+\w+\s*\([^)]*\)(\s+ON\s+\w+\s+\w+)*',
                '', q, flags=_re.IGNORECASE
            )
            # CONSTRAINT ... UNIQUE (...) -> keep as is (SQLite supports this)
            # ON CONFLICT DO UPDATE SET ... (upsert) -> ignore clause for SQLite
            q = _re.sub(
                r'\bON\s+CONFLICT\s*\([^)]*\)\s*DO\s+UPDATE\s+SET\b.*',
                'ON CONFLICT DO NOTHING',
                q, flags=_re.IGNORECASE | _re.DOTALL
            )
            return q

        def execute(self, query, params=None):
            sqlite_query = self._convert(query)
            try:
                if params:
                    return self.cursor.execute(sqlite_query, params)
                return self.cursor.execute(sqlite_query)
            except Exception as e:
                print(f"[SQLite ERROR] {e}\nQuery: {sqlite_query[:300]}")
                raise

        def fetchone(self):
            row = self.cursor.fetchone()
            return tuple(row) if row else None

        def fetchall(self):
            return [tuple(row) for row in self.cursor.fetchall()]

        @property
        def rowcount(self):
            return self.cursor.rowcount
    
    sql = SQLiteCursor(cursor)
    DB_CONFIG = {"dbname": DB_NAME, "user": "", "password": "", "host": "", "port": ""}
    print(f"[DB] Using SQLite database: {DB_NAME}")

ADMIN_ID = ADMINS = [int(admin_id) for admin_id in os.getenv("ADMINS_ID", "1918760732").split(",")]

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(link_preview_is_disabled=True))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

LANGUAGES = {
    "auto": {"name": "Avto", "flag": "🌐"},
    "uz": {"name": "O'zbek", "flag": "🇺🇿"},
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
    "kk": {"name": "Qazaqşa", "flag": "🇰🇿"},
    "ky": {"name": "Кыргызча", "flag": "🇰🇬"},
    "az": {"name": "Azərbaycan dili", "flag": "🇦🇿"},
    "tk": {"name": "Türkmençe", "flag": "🇹🇲"},
    "tg": {"name": "Тоҷикӣ", "flag": "🇹🇯"},
    "pl": {"name": "Polski", "flag": "🇵🇱"},
    "pt": {"name": "Português", "flag": "🇵🇹"},
    "am": {"name": "አማርኛ", "flag": "🇪🇹"},
}
