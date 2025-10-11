from aiogram import Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
import random
from math import ceil
from pathlib import Path
import json

from src.handlers.users.lughatlar.vocabs import (
    get_user_data, db_exec, get_locale, safe_edit_or_send,
    cabinet_kb, BOOKS_PER_PAGE
)
from config import ADMIN_ID

parallel_router = Router()

# =====================================================
# 📌 Constants
# =====================================================
PARALLEL_SERIES = {
    "uz_en": {"name": "O'zbek-Ingliz", "src_lang": "uz", "trg_lang": "en", "icon": "🇺🇿🇬🇧"},
    "uz_ru": {"name": "O'zbek-Rus", "src_lang": "uz", "trg_lang": "ru", "icon": "🇺🇿🇷🇺"},
    "en_ru": {"name": "Ingliz-Rus", "src_lang": "en", "trg_lang": "ru", "icon": "🇬🇧🇷🇺"}
}

# Mavzular darajalari (mavzu nomiga qarab)
TOPIC_DIFFICULTY = {
    "Greetings": 1,
    "Family": 2,
    "Food": 2,
    "Travel": 3,
    "Business": 4,
    "Technology": 4,
    "default": 2
}


# =====================================================
# 📌 FSM States
# =====================================================
class ParallelStates(StatesGroup):
    practicing = State()
    ready_to_start = State()


# =====================================================
# 📌 Database functions
# =====================================================
async def create_parallel_tables():
    """Parallel tarjimalar uchun jadvallar yaratish."""

    # Parallel series jadvali
    await db_exec("""
                  CREATE TABLE IF NOT EXISTS parallel_series
                  (
                      id
                      SERIAL
                      PRIMARY
                      KEY,
                      code
                      VARCHAR
                  (
                      20
                  ) UNIQUE NOT NULL,
                      name VARCHAR
                  (
                      200
                  ) NOT NULL,
                      src_lang VARCHAR
                  (
                      10
                  ) NOT NULL,
                      trg_lang VARCHAR
                  (
                      10
                  ) NOT NULL,
                      icon VARCHAR
                  (
                      20
                  ),
                      is_active BOOLEAN DEFAULT TRUE,
                      created_at TIMESTAMP DEFAULT now
                  (
                  )
                      )
                  """)

    # Parallel topics jadvali (units o'rniga topics)
    await db_exec("""
                  CREATE TABLE IF NOT EXISTS parallel_topics
                  (
                      id
                      SERIAL
                      PRIMARY
                      KEY,
                      series_id
                      INTEGER
                      NOT
                      NULL,
                      topic_name
                      VARCHAR
                  (
                      200
                  ) NOT NULL,
                      display_name VARCHAR
                  (
                      200
                  ),
                      difficulty_level INTEGER DEFAULT 2,
                      word_count INTEGER DEFAULT 0,
                      is_active BOOLEAN DEFAULT TRUE,
                      created_at TIMESTAMP DEFAULT now
                  (
                  ),
                      CONSTRAINT fk_parallel_series
                      FOREIGN KEY
                  (
                      series_id
                  ) REFERENCES parallel_series
                  (
                      id
                  )
                      ON DELETE CASCADE,
                      CONSTRAINT uq_series_topic UNIQUE
                  (
                      series_id,
                      topic_name
                  )
                      )
                  """)

    # Parallel entries jadvali
    await db_exec("""
                  CREATE TABLE IF NOT EXISTS parallel_entries
                  (
                      id
                      SERIAL
                      PRIMARY
                      KEY,
                      topic_id
                      INTEGER
                      NOT
                      NULL,
                      category
                      VARCHAR
                  (
                      100
                  ),
                      word_src TEXT NOT NULL,
                      word_trg TEXT NOT NULL,
                      word_trg2 TEXT,
                      position INTEGER DEFAULT 0,
                      is_active BOOLEAN DEFAULT TRUE,
                      created_at TIMESTAMP DEFAULT now
                  (
                  ),
                      CONSTRAINT fk_parallel_topic
                      FOREIGN KEY
                  (
                      topic_id
                  ) REFERENCES parallel_topics
                  (
                      id
                  )
                      ON DELETE CASCADE
                      )
                  """)

    # Indekslar (IF NOT EXISTS bilan)
    await db_exec("""
                  CREATE INDEX IF NOT EXISTS idx_parallel_topics_series
                      ON parallel_topics(series_id);
                  """)

    await db_exec("""
                  CREATE INDEX IF NOT EXISTS idx_parallel_entries_topic
                      ON parallel_entries(topic_id);
                  """)

    await db_exec("""
                  CREATE INDEX IF NOT EXISTS idx_parallel_entries_category
                      ON parallel_entries(category);
                  """)


