from aiogram import Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
import random
from math import ceil
from pathlib import Path
import re
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

DIFFICULTY_LEVELS = {
    1: "Beginner",
    2: "Elementary",
    3: "Intermediate",
    4: "Upper-Intermediate",
    5: "Advanced"
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

    # Parallel units jadvali
    await db_exec("""
                  CREATE TABLE IF NOT EXISTS parallel_units
                  (
                      id
                      SERIAL
                      PRIMARY
                      KEY,
                      series_id
                      INTEGER
                      NOT
                      NULL,
                      unit_number
                      INTEGER
                      NOT
                      NULL,
                      title
                      VARCHAR
                  (
                      200
                  ),
                      difficulty_level INTEGER DEFAULT 1,
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
                      ON DELETE CASCADE
                      )
                  """)

    # Unique constraint alohida qo'shish (agar mavjud bo'lmasa)
    await db_exec("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint 
                WHERE conname = 'uq_series_unit')
            ) THEN
                ALTER TABLE parallel_units 
                ADD CONSTRAINT uq_series_unit UNIQUE (series_id, unit_number);
            END IF;
        END $$;
    """)

    # Parallel entries jadvali
    await db_exec("""
                  CREATE TABLE IF NOT EXISTS parallel_entries
                  (
                      id
                      SERIAL
                      PRIMARY
                      KEY,
                      unit_id
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
                      frequency_score INTEGER DEFAULT 0,
                      is_active BOOLEAN DEFAULT TRUE,
                      created_at TIMESTAMP DEFAULT now
                  (
                  ),
                      CONSTRAINT fk_parallel_unit
                      FOREIGN KEY
                  (
                      unit_id
                  ) REFERENCES parallel_units
                  (
                      id
                  )
                      ON DELETE CASCADE
                      )
                  """)

    # Indekslar (IF NOT EXISTS bilan)
    await db_exec("""
                  CREATE INDEX IF NOT EXISTS idx_parallel_units_series
                      ON parallel_units(series_id);
                  """)

    await db_exec("""
                  CREATE INDEX IF NOT EXISTS idx_parallel_entries_unit
                      ON parallel_entries(unit_id);
                  """)

    await db_exec("""
                  CREATE INDEX IF NOT EXISTS idx_parallel_entries_category
                      ON parallel_entries(category);
                  """)

    await db_exec("""
                  CREATE INDEX IF NOT EXISTS idx_parallel_entries_frequency
                      ON parallel_entries(frequency_score DESC);
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


def parse_parallel_json(file_path: str, src_lang: str, trg_lang: str) -> list:
    """Parallel JSON faylni parse qilish va ma'lumotlarni qaytarish."""
    entries = []

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    for category, items in data.items():
        for item in items:
            if src_lang in item and trg_lang in item:
                word_src = item[src_lang].strip()
                word_trg = item[trg_lang].strip()
                word_trg2 = None  # Agar kerak bo'lsa, boshqa tilni qo'shish mumkin

                if category and word_src and word_trg:
                    entries.append({
                        'category': category,
                        'word_src': word_src,
                        'word_trg': word_trg,
                        'word_trg2': word_trg2
                    })

    return entries


def calculate_difficulty(entries: list, start_idx: int, end_idx: int) -> int:
    """So'zlar murakkablik darajasini hisoblash."""
    chunk = entries[start_idx:end_idx]

    # O'rtacha so'z uzunligi asosida
    avg_length = sum(len(e['word_src'].split()) for e in chunk) / len(chunk)

    if avg_length < 1.5:
        return 1  # Beginner
    elif avg_length < 2.5:
        return 2  # Elementary
    elif avg_length < 4:
        return 3  # Intermediate
    elif avg_length < 6:
        return 4  # Upper-Intermediate
    else:
        return 5  # Advanced


