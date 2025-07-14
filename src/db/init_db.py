from config import db, sql
from src.handlers.users.translate import LANGUAGES


async def create_all_base():
    sql.execute("""CREATE TABLE IF NOT EXISTS public.accounts
    (
        id SERIAL NOT NULL,
        user_id BIGINT NOT NULL,
        lang_code CHARACTER VARYING(10),
        date TIMESTAMP DEFAULT now(),
        CONSTRAINT accounts_pkey PRIMARY KEY (id)
    )""")
    db.commit()

    sql.execute("""CREATE TABLE IF NOT EXISTS public.mandatorys
    (
        id SERIAL NOT NULL,
        chat_id bigint NOT NULL,
        title character varying,
        username character varying,
        types character varying,
        CONSTRAINT channels_pkey PRIMARY KEY (id)
    )""")
    db.commit()

    sql.execute("""CREATE TABLE IF NOT EXISTS public.admins
    (
        id SERIAL NOT NULL,
        user_id BIGINT NOT NULL,
        date TIMESTAMP DEFAULT now(),
        CONSTRAINT admins_pkey PRIMARY KEY (id)
    )""")
    db.commit()

    sql.execute("""
        CREATE TABLE IF NOT EXISTS languages (
            code TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            flag TEXT
        );
    """)
    db.commit()

    sql.execute("""
    CREATE TABLE IF NOT EXISTS user_languages (
        user_id BIGINT PRIMARY KEY,
        from_lang TEXT,
        to_lang TEXT,
        FOREIGN KEY (from_lang) REFERENCES languages(code),
        FOREIGN KEY (to_lang) REFERENCES languages(code)
    );
    """)
    db.commit()

def init_languages_table():
    # Tillar mavjudligini tekshirish
    sql.execute("SELECT COUNT(*) FROM languages;")
    count = sql.fetchone()[0]

    if count == 0:
        print("Tillar bazaga qo‘shilmoqda...")
        for code, data in LANGUAGES.items():
            sql.execute(
                "INSERT INTO languages (code, name, flag) VALUES (%s, %s, %s) ON CONFLICT (code) DO NOTHING;",
                (code, data["name"], data["flag"])
            )
        db.commit()
        return True
    else:
        print(f"{count} ta til allaqachon mavjud.")
        return False