async def init_parallel_series():
    """Parallel seriyalarni bazaga kiritish."""
    for code, info in PARALLEL_SERIES.items():
        await db_exec("""
                      INSERT INTO parallel_series (code, name, src_lang, trg_lang, icon)
                      VALUES (%s, %s, %s, %s, %s) ON CONFLICT (code) DO
                      UPDATE
                          SET name = EXCLUDED.name,
                          src_lang = EXCLUDED.src_lang,
                          trg_lang = EXCLUDED.trg_lang,
                          icon = EXCLUDED.icon
                      """, (code, info["name"], info["src_lang"], info["trg_lang"], info["icon"]))


def parse_parallel_json(file_path: str, series_code: str) -> dict:
    """JSON faylni parse qilish va mavzular bo'yicha guruhlab qaytarish."""
    topics_data = {}

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Seriya bo'yicha tillarni aniqlash
        if series_code == "uz_en":
            src_key, trg_key = "uz", "en"
        elif series_code == "uz_ru":
            src_key, trg_key = "uz", "ru"
        elif series_code == "en_ru":
            src_key, trg_key = "en", "ru"
        else:
            return topics_data

        # Har bir mavzuni alohida guruhlash
        for topic_name, items in data.items():
            entries = []
            for item in items:
                if src_key in item and trg_key in item:
                    entries.append({
                        'category': topic_name,
                        'word_src': item[src_key],
                        'word_trg': item[trg_key],
                        'word_trg2': item.get('ru') if series_code == "uz_en" else None
                    })

            if entries:  # Faqat bo'sh bo'lmagan mavzularni qo'shamiz
                topics_data[topic_name] = {
                    'entries': entries,
                    'word_count': len(entries),
                    'difficulty': TOPIC_DIFFICULTY.get(topic_name, TOPIC_DIFFICULTY['default'])
                }

    except Exception as e:
        print(f"JSON faylni o'qishda xato: {e}")

    return topics_data


def get_topic_display_name(topic_name: str) -> str:
    """Mavzu nomini chiroyli ko'rinishga o'tkazish."""
    display_names = {
        "Greetings": "Salomlashish",
        "Family": "Oila",
        "Food": "Ovqat",
        "Travel": "Sayohat",
        "Business": "Biznes",
        "Technology": "Texnologiya",
        "Shopping": "Xarid",
        "Health": "Sog'liq",
        "Education": "Ta'lim",
        "Work": "Ish"
    }
    return display_names.get(topic_name, topic_name)


def get_difficulty_icon(difficulty: int) -> str:
    """Daraja bo'yicha icon qaytarish."""
    icons = {
        1: "🟢",  # Beginner
        2: "🔵",  # Elementary
        3: "🟡",  # Intermediate
        4: "🟠",  # Upper-Intermediate
        5: "🔴"  # Advanced
    }
    return icons.get(difficulty, "⚪")