def optimize_and_group_entries(entries: list, words_per_unit: int = 50) -> list:
    """So'zlarni optimallash va guruhlash."""

    # 1. Takrorlarni olib tashlash
    unique_entries = []
    seen = set()

    for entry in entries:
        key = f"{entry['word_src']}:{entry['word_trg']}"
        if key not in seen:
            seen.add(key)
            unique_entries.append(entry)

    # 2. Chastota ball berish (kategoriya va so'z uzunligiga qarab)
    category_freq = {}
    for entry in unique_entries:
        cat = entry['category']
        category_freq[cat] = category_freq.get(cat, 0) + 1

    for entry in unique_entries:
        word_length = len(entry['word_src'].split())
        cat_freq = category_freq.get(entry['category'], 0)

        # Oddiy formulaga asoslangan ball
        entry['frequency_score'] = (cat_freq * 10) + (10 - min(word_length, 10))

    # 3. Ball bo'yicha saralash (yuqori ball = oddiy, ko'p uchraydigan)
    sorted_entries = sorted(unique_entries, key=lambda x: x['frequency_score'], reverse=True)

    # 4. Unitlarga ajratish
    units = []
    for i in range(0, len(sorted_entries), words_per_unit):
        chunk = sorted_entries[i:i + words_per_unit]
        if len(chunk) >= 20:  # Kamida 20 ta so'z bo'lishi kerak
            difficulty = calculate_difficulty(sorted_entries, i, min(i + words_per_unit, len(sorted_entries)))
            units.append({
                'words': chunk,
                'difficulty': difficulty,
                'word_count': len(chunk)
            })

    return units


async def import_parallel_files(series_code: str, file_paths: list, admin_id: int) -> dict:
    """Parallel fayllarni bazaga import qilish."""

    # Series ID olish
    series = await db_exec(
        "SELECT id FROM parallel_series WHERE code = %s",
        (series_code,), fetch=True
    )

    if not series:
        return {"success": False, "error": "Series topilmadi"}

    series_id = series['id']

    # Barcha fayllardan ma'lumotlarni yig'ish
    all_entries = []
    src_lang = PARALLEL_SERIES[series_code]["src_lang"]
    trg_lang = PARALLEL_SERIES[series_code]["trg_lang"]
    for file_path in file_paths:
        if Path(file_path).exists():
            entries = parse_parallel_json(file_path, src_lang, trg_lang)
            all_entries.extend(entries)

    if not all_entries:
        return {"success": False, "error": "Fayllar bo'sh yoki xato"}

    # Unitlarga guruhlash
    units = optimize_and_group_entries(all_entries)
    if not units:
        return {"success": False, "error": "Yetarli so'z topilmadi"}

    total_words = 0
    total_units = len(units)

    # Avvalgi unitlarni o'chirish
    await db_exec(
        "DELETE FROM parallel_units WHERE series_id = %s",
        (series_id,)
    )

    for unit_num, unit in enumerate(units, 1):
        title = f"Unit {unit_num} - {DIFFICULTY_LEVELS[unit['difficulty']]}"

        # Unit qo'shish
        unit_id = await db_exec("""
            INSERT INTO parallel_units
            (series_id, unit_number, title, difficulty_level, word_count)
            VALUES (%s, %s, %s, %s, %s) RETURNING id
        """, (series_id, unit_num, title, unit['difficulty'], unit['word_count']), fetch=True)

        unit_id = unit_id['id']

        # Entries qo'shish
        for pos, word in enumerate(unit['words'], 1):
            await db_exec("""
                INSERT INTO parallel_entries
                (unit_id, category, word_src, word_trg, word_trg2, position, frequency_score)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (unit_id, word['category'], word['word_src'], word['word_trg'],
                  word.get('word_trg2'), pos, word['frequency_score']))

        total_words += unit['word_count']

    return {
        "success": True,
        "units": total_units,
        "words": total_words
    }


@parallel_router.message(lambda m: m.text == "📚 Parallellarni kirgizish" and m.from_user.id in ADMIN_ID)
async def cmd_import_parallel(msg: Message):
    """Parallel fayllarni import qilish."""

    current_dir = Path(__file__).parent
    parallel_folder = current_dir / "parallel"
    if not parallel_folder.exists():
        await msg.answer("❌ Parallel folder topilmadi!")
        return

    await msg.answer("⏳ Parallel tarjimalar import qilinmoqda...")

    results = []
    total_words = 0
    total_units = 0

    # JSON fayl yo'li
    json_file = str(parallel_folder / "q1.json")

    # Har bir seriya uchun
    for series_code, info in PARALLEL_SERIES.items():
        file_paths = [json_file]
        if Path(json_file).exists():
            result = await import_parallel_files(series_code, file_paths, msg.from_user.id)

            if result["success"]:
                results.append(
                    f"✅ {info['name']}: {result['units']} unit, {result['words']} so'z")
                total_words += result["words"]
                total_units += result["units"]
            else:
                results.append(f"❌ {info['name']}: {result['error']}")
        else:
            results.append(f"⚠️ {info['name']}: q1.json topilmadi")

    # Natijani yuborish
    result_text = "📚 Parallel tarjimalar import natijasi:\n\n"
    result_text += "\n".join(results)
    result_text += f"\n\n📊 Jami: {total_units} unit, {total_words} so'z"

    await msg.answer(result_text)


# Admin buyrug'ida qo'shing
@parallel_router.message(lambda m: m.text == "qaytatdan" and m.from_user.id in ADMIN_ID)
async def cmd_recreate_tables(msg: Message):
    """Jadvallarni qayta yaratish."""
    try:
        await db_exec("DROP TABLE IF EXISTS parallel_entries CASCADE")
        await db_exec("DROP TABLE IF EXISTS parallel_units CASCADE")
        await db_exec("DROP TABLE IF EXISTS parallel_series CASCADE")

        await msg.answer("✅ Jadvallar muvaffaqiyatli qayta yaratildi!")
    except Exception as e:
        await msg.answer(f"❌ Xatolik: {e}")


async def get_unit_words(unit_id: int) -> list:
    """Unitdagi so'zlarni olish."""
    words = await db_exec("""
        SELECT word_src, word_trg, word_trg2
        FROM parallel_entries
        WHERE unit_id = %s AND is_active = TRUE
        ORDER BY position
    """, (unit_id,), fetch=True, many=True)
    return words or []


def parallel_main_kb(lang: str) -> InlineKeyboardMarkup:
    """Parallel asosiy menyu klaviaturasi."""
    L = get_locale(lang)
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=f"{PARALLEL_SERIES['uz_en']['icon']} {PARALLEL_SERIES['uz_en']['name']}",
                                 callback_data="parallel:series:uz_en"),
            InlineKeyboardButton(text=f"{PARALLEL_SERIES['uz_ru']['icon']} {PARALLEL_SERIES['uz_ru']['name']}",
                                 callback_data="parallel:series:uz_ru")
        ],
        [
            InlineKeyboardButton(text=f"{PARALLEL_SERIES['en_ru']['icon']} {PARALLEL_SERIES['en_ru']['name']}",
                                 callback_data="parallel:series:en_ru")
        ],
        [InlineKeyboardButton(text=L["back"], callback_data="cab:back")]
    ])


