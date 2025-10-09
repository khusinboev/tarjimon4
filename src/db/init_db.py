from config import db, sql
from src.handlers.users.lughatlar.parallel import create_parallel_tables, init_parallel_series
from src.handlers.users.translate import LANGUAGES

async def create_all_base():
    """Barcha jadvallarni yaratish."""

    # 1) Accounts - foydalanuvchilar jadvali
    sql.execute("""
    CREATE TABLE IF NOT EXISTS public.accounts (
        id SERIAL PRIMARY KEY,
        user_id BIGINT NOT NULL UNIQUE,
        lang_code CHARACTER VARYING(10) DEFAULT 'uz',
        created_at TIMESTAMP DEFAULT now(),
        updated_at TIMESTAMP DEFAULT now()
    )""")

    # Index qo'shish
    sql.execute("""
    CREATE INDEX IF NOT EXISTS idx_accounts_user_id ON accounts(user_id);
    """)
    db.commit()

    # 2) Mandatorys - majburiy kanallar
    sql.execute("""
    CREATE TABLE IF NOT EXISTS public.mandatorys (
        id SERIAL PRIMARY KEY,
        chat_id BIGINT NOT NULL,
        title VARCHAR(255),
        username VARCHAR(100),
        types VARCHAR(50),
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT now()
    )""")
    db.commit()

    # 3) Admins - administratorlar
    sql.execute("""
    CREATE TABLE IF NOT EXISTS public.admins (
        id SERIAL PRIMARY KEY,
        user_id BIGINT NOT NULL UNIQUE,
        created_at TIMESTAMP DEFAULT now(),
        is_active BOOLEAN DEFAULT TRUE
    )""")

    sql.execute("""
    CREATE INDEX IF NOT EXISTS idx_admins_user_id ON admins(user_id);
    """)
    db.commit()

    # 4) Languages - tillar jadvali
    sql.execute("""
    CREATE TABLE IF NOT EXISTS languages (
        code TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        flag TEXT,
        is_active BOOLEAN DEFAULT TRUE
    )""")
    db.commit()

    # 5) User Languages - foydalanuvchi tillari
    sql.execute("""
    CREATE TABLE IF NOT EXISTS user_languages (
        user_id BIGINT PRIMARY KEY,
        from_lang TEXT DEFAULT 'en',
        to_lang TEXT DEFAULT 'uz',
        updated_at TIMESTAMP DEFAULT now(),
        FOREIGN KEY (from_lang) REFERENCES languages(code) ON DELETE SET NULL,
        FOREIGN KEY (to_lang) REFERENCES languages(code) ON DELETE SET NULL
    )""")
    db.commit()

    # 6) Vocab Books - lug'atlar jadvali (yaxshilangan)
    sql.execute("""
    CREATE TABLE IF NOT EXISTS vocab_books (
        id SERIAL PRIMARY KEY,
        user_id BIGINT NOT NULL,
        name VARCHAR(200) NOT NULL,
        description TEXT,
        src_lang VARCHAR(10) DEFAULT 'en',
        trg_lang VARCHAR(10) DEFAULT 'uz',
        is_public BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT now(),
        updated_at TIMESTAMP DEFAULT now(),
        CONSTRAINT uq_user_book UNIQUE (user_id, name)
    )""")

    # Indekslar
    sql.execute("""
    CREATE INDEX IF NOT EXISTS idx_vocab_books_user ON vocab_books(user_id);
    CREATE INDEX IF NOT EXISTS idx_vocab_books_public ON vocab_books(is_public) WHERE is_public = TRUE;
    CREATE INDEX IF NOT EXISTS idx_vocab_books_created ON vocab_books(created_at DESC);
    """)
    db.commit()

    # 7) Vocab Entries - so'zlar jadvali (yaxshilangan)
    sql.execute("""
    CREATE TABLE IF NOT EXISTS vocab_entries (
        id SERIAL PRIMARY KEY,
        book_id INTEGER NOT NULL,
        word_src TEXT NOT NULL,
        word_trg TEXT NOT NULL,
        src_lang VARCHAR(10),
        trg_lang VARCHAR(10),
        position INTEGER DEFAULT 0,
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT now(),
        updated_at TIMESTAMP DEFAULT now(),
        CONSTRAINT fk_entries_book FOREIGN KEY (book_id) REFERENCES vocab_books(id) ON DELETE CASCADE,
        CONSTRAINT uq_entry UNIQUE (book_id, word_src, word_trg)
    )""")

    # Indekslar
    sql.execute("""
    CREATE INDEX IF NOT EXISTS idx_vocab_entries_book ON vocab_entries(book_id);
    CREATE INDEX IF NOT EXISTS idx_vocab_entries_active ON vocab_entries(is_active) WHERE is_active = TRUE;
    CREATE INDEX IF NOT EXISTS idx_vocab_entries_created ON vocab_entries(created_at DESC);
    """)
    db.commit()

    # 8) Practice Sessions - mashq sessiyalari jadvali (yaxshilangan)
    sql.execute("""
    CREATE TABLE IF NOT EXISTS practice_sessions (
        id SERIAL PRIMARY KEY,
        user_id BIGINT NOT NULL,
        book_id INTEGER,
        session_type VARCHAR(50) DEFAULT 'personal', -- 'personal' yoki 'public'
        started_at TIMESTAMP DEFAULT now(),
        finished_at TIMESTAMP,
        total_questions INTEGER DEFAULT 0,
        correct_count INTEGER DEFAULT 0,
        wrong_count INTEGER DEFAULT 0,
        accuracy_percentage DECIMAL(5,2) DEFAULT 0,
        time_spent_seconds INTEGER DEFAULT 0,
        meta JSONB DEFAULT '{}'::jsonb,
        CONSTRAINT fk_session_book FOREIGN KEY (book_id) REFERENCES vocab_books(id) ON DELETE SET NULL
    )""")

    # Indekslar
    sql.execute("""
    CREATE INDEX IF NOT EXISTS idx_practice_sessions_user ON practice_sessions(user_id);
    CREATE INDEX IF NOT EXISTS idx_practice_sessions_book ON practice_sessions(book_id);
    CREATE INDEX IF NOT EXISTS idx_practice_sessions_started ON practice_sessions(started_at DESC);
    CREATE INDEX IF NOT EXISTS idx_practice_sessions_type ON practice_sessions(session_type);
    """)
    db.commit()

    # 9) Practice Questions - mashq savollari jadvali (yaxshilangan)
    sql.execute("""
    CREATE TABLE IF NOT EXISTS practice_questions (
        id SERIAL PRIMARY KEY,
        session_id INTEGER NOT NULL,
        entry_id INTEGER,
        presented_text TEXT NOT NULL,
        correct_translation TEXT NOT NULL,
        choices JSONB,
        chosen_option TEXT,
        is_correct BOOLEAN,
        response_time_ms INTEGER DEFAULT 0,
        asked_at TIMESTAMP DEFAULT now(),
        answered_at TIMESTAMP,
        CONSTRAINT fk_question_session FOREIGN KEY (session_id) REFERENCES practice_sessions(id) ON DELETE CASCADE,
        CONSTRAINT fk_question_entry FOREIGN KEY (entry_id) REFERENCES vocab_entries(id) ON DELETE SET NULL
    )""")

    # Indekslar
    sql.execute("""
    CREATE INDEX IF NOT EXISTS idx_practice_questions_session ON practice_questions(session_id);
    CREATE INDEX IF NOT EXISTS idx_practice_questions_entry ON practice_questions(entry_id);
    CREATE INDEX IF NOT EXISTS idx_practice_questions_asked ON practice_questions(asked_at DESC);
    """)
    db.commit()

    # 10) User Statistics - foydalanuvchi statistikalari jadvali
    sql.execute("""
    CREATE TABLE IF NOT EXISTS user_statistics (
        id SERIAL PRIMARY KEY,
        user_id BIGINT NOT NULL UNIQUE,
        total_words_learned INTEGER DEFAULT 0,
        total_practice_sessions INTEGER DEFAULT 0,
        total_questions_answered INTEGER DEFAULT 0,
        total_correct_answers INTEGER DEFAULT 0,
        average_accuracy DECIMAL(5,2) DEFAULT 0,
        total_study_time_minutes INTEGER DEFAULT 0,
        streak_days INTEGER DEFAULT 0,
        last_practice_date DATE,
        created_at TIMESTAMP DEFAULT now(),
        updated_at TIMESTAMP DEFAULT now()
    )""")

    sql.execute("""
    CREATE INDEX IF NOT EXISTS idx_user_statistics_user ON user_statistics(user_id);
    """)
    db.commit()

    # 11) Book Statistics - lug'at statistikalari
    sql.execute("""
    CREATE TABLE IF NOT EXISTS book_statistics (
        id SERIAL PRIMARY KEY,
        book_id INTEGER NOT NULL UNIQUE,
        total_practices INTEGER DEFAULT 0,
        total_users_practiced INTEGER DEFAULT 0,
        average_accuracy DECIMAL(5,2) DEFAULT 0,
        difficulty_level VARCHAR(20) DEFAULT 'medium', -- easy, medium, hard
        updated_at TIMESTAMP DEFAULT now(),
        CONSTRAINT fk_book_stats FOREIGN KEY (book_id) REFERENCES vocab_books(id) ON DELETE CASCADE
    )""")

    sql.execute("""
    CREATE INDEX IF NOT EXISTS idx_book_statistics_book ON book_statistics(book_id);
    """)
    db.commit()

    print("✅ Barcha jadvallar muvaffaqiyatli yaratildi!")
    try:
        await create_parallel_tables()
        await init_parallel_series()
        print("✅ Parallel tarjimalar jadvallari yaratildi")
    except Exception as e:
        print(f"⚠️ Parallel jadvallar yaratishda xato: {e}")

    print("✅ Barcha jadvallar muvaffaqiyatli yaratildi!")