async def import_parallel_files(series_code: str, file_paths: list, admin_id: int) -> dict:
    """Parallel fayllarni bazaga import qilish (mavzular bo'yicha)."""

    # Series ID olish
    series = await db_exec(
        "SELECT id FROM parallel_series WHERE code = %s",
        (series_code,), fetch=True
    )

    if not series:
        return {"success": False, "error": "Series topilmadi"}

    series_id = series['id']

    # Barcha fayllardan ma'lumotlarni yig'ish
    all_topics = {}
    for file_path in file_paths:
        if Path(file_path).exists():
            topics_data = parse_parallel_json(file_path, series_code)
            # Mavzularni birlashtirish
            for topic_name, topic_info in topics_data.items():
                if topic_name in all_topics:
                    # Agar mavzu allaqachon mavjud bo'lsa, yangi so'zlarni qo'shamiz
                    all_topics[topic_name]['entries'].extend(topic_info['entries'])
                    all_topics[topic_name]['word_count'] += topic_info['word_count']
                else:
                    all_topics[topic_name] = topic_info

    if not all_topics:
        return {"success": False, "error": "Fayllar bo'sh yoki noto'g'ri format"}

    total_words = 0
    imported_topics = 0

    # Eski ma'lumotlarni o'chirish
    await db_exec("""
                  DELETE
                  FROM parallel_entries
                  WHERE topic_id IN (SELECT id
                                     FROM parallel_topics
                                     WHERE series_id = %s)
                  """, (series_id,))
    await db_exec("DELETE FROM parallel_topics WHERE series_id = %s", (series_id,))

    # Yangi mavzularni qo'shish
    for topic_name, topic_data in all_topics.items():
        try:
            # Topic yaratish
            display_name = get_topic_display_name(topic_name)
            difficulty = topic_data['difficulty']

            topic = await db_exec("""
                                  INSERT INTO parallel_topics
                                      (series_id, topic_name, display_name, difficulty_level, word_count)
                                  VALUES (%s, %s, %s, %s, %s) RETURNING id
                                  """, (series_id, topic_name, display_name, difficulty, topic_data['word_count']),
                                  fetch=True)

            topic_id = topic['id']

            # So'zlarni qo'shish
            word_count = 0
            for pos, entry in enumerate(topic_data['entries'], 1):
                try:
                    await db_exec("""
                                  INSERT INTO parallel_entries
                                      (topic_id, category, word_src, word_trg, word_trg2, position)
                                  VALUES (%s, %s, %s, %s, %s, %s)
                                  """, (topic_id, entry['category'], entry['word_src'],
                                        entry['word_trg'], entry.get('word_trg2'), pos))
                    word_count += 1
                except Exception as e:
                    print(f"So'z qo'shishda xato: {entry['word_src']} - {e}")
                    continue

            # Topic word_count yangilash (agar kerak bo'lsa)
            if word_count != topic_data['word_count']:
                await db_exec(
                    "UPDATE parallel_topics SET word_count = %s WHERE id = %s",
                    (word_count, topic_id)
                )

            total_words += word_count
            imported_topics += 1

        except Exception as e:
            print(f"Mavzu {topic_name} import qilishda xato: {e}")
            continue

    return {
        "success": True,
        "topics": imported_topics,
        "words": total_words,
        "series": series_code
    }