def parallel_units_kb(series_code: str, units: list, page: int, total_pages: int, lang: str) -> InlineKeyboardMarkup:
    """Parallel unitlar klaviaturasi."""
    L = get_locale(lang)
    rows = []
    for unit in units:
        title = unit.get('title', f"Unit {unit['unit_number']}")
        rows.append([
            InlineKeyboardButton(
                text=f"📖 {title} ({unit['word_count']}) ⭐{unit['difficulty_level']}",
                callback_data=f"parallel:unit:{unit['id']}"
            )
        ])

    # Sahifalash
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text=L["prev_page"], callback_data=f"parallel:series:{series_code}:{page-1}"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton(text=L["next_page"], callback_data=f"parallel:series:{series_code}:{page+1}"))
    if nav_row:
        rows.append(nav_row)

    rows.append([InlineKeyboardButton(text=L["back"], callback_data="parallel:main")])

    return InlineKeyboardMarkup(inline_keyboard=rows)


def start_parallel_practice_kb(lang: str) -> InlineKeyboardMarkup:
    """Mashqni boshlash klaviaturasi."""
    L = get_locale(lang)
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏁 Boshlash", callback_data="parallel:begin_practice")],
        [InlineKeyboardButton(text=L["back"], callback_data="parallel:main")]
    ])