def init_languages_table():
    """Tillar jadvalini ma'lumotlar bilan to'ldirish."""
    sql.execute("SELECT COUNT(*) FROM languages;")
    count = sql.fetchone()[0]

    if count == 0:
        print("📚 Tillar bazaga qo'shilmoqda...")
        for code, data in LANGUAGES.items():
            sql.execute(
                "INSERT INTO languages (code, name, flag) VALUES (%s, %s, %s) ON CONFLICT (code) DO NOTHING;",
                (code, data["name"], data["flag"])
            )
        db.commit()
        print(f"✅ {len(LANGUAGES)} ta til qo'shildi.")
        return True
    else:
        print(f"ℹ️ {count} ta til allaqachon mavjud.")
        return False

def create_indexes_and_constraints():
    """Qo'shimcha indekslar va cheklovlar qo'shish."""

    # Qo'shimcha indekslar
    additional_indexes = [
        "CREATE INDEX IF NOT EXISTS idx_vocab_books_name ON vocab_books(name);",
        "CREATE INDEX IF NOT EXISTS idx_vocab_entries_word_src ON vocab_entries(word_src);",
        "CREATE INDEX IF NOT EXISTS idx_practice_sessions_accuracy ON practice_sessions(accuracy_percentage DESC);",
        "CREATE INDEX IF NOT EXISTS idx_user_statistics_streak ON user_statistics(streak_days DESC);",
    ]

    for index_sql in additional_indexes:
        try:
            sql.execute(index_sql)
            db.commit()
        except Exception as e:
            print(f"⚠️ Index yaratishda xato: {e}")

    print("✅ Qo'shimcha indekslar yaratildi!")