# =====================================================
# 📌 UI Builders
# =====================================================
def parallel_main_kb(lang: str) -> InlineKeyboardMarkup:
    """Parallel tarjimalar asosiy menyu."""
    L = get_locale(lang)

    buttons = []
    for code, info in PARALLEL_SERIES.items():
        text = f"{info['icon']} {info['name']}"
        buttons.append([InlineKeyboardButton(text=text, callback_data=f"parallel:series:{code}")])

    buttons.append([InlineKeyboardButton(text=L["back"], callback_data="cab:back")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def parallel_topics_kb(series_code: str, topics: list, page: int, total_pages: int, lang: str) -> InlineKeyboardMarkup:
    """Parallel topics ro'yxati klaviaturasi."""
    L = get_locale(lang)
    rows = []

    # Topics tugmalari
    for topic in topics:
        difficulty_icon = get_difficulty_icon(topic['difficulty_level'])
        display_name = topic['display_name'] or get_topic_display_name(topic['topic_name'])
        text = f"{difficulty_icon} {display_name} ({topic['word_count']})"
        callback = f"parallel:topic:{topic['id']}"
        rows.append([InlineKeyboardButton(text=text, callback_data=callback)])

    # Sahifalash
    if total_pages > 1:
        nav_row = []
        if page > 0:
            nav_row.append(InlineKeyboardButton(text=L["prev_page"],
                                                callback_data=f"parallel:series:{series_code}:{page - 1}"))
        if page < total_pages - 1:
            nav_row.append(InlineKeyboardButton(text=L["next_page"],
                                                callback_data=f"parallel:series:{series_code}:{page + 1}"))
        if nav_row:
            rows.append(nav_row)

        # Sahifa ma'lumoti
        page_info = L["page_info"].format(current=page + 1, total=total_pages)
        rows.append([InlineKeyboardButton(text=page_info, callback_data="noop")])

    rows.append([InlineKeyboardButton(text=L["back"], callback_data="parallel:main")])

    return InlineKeyboardMarkup(inline_keyboard=rows)


def start_parallel_practice_kb(lang: str) -> InlineKeyboardMarkup:
    """Mashqni boshlash klaviaturasi."""
    L = get_locale(lang)
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="▶️ Mashqni boshlash", callback_data="parallel:begin_practice")],
        [InlineKeyboardButton(text=L["back"], callback_data="parallel:main")]
    ])


# =====================================================
# 📌 Practice functions
# =====================================================
async def get_topic_words(topic_id: int) -> list:
    """Topic so'zlarini olish."""
    words = await db_exec("""
                          SELECT word_src, word_trg, word_trg2, category
                          FROM parallel_entries
                          WHERE topic_id = %s
                            AND is_active = TRUE
                          ORDER BY position
                          """, (topic_id,), fetch=True, many=True)

    return words or []


async def send_next_parallel_question(msg: Message, state: FSMContext, lang: str):
    """Parallel mashq savolini yuborish."""
    data = await state.get_data()
    words, index = data["words"], data["index"]
    L = get_locale(lang)

    if index >= len(words):
        cycles = data.get("cycles", 0) + 1
        cycles_stats = data.get("cycles_stats", [])
        cycles_stats.append({
            "correct": data.get("current_cycle_correct", 0),
            "wrong": data.get("current_cycle_wrong", 0)
        })
        random.shuffle(words)
        await state.update_data(
            words=words, index=0, cycles=cycles, cycles_stats=cycles_stats,
            current_cycle_correct=0, current_cycle_wrong=0
        )
        data = await state.get_data()
        index = 0

    current = data["words"][index]
    correct_answer = current["word_trg"]
    options = [correct_answer]
    seen = set(options)

    # Noto'g'ri javoblar qo'shish
    while len(options) < 4 and len(options) < len(data["words"]):
        candidate = random.choice(data["words"])["word_trg"]
        if candidate not in seen:
            options.append(candidate)
            seen.add(candidate)

    random.shuffle(options)

    kb_rows = [[InlineKeyboardButton(text=o, callback_data=f"parallel_ans:{index}:{o}")] for o in options]
    kb_rows.extend([
        [InlineKeyboardButton(text=L["finish"], callback_data="parallel:finish")],
        [InlineKeyboardButton(text=L["main_menu"], callback_data="cab:back")]
    ])
    kb = InlineKeyboardMarkup(inline_keyboard=kb_rows)

    # Progress ko'rsatish
    progress_text = f"📊 {data.get('correct', 0)}/{data.get('answers', 0)} to'g'ri"
    topic_title = data.get('topic_title', 'Parallel Topic')
    question_text = f"📖 {topic_title}\n\n<b>❓ {current['word_src']}</b>\n\n{progress_text}"

    try:
        await msg.edit_text(question_text, reply_markup=kb, parse_mode="html")
    except Exception:
        try:
            await msg.delete()
        except Exception:
            pass
        await msg.answer(question_text, reply_markup=kb, parse_mode="html")