async def send_next_parallel_question(message: Message, state: FSMContext, lang: str):
    """Keyingi savolni yuborish."""
    data = await state.get_data()
    index = data.get("index", 0)
    words = data.get("words", [])
    unit_title = data.get("unit_title", "Parallel Unit")
    total = data.get("total", 0)
    correct = data.get("correct", 0)
    wrong = data.get("wrong", 0)
    cycles = data.get("cycles", 0)
    current_cycle_correct = data.get("current_cycle_correct", 0)
    current_cycle_wrong = data.get("current_cycle_wrong", 0)

    L = get_locale(lang)

    if index >= total:
        # Tsikl tugadi
        cycles += 1
        cycles_stats = data.get("cycles_stats", [])
        cycles_stats.append({
            "cycle": cycles,
            "correct": current_cycle_correct,
            "wrong": current_cycle_wrong
        })

        if current_cycle_wrong == 0 or cycles >= 3:
            # Mashqni tugatish
            await message.answer(L["session_end"])
            await parallel_finish(message, state, lang)
            return

        # Yangi tsikl boshlash
        wrong_words = [w for w in words if 'answered_correctly' not in w]
        random.shuffle(wrong_words)
        await state.update_data(
            words=wrong_words,
            index=0,
            total=len(wrong_words),
            cycles=cycles,
            cycles_stats=cycles_stats,
            current_cycle_correct=0,
            current_cycle_wrong=0
        )
        index = 0
        words = wrong_words
        total = len(words)

        cycle_text = f"🔄 {cycles}-tsikl: Xatolar ustida ishlaymiz ({len(words)} ta)"
        await message.answer(cycle_text)

    current = words[index]
    question_text = f"📖 {unit_title}\n"
    question_text += f"🔄 Tsikllar: {cycles} | ✅ {correct} | ❌ {wrong}\n"
    question_text += f"❓ {current['word_src']}"

    # Variantlar tayyorlash
    choices = [current['word_trg']]
    all_trgs = set(w['word_trg'] for w in words)
    all_trgs.discard(current['word_trg'])
    choices.extend(random.sample(list(all_trgs), min(3, len(all_trgs))))
    random.shuffle(choices)

    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for choice in choices:
        kb.inline_keyboard.append([
            InlineKeyboardButton(text=choice, callback_data=f"parallel_ans:{index}:{choice}")
        ])
    kb.inline_keyboard.append([
        InlineKeyboardButton(text=L["finish"], callback_data="parallel:finish")
    ])

    await message.answer(question_text, reply_markup=kb)


async def parallel_finish(message: Message, state: FSMContext, lang: str):
    """Mashqni yakunlash."""
    data = await state.get_data()
    total_unique = data.get("total", 0)
    total_answers = data.get("answers", 0)
    total_correct = data.get("correct", 0)
    total_wrong = data.get("wrong", 0)
    unit_title = data.get("unit_title", "Parallel Unit")
    cycles = data.get("cycles", 0)
    cycles_stats = data.get("cycles_stats", [])

    percent = (total_correct / total_answers * 100) if total_answers else 0.0

    L = get_locale(lang)

    full_text = f"📖 {unit_title}\n"
    full_text += L["results_header"] + "\n\n"
    full_text += L["results_lines"].format(unique=total_unique, answers=total_answers,
                                           correct=total_correct, wrong=total_wrong, percent=percent)

    if cycles > 0:
        full_text += f"\n🔄 Jami tsikllar: {cycles}"
        for stat in cycles_stats:
            full_text += f"\n   - Tsikl {stat['cycle']}: ✅ {stat['correct']} | ❌ {stat['wrong']}"

    # Motivatsion xabar
    if percent >= 90:
        full_text += "\n\n🎉 Mukammal! Siz bu unitni juda yaxshi bilasiz!"
    elif percent >= 80:
        full_text += "\n\n⭐ Ajoyib natija! Davom eting!"
    elif percent >= 70:
        full_text += "\n\n👍 Yaxshi natija! Yanada yaxshilashga harakat qiling!"
    elif percent >= 50:
        full_text += "\n\n💪 Yomon emas! Yana mashq qiling!"
    else:
        full_text += "\n\n📚 Mashq davom eting, har gal yaxshilashasiz!"

    await state.clear()
    await message.answer(full_text)
    await message.answer(L["cabinet"], reply_markup=cabinet_kb(lang))


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
    """Parallel seriya units ro'yxati."""
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

    # Units ro'yxatini olish
    offset = page * BOOKS_PER_PAGE
    units = await db_exec("""
                          SELECT id, unit_number, word_count, difficulty_level, title
                          FROM parallel_units
                          WHERE series_id = %s
                            AND is_active = TRUE
                          ORDER BY unit_number
                              LIMIT %s
                          OFFSET %s
                          """, (series['id'], BOOKS_PER_PAGE, offset), fetch=True, many=True)

    total_count = await db_exec(
        "SELECT COUNT(*) as count FROM parallel_units WHERE series_id = %s AND is_active = TRUE",
        (series['id'],), fetch=True
    )

    total = total_count.get('count', 0) if total_count else 0

    if not units and page == 0:
        await cb.answer("❌ Bu seriyada unitlar mavjud emas!", show_alert=True)
        return

    total_pages = ceil(total / BOOKS_PER_PAGE)
    kb = parallel_units_kb(series_code, units, page, total_pages, lang)

    header_text = f"{series['icon']} {series['name']}\n📊 Jami {total} ta unit"
    if total_pages > 1:
        header_text += f"\n📄 {page + 1}/{total_pages} sahifa"

    await safe_edit_or_send(cb, header_text, kb, lang)
    await cb.answer()


