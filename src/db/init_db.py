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

    sql.execute("""
    -- 1) Lug'atlar (book)
CREATE TABLE IF NOT EXISTS vocab_books (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    src_lang VARCHAR(10),
    trg_lang VARCHAR(10),
    is_public BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now(),
    CONSTRAINT uq_user_book UNIQUE (user_id, name)
);

-- 2) So'z juftliklari
CREATE TABLE IF NOT EXISTS vocab_entries (
    id SERIAL PRIMARY KEY,
    book_id INTEGER NOT NULL REFERENCES vocab_books(id) ON DELETE CASCADE,
    word_src TEXT NOT NULL,
    word_trg TEXT NOT NULL,
    src_lang VARCHAR(10),
    trg_lang VARCHAR(10),
    position INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now(),
    CONSTRAINT uq_entry UNIQUE (book_id, word_src, word_trg)
);

-- 3) Mashq (session)
CREATE TABLE IF NOT EXISTS practice_sessions (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    book_id INTEGER,
    started_at TIMESTAMP DEFAULT now(),
    finished_at TIMESTAMP,
    total_questions INTEGER DEFAULT 0,
    correct_count INTEGER DEFAULT 0,
    wrong_count INTEGER DEFAULT 0,
    meta JSONB DEFAULT '{}'::jsonb
);

-- 4) Har bir savol haqida yozuv
CREATE TABLE IF NOT EXISTS practice_questions (
    id SERIAL PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES practice_sessions(id) ON DELETE CASCADE,
    entry_id INTEGER REFERENCES vocab_entries(id) ON DELETE SET NULL,
    presented_text TEXT,
    correct_translation TEXT,
    choices JSONB, -- array of choices
    chosen_option TEXT,
    is_correct BOOLEAN,
    asked_at TIMESTAMP DEFAULT now(),
    answered_at TIMESTAMP
);

-- Indekslar
CREATE INDEX IF NOT EXISTS idx_vocab_books_user ON vocab_books(user_id);
CREATE INDEX IF NOT EXISTS idx_vocab_entries_book ON vocab_entries(book_id);
CREATE INDEX IF NOT EXISTS idx_practice_sessions_user ON practice_sessions(user_id);""") 
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