# =====================================================
# 📌 Admin commands
# =====================================================
@parallel_router.message(lambda m: m.text == "📚 Parallellarni kirgizish" and m.from_user.id in ADMIN_ID)
async def cmd_import_parallels(msg: Message):
    """Parallel tarjimalarni import qilish."""

    await create_parallel_tables()
    await init_parallel_series()

    current_dir = Path(__file__).parent
    parallel_folder = current_dir / "parallel"

    if not parallel_folder.exists():
        await msg.answer("❌ 'parallel' papkasi topilmadi!")
        return

    await msg.answer("⏳ Parallel tarjimalar import qilinmoqda...")

    results = []
    total_words = 0
    total_topics = 0

    # Har bir seriya uchun
    for series_code, info in PARALLEL_SERIES.items():
        file_paths = []
        json_file = parallel_folder / "q1.json"
        if json_file.exists():
            file_paths.append(str(json_file))

        if file_paths:
            result = await import_parallel_files(series_code, file_paths, msg.from_user.id)

            if result["success"]:
                results.append(
                    f"✅ {info['name']}: {result['topics']} mavzu, {result['words']} so'z")
                total_words += result["words"]
                total_topics += result["topics"]
            else:
                results.append(f"❌ {info['name']}: {result['error']}")
        else:
            results.append(f"⚠️ {info['name']}: JSON fayl topilmadi")

    # Natijani yuborish
    result_text = "📚 Parallel tarjimalar import natijasi:\n\n"
    result_text += "\n".join(results)
    result_text += f"\n\n📊 Jami: {total_topics} mavzu, {total_words} so'z"

    await msg.answer(result_text)


# Admin buyrug'ida qo'shing
@parallel_router.message(lambda m: m.text == "qaytatdan" and m.from_user.id in ADMIN_ID)
async def cmd_recreate_tables(msg: Message):
    """Jadvallarni qayta yaratish."""
    try:
        await db_exec("DROP TABLE IF EXISTS parallel_entries CASCADE")
        await db_exec("DROP TABLE IF EXISTS parallel_topics CASCADE")
        await db_exec("DROP TABLE IF EXISTS parallel_series CASCADE")

        await msg.answer("✅ Jadvallar muvaffaqiyatli qayta yaratildi!")
    except Exception as e:
        await msg.answer(f"❌ Xatolik: {e}")


# =====================================================
# 📌 User handlers
# =====================================================
@parallel_router.callback_query(lambda c: c.data == "parallel:main")
async def cb_parallel_main(cb: CallbackQuery):
    """Parallel asosiy menyu."""
    user_data = await get_user_data(cb.from_user.id)
    lang = user_data["lang"]

    text = "📚 Parallel tarjimalar\n\n"
    text += "Turli tillarda so'zlarni parallel o'rganing va mashq qiling!"

    await safe_edit_or_send(cb, text, parallel_main_kb(lang), lang)
    await cb.answer()