@parallel_router.callback_query(lambda c: c.data and c.data.startswith("parallel:unit:"))
async def cb_parallel_unit_practice(cb: CallbackQuery, state: FSMContext):
    """Parallel unit bilan mashq boshlash."""
    unit_id = int(cb.data.split(":")[2])
    user_id = cb.from_user.id

    unit_info = await db_exec("""
                              SELECT pu.unit_number,
                                     pu.title,
                                     pu.word_count,
                                     pu.difficulty_level,
                                     ps.name as series_name,
                                     ps.icon
                              FROM parallel_units pu
                                       JOIN parallel_series ps ON pu.series_id = ps.id
                              WHERE pu.id = %s
                                AND pu.is_active = TRUE
                              """, (unit_id,), fetch=True)

    if not unit_info:
        await cb.answer("❌ Unit topilmadi!", show_alert=True)
        return

    words = await get_unit_words(unit_id)

    if len(words) < 4:
        await cb.answer("❌ Bu unitda yetarli so'z yo'q (kamida 4 ta kerak)!", show_alert=True)
        return

    user_data = await get_user_data(user_id)
    lang = user_data["lang"]

    # So'zlar ro'yxatini tayyorlash
    difficulty_name = DIFFICULTY_LEVELS.get(unit_info['difficulty_level'], 'Unknown')
    unit_title = f"{unit_info['icon']} {unit_info['series_name']} - Unit {unit_info['unit_number']}"

    words_list = []
    for idx, word in enumerate(words, 1):
        trg_text = word['word_trg']
        if word.get('word_trg2'):
            trg_text += f" / {word['word_trg2']}"
        words_list.append(f"{idx}. <b>{word['word_src']}</b> - {trg_text}")

    words_text = f"📖 <b>{unit_title}</b>\n"
    words_text += f"⭐ Daraja: {difficulty_name}\n"
    words_text += f"📊 Jami: {len(words)} ta so'z\n\n"
    words_text += "\n".join(words_list)
    words_text += "\n\n💡 So'zlarni ko'rib chiqing va tayyor bo'lganingizda mashqni boshlang!"

    random.shuffle(words)
    await state.update_data(
        unit_id=unit_id,
        unit_title=unit_title,
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
        current['answered_correctly'] = True
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
    unit_title = data.get("unit_title", "Parallel Unit")
    cycles = data.get("cycles", 0)

    percent = (total_correct / total_answers * 100) if total_answers else 0.0

    user_data = await get_user_data(cb.from_user.id)
    L = get_locale(user_data["lang"])

    full_text = f"📖 {unit_title}\n"
    full_text += L["results_header"] + "\n\n"
    full_text += L["results_lines"].format(unique=total_unique, answers=total_answers, correct=total_correct, wrong=total_wrong, percent=percent)

    if cycles > 0:
        full_text += f"\n🔄 Takrorlangan tsikllar: {cycles}"

    # Motivatsion xabar
    if percent >= 90:
        full_text += "\n\n🎉 Mukammal! Siz bu unitni juda yaxshi bilasiz!"
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