@parallel_router.callback_query(lambda c: c.data and c.data.startswith("parallel:series:"))
async def cb_parallel_series(cb: CallbackQuery):
    """Parallel seriya topics ro'yxati."""
    parts = cb.data.split(":")
    series_code = parts[2]
    page = int(parts[3]) if len(parts) > 3 else 0

    user_data = await get_user_data(cb.from_user.id)
    lang = user_data["lang"]

    series = await db_exec(
        "SELECT id, name, icon FROM parallel_series WHERE code = %s AND is_active = TRUE",
        (series_code,), fetch=True
    )

    if not series:
        await cb.answer("❌ Series topilmadi!", show_alert=True)
        return

    # Topics ro'yxatini olish
    offset = page * BOOKS_PER_PAGE
    topics = await db_exec("""
                           SELECT id, topic_name, display_name, word_count, difficulty_level
                           FROM parallel_topics
                           WHERE series_id = %s
                             AND is_active = TRUE
                           ORDER BY topic_name
                               LIMIT %s
                           OFFSET %s
                           """, (series['id'], BOOKS_PER_PAGE, offset), fetch=True, many=True)

    total_count = await db_exec(
        "SELECT COUNT(*) as count FROM parallel_topics WHERE series_id = %s AND is_active = TRUE",
        (series['id'],), fetch=True
    )

    total = total_count.get('count', 0) if total_count else 0

    if not topics and page == 0:
        await cb.answer("❌ Bu seriyada mavzular mavjud emas!", show_alert=True)
        return

    total_pages = ceil(total / BOOKS_PER_PAGE)
    kb = parallel_topics_kb(series_code, topics, page, total_pages, lang)

    header_text = f"{series['icon']} {series['name']}\n📊 Jami {total} ta mavzu"
    if total_pages > 1:
        header_text += f"\n📄 {page + 1}/{total_pages} sahifa"

    await safe_edit_or_send(cb, header_text, kb, lang)
    await cb.answer()


@parallel_router.callback_query(lambda c: c.data and c.data.startswith("parallel:topic:"))
async def cb_parallel_topic_practice(cb: CallbackQuery, state: FSMContext):
    """Parallel topic bilan mashq boshlash."""
    topic_id = int(cb.data.split(":")[2])
    user_id = cb.from_user.id

    topic_info = await db_exec("""
                               SELECT pt.topic_name,
                                      pt.display_name,
                                      pt.word_count,
                                      pt.difficulty_level,
                                      ps.name as series_name,
                                      ps.icon
                               FROM parallel_topics pt
                                        JOIN parallel_series ps ON pt.series_id = ps.id
                               WHERE pt.id = %s
                                 AND pt.is_active = TRUE
                               """, (topic_id,), fetch=True)

    if not topic_info:
        await cb.answer("❌ Mavzu topilmadi!", show_alert=True)
        return

    words = await get_topic_words(topic_id)

    if len(words) < 4:
        await cb.answer("❌ Bu mavzuda yetarli so'z yo'q (kamida 4 ta kerak)!", show_alert=True)
        return

    user_data = await get_user_data(user_id)
    lang = user_data["lang"]

    # So'zlar ro'yxatini tayyorlash
    difficulty_icon = get_difficulty_icon(topic_info['difficulty_level'])
    display_name = topic_info['display_name'] or get_topic_display_name(topic_info['topic_name'])
    topic_title = f"{topic_info['icon']} {topic_info['series_name']} - {display_name}"

    words_list = []
    for idx, word in enumerate(words, 1):
        trg_text = word['word_trg']
        if word.get('word_trg2'):
            trg_text += f" / {word['word_trg2']}"
        words_list.append(f"{idx}. <b>{word['word_src']}</b> - {trg_text}")

    words_text = f"📖 <b>{topic_title}</b>\n"
    words_text += f"{difficulty_icon} Daraja: {topic_info['difficulty_level']}\n"
    words_text += f"📊 Jami: {len(words)} ta so'z\n\n"
    words_text += "\n".join(words_list)
    words_text += "\n\n💡 So'zlarni ko'rib chiqing va tayyor bo'lganingizda mashqni boshlang!"

    random.shuffle(words)
    await state.update_data(
        topic_id=topic_id,
        topic_title=topic_title,
        words=words,
        index=0,
        correct=0,
        wrong=0,
        total=len(words),
        answers=0,
        cycles=0,
        current_cycle_correct=0,
        current_cycle_wrong=0,
        cycles_stats=[]
    )
    await state.set_state(ParallelStates.ready_to_start)

    await safe_edit_or_send(cb, words_text, start_parallel_practice_kb(lang), lang)
    await cb.answer()


@parallel_router.callback_query(lambda c: c.data == "parallel:begin_practice")
async def cb_begin_parallel_practice(cb: CallbackQuery, state: FSMContext):
    """Mashqni boshlash."""
    current_state = await state.get_state()
    if current_state != ParallelStates.ready_to_start:
        await cb.answer("❌ Xato holat!", show_alert=True)
        return

    user_data = await get_user_data(cb.from_user.id)
    lang = user_data["lang"]

    await state.set_state(ParallelStates.practicing)

    try:
        await cb.message.delete()
    except:
        pass

    await send_next_parallel_question(cb.message, state, lang)
    await cb.answer()


@parallel_router.callback_query(lambda c: c.data and c.data.startswith("parallel_ans:"))
async def cb_parallel_answer(cb: CallbackQuery, state: FSMContext):
    """Javobni tekshirish."""
    data = await state.get_data()
    _, idx_str, chosen = cb.data.split(":", 2)
    idx = int(idx_str)

    if idx >= len(data["words"]):
        await cb.answer("❌ Xato", show_alert=True)
        return

    current = data["words"][idx]
    correct_answer = current["word_trg"]
    data["answers"] = data.get("answers", 0) + 1

    user_data = await get_user_data(cb.from_user.id)
    L = get_locale(user_data["lang"])

    if chosen == correct_answer:
        data["correct"] = data.get("correct", 0) + 1
        data["current_cycle_correct"] = data.get("current_cycle_correct", 0) + 1
        await cb.answer(L["correct"])
    else:
        data["wrong"] = data.get("wrong", 0) + 1
        data["current_cycle_wrong"] = data.get("current_cycle_wrong", 0) + 1
        await cb.answer(L["wrong"].format(correct=correct_answer), show_alert=True)

    data["index"] = idx + 1
    await state.update_data(**data)
    await send_next_parallel_question(cb.message, state, user_data["lang"])


@parallel_router.callback_query(lambda c: c.data == "parallel:finish")
async def cb_parallel_finish(cb: CallbackQuery, state: FSMContext):
    """Mashqni tugatish."""
    data = await state.get_data()
    total_unique = data.get("total", 0)
    total_answers = data.get("answers", 0)
    total_correct = data.get("correct", 0)
    total_wrong = data.get("wrong", 0)
    topic_title = data.get("topic_title", "Parallel Mavzu")
    cycles = data.get("cycles", 0)

    percent = (total_correct / total_answers * 100) if total_answers else 0.0

    user_data = await get_user_data(cb.from_user.id)
    L = get_locale(user_data["lang"])

    full_text = f"📖 {topic_title}\n"
    full_text += f"{L['results_header']}\n\n"
    full_text += f"{L['results_lines'].format(unique=total_unique, answers=total_answers, correct=total_correct, wrong=total_wrong, percent=percent)}"

    if cycles > 0:
        full_text += f"\n🔄 Takrorlangan tsikllar: {cycles}"

    # Motivatsional xabar
    if percent >= 90:
        full_text += "\n\n🎉 Mukammal! Siz bu mavzuni juda yaxshi bilasiz!"
    elif percent >= 80:
        full_text += "\n\n⭐ Ajoyib natija! Davom eting!"
    elif percent >= 70:
        full_text += "\n\n👍 Yaxshi natija! Yanada yaxshilashga harakat qiling!"
    elif percent >= 50:
        full_text += "\n\n💪 Yomon emas! Yana mashq qiling!"
    else:
        full_text += "\n\n📚 Mashq davom eting, har gal yaxshilashasiz!"

    await state.clear()

    try:
        await cb.message.delete()
    except:
        pass

    await cb.message.answer(full_text)
    await cb.message.answer(L["cabinet"], reply_markup=cabinet_kb(user_data["lang"]))
    await cb.answer()