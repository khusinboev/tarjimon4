import os
import re
from pathlib import Path
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ChatType
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
import random
from math import ceil

from src.handlers.users.lughatlar.vocabs import (
    get_user_data, db_exec, get_locale, safe_edit_or_send,
    cabinet_kb, BOOKS_PER_PAGE
)
from config import ADMIN_ID

essential_router = Router()

# =====================================================
# 📌 Essential kitoblar uchun constants
# =====================================================
ESSENTIAL_BOOKS = {
    "essential1": "Essential English Words 1",
    "essential2": "Essential English Words 2",
    "essential3": "Essential English Words 3",
    "essential4": "Essential English Words 4",
    "essential5": "Essential English Words 5"
}


# =====================================================
# 📌 FSM States
# =====================================================
class EssentialStates(StatesGroup):
    practicing = State()
    ready_to_start = State()  # Yangi holat: so'zlar ko'rsatildi, mashq boshlashga tayyor


# =====================================================
# 📌 Database helper functions
# =====================================================
async def create_essential_tables():
    """Essential kitoblar uchun jadvallar yaratish."""

    # Essential series jadvali
    await db_exec("""
                  CREATE TABLE IF NOT EXISTS essential_series
                  (
                      id SERIAL PRIMARY KEY, 
                      code VARCHAR
                  (
                      20
                  ) UNIQUE NOT NULL,
                      name VARCHAR
                  (
                      200
                  ) NOT NULL,
                      description TEXT,
                      level_order INTEGER DEFAULT 0,
                      is_active BOOLEAN DEFAULT TRUE,
                      created_at TIMESTAMP DEFAULT now
                  (
                  )
                      )
                  """)

    # Essential books jadvali
    await db_exec("""
                  CREATE TABLE IF NOT EXISTS essential_books
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
                      word_count INTEGER DEFAULT 0,
                      is_active BOOLEAN DEFAULT TRUE,
                      created_at TIMESTAMP DEFAULT now
                  (
                  ),
                      CONSTRAINT fk_essential_series FOREIGN KEY
                  (
                      series_id
                  ) REFERENCES essential_series
                  (
                      id
                  ) ON DELETE CASCADE,
                      CONSTRAINT uq_series_unit UNIQUE
                  (
                      series_id,
                      unit_number
                  )
                      )
                  """)

    # Essential entries jadvali
    await db_exec("""
                  CREATE TABLE IF NOT EXISTS essential_entries
                  (
                      id
                      SERIAL
                      PRIMARY
                      KEY,
                      book_id
                      INTEGER
                      NOT
                      NULL,
                      word_src
                      VARCHAR
                  (
                      255
                  ) NOT NULL,
                      word_trg VARCHAR
                  (
                      255
                  ) NOT NULL,
                      position INTEGER DEFAULT 0,
                      is_active BOOLEAN DEFAULT TRUE,
                      created_at TIMESTAMP DEFAULT now
                  (
                  ),
                      CONSTRAINT fk_essential_book FOREIGN KEY
                  (
                      book_id
                  ) REFERENCES essential_books
                  (
                      id
                  ) ON DELETE CASCADE,
                      CONSTRAINT uq_book_word UNIQUE
                  (
                      book_id,
                      word_src
                  )
                      )
                  """)

    # Indekslar
    await db_exec("""
                  CREATE INDEX IF NOT EXISTS idx_essential_books_series ON essential_books(series_id);
                  CREATE INDEX IF NOT EXISTS idx_essential_entries_book ON essential_entries(book_id);
                  CREATE INDEX IF NOT EXISTS idx_essential_entries_word ON essential_entries(word_src);
                  """)


async def init_essential_series():
    """Essential seriyalarni bazaga kiritish."""
    for i, (code, name) in enumerate(ESSENTIAL_BOOKS.items(), 1):
        await db_exec("""
                      INSERT INTO essential_series (code, name, level_order)
                      VALUES (%s, %s, %s) ON CONFLICT (code) DO NOTHING
                      """, (code, name, i))


# =====================================================
# 📌 File processing functions
# =====================================================
def parse_essential_file(file_path: str) -> dict:
    """Essential fayl mazmunini parse qilish."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        units = {}
        current_unit = None

        lines = content.strip().split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Unit sarlavhasini aniqlash
            unit_match = re.match(r'^Unit\s+(\d+)', line)
            if unit_match:
                current_unit = int(unit_match.group(1))
                units[current_unit] = []
                continue

            # So'z va tarjimasini ajratish
            if current_unit and ' - ' in line:
                parts = line.split(' - ', 1)
                if len(parts) == 2:
                    word = parts[0].strip()
                    translation = parts[1].strip()
                    if word and translation:
                        units[current_unit].append((word, translation))

        return units
    except Exception as e:
        logging.error(f"Fayl o'qishda xato: {e}")
        return {}


async def import_essential_file(series_code: str, file_path: str, admin_id: int) -> dict:
    """Essential faylini bazaga import qilish."""

    # Series ID olish
    series = await db_exec(
        "SELECT id FROM essential_series WHERE code = %s",
        (series_code,), fetch=True
    )

    if not series:
        return {"success": False, "error": "Series topilmadi"}

    series_id = series['id']

    # Faylni parse qilish
    units = parse_essential_file(file_path)

    if not units:
        return {"success": False, "error": "Fayl bo'sh yoki noto'g'ri format"}

    total_words = 0
    imported_units = 0

    for unit_num, words in units.items():
        try:
            # Unit uchun kitob yaratish yoki yangilash
            book = await db_exec("""
                                 INSERT INTO essential_books (series_id, unit_number, title, word_count)
                                 VALUES (%s, %s, %s, %s) ON CONFLICT (series_id, unit_number) 
                DO
                                 UPDATE SET word_count = EXCLUDED.word_count, created_at = now()
                                     RETURNING id
                                 """, (series_id, unit_num, f"Unit {unit_num}", len(words)), fetch=True)

            book_id = book['id']

            # Eski so'zlarni o'chirish
            await db_exec("DELETE FROM essential_entries WHERE book_id = %s", (book_id,))

            # Yangi so'zlarni qo'shish
            word_count = 0
            for pos, (word, translation) in enumerate(words, 1):
                try:
                    await db_exec("""
                                  INSERT INTO essential_entries (book_id, word_src, word_trg, position)
                                  VALUES (%s, %s, %s, %s)
                                  """, (book_id, word, translation, pos))
                    word_count += 1
                except Exception as e:
                    logging.warning(f"So'z qo'shishda xato: {word} - {e}")
                    continue

            # Kitob word_count yangilash
            await db_exec(
                "UPDATE essential_books SET word_count = %s WHERE id = %s",
                (word_count, book_id)
            )

            total_words += word_count
            imported_units += 1

        except Exception as e:
            logging.error(f"Unit {unit_num} import qilishda xato: {e}")
            continue

    return {
        "success": True,
        "units": imported_units,
        "words": total_words,
        "series": series_code
    }


# =====================================================
# 📌 UI Builders
# =====================================================
def essential_main_kb(lang: str) -> InlineKeyboardMarkup:
    """Essential asosiy menyu."""
    L = get_locale(lang)
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📚 Essential 1", callback_data="essential:series:essential1")],
        [InlineKeyboardButton(text="📗 Essential 2", callback_data="essential:series:essential2")],
        [InlineKeyboardButton(text="📘 Essential 3", callback_data="essential:series:essential3")],
        [InlineKeyboardButton(text="📙 Essential 4", callback_data="essential:series:essential4")],
        [InlineKeyboardButton(text="📕 Essential 5", callback_data="essential:series:essential5")],
        [InlineKeyboardButton(text=L["back"], callback_data="essential:back_to_cabinet")]
    ])


def essential_units_kb(series_code: str, units: list, page: int, total_pages: int, lang: str) -> InlineKeyboardMarkup:
    """Essential units ro'yxati klaviaturasi."""
    L = get_locale(lang)
    rows = []

    # Units tugmalari (2x2 formatda)
    unit_rows = []
    for i in range(0, len(units), 2):
        row = []
        for j in range(2):
            if i + j < len(units):
                unit = units[i + j]
                text = f"Unit {unit['unit_number']} ({unit['word_count']})"
                callback = f"essential:unit:{unit['id']}"
                row.append(InlineKeyboardButton(text=text, callback_data=callback))
        unit_rows.append(row)

    rows.extend(unit_rows)

    # Sahifalash tugmalari
    if total_pages > 1:
        nav_row = []
        if page > 0:
            nav_row.append(InlineKeyboardButton(text=L["prev_page"],
                                                callback_data=f"essential:series:{series_code}:{page - 1}"))
        if page < total_pages - 1:
            nav_row.append(InlineKeyboardButton(text=L["next_page"],
                                                callback_data=f"essential:series:{series_code}:{page + 1}"))
        if nav_row:
            rows.append(nav_row)

    rows.append([InlineKeyboardButton(text=L["back"], callback_data="essential:main")])

    return InlineKeyboardMarkup(inline_keyboard=rows)


def start_practice_kb(lang: str) -> InlineKeyboardMarkup:
    """Mashqni boshlash klaviaturasi."""
    L = get_locale(lang)
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="▶️ Mashqni boshlash", callback_data="essential:begin_practice")],
        [InlineKeyboardButton(text=L["back"], callback_data="essential:main")]
    ])


def essential_practice_kb(lang: str) -> InlineKeyboardMarkup:
    """Essential mashq klaviaturasi."""
    L = get_locale(lang)
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=L["finish"], callback_data="essential:finish")],
        [InlineKeyboardButton(text=L["main_menu"], callback_data="cab:back")]
    ])


# =====================================================
# 📌 Practice functions
# =====================================================
async def get_unit_words(unit_id: int) -> list:
    """Unit so'zlarini olish."""
    words = await db_exec("""
                          SELECT word_src, word_trg
                          FROM essential_entries
                          WHERE book_id = %s
                            AND is_active = TRUE
                          ORDER BY position
                          """, (unit_id,), fetch=True, many=True)

    return words or []


async def send_next_essential_question(msg: Message, state: FSMContext, lang: str):
    """Essential mashq savolini yuborish."""
    data = await state.get_data()
    words, index = data["words"], data["index"]
    L = get_locale(lang)

    if index >= len(words):
        # Tsikl tugadi, yangi tsikl boshlash
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

    kb_rows = [[InlineKeyboardButton(text=o, callback_data=f"essential_ans:{index}:{o}")] for o in options]
    kb_rows.extend([
        [InlineKeyboardButton(text=L["finish"], callback_data="essential:finish")],
        [InlineKeyboardButton(text=L["main_menu"], callback_data="cab:back")]
    ])
    kb = InlineKeyboardMarkup(inline_keyboard=kb_rows)

    # Progress ko'rsatish
    progress_text = f"📊 {data.get('correct', 0)}/{data.get('answers', 0)} to'g'ri"
    unit_title = data.get('unit_title', 'Essential Unit')
    question_text = f"📖 {unit_title}\n\n<b>❓ {current['word_src']}</b>\n\n{progress_text}"

    # Try to edit message first; if fails, delete and send new one
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
@essential_router.message(F.text == "📚 Kitoblarni kirgizish", F.from_user.id.in_(ADMIN_ID),
                          F.chat.type == ChatType.PRIVATE)
async def cmd_import_essentials(msg: Message):
    """Essential kitoblarni import qilish."""

    # Jadvallarni yaratish
    await create_essential_tables()
    await init_essential_series()

    # Essential papkasini topish
    current_dir = Path(__file__).parent
    essential_folder = current_dir / "essential"
    if not essential_folder.exists():
        await msg.answer("❌ 'essential' papkasi topilmadi!")
        return

    await msg.answer("⏳ Essential kitoblar import qilinmoqda...")

    imported_files = []
    total_words = 0
    total_units = 0

    # Barcha essential fayllarni import qilish
    for series_code in ESSENTIAL_BOOKS.keys():
        file_path = essential_folder / f"{series_code}.txt"

        if file_path.exists():
            result = await import_essential_file(series_code, str(file_path), msg.from_user.id)

            if result["success"]:
                imported_files.append(
                    f"✅ {ESSENTIAL_BOOKS[series_code]}: {result['units']} unit, {result['words']} so'z")
                total_words += result["words"]
                total_units += result["units"]
            else:
                imported_files.append(f"❌ {ESSENTIAL_BOOKS[series_code]}: {result['error']}")
        else:
            imported_files.append(f"⚠️ {series_code}.txt fayli topilmadi")

    # Natijani yuborish
    result_text = "📚 Essential kitoblar import natijasi:\n\n"
    result_text += "\n".join(imported_files)
    result_text += f"\n\n📊 Jami: {total_units} unit, {total_words} so'z"

    await msg.answer(result_text)


# =====================================================
# 📌 User handlers
# =====================================================
@essential_router.callback_query(lambda c: c.data == "essential:main")
async def cb_essential_main(cb: CallbackQuery):
    """Essential asosiy menyu."""
    user_data = await get_user_data(cb.from_user.id)
    lang = user_data["lang"]

    await safe_edit_or_send(cb, "📚 Essential English Words", essential_main_kb(lang), lang)
    await cb.answer()


@essential_router.callback_query(lambda c: c.data and c.data.startswith("essential:series:"))
async def cb_essential_series(cb: CallbackQuery):
    """Essential seriya units ro'yxati."""
    parts = cb.data.split(":")
    series_code = parts[2]
    page = int(parts[3]) if len(parts) > 3 else 0

    user_data = await get_user_data(cb.from_user.id)
    lang = user_data["lang"]

    # Series mavjudligini tekshirish
    series = await db_exec(
        "SELECT id, name FROM essential_series WHERE code = %s AND is_active = TRUE",
        (series_code,), fetch=True
    )

    if not series:
        await cb.answer("❌ Series topilmadi!", show_alert=True)
        return

    # Units ro'yxatini olish
    offset = page * BOOKS_PER_PAGE
    units = await db_exec("""
                          SELECT id, unit_number, word_count, title
                          FROM essential_books
                          WHERE series_id = %s
                            AND is_active = TRUE
                          ORDER BY unit_number
                              LIMIT %s
                          OFFSET %s
                          """, (series['id'], BOOKS_PER_PAGE, offset), fetch=True, many=True)

    # Umumiy soni
    total_count = await db_exec(
        "SELECT COUNT(*) as count FROM essential_books WHERE series_id = %s AND is_active = TRUE",
        (series['id'],), fetch=True
    )

    total = total_count.get('count', 0) if total_count else 0

    if not units and page == 0:
        await cb.answer("❌ Bu seriyada unitlar mavjud emas!", show_alert=True)
        return

    if not units and page > 0:
        await cb.answer("❌ Bu sahifada unitlar yo'q!", show_alert=True)
        return

    total_pages = ceil(total / BOOKS_PER_PAGE)
    kb = essential_units_kb(series_code, units, page, total_pages, lang)

    header_text = f"📚 {series['name']}\n📊 Jami {total} ta unit"
    if total_pages > 1:
        header_text += f"\n📄 {page + 1}/{total_pages} sahifa"

    await safe_edit_or_send(cb, header_text, kb, lang)
    await cb.answer()


@essential_router.callback_query(lambda c: c.data and c.data.startswith("essential:unit:"))
async def cb_essential_unit_practice(cb: CallbackQuery, state: FSMContext):
    """Essential unit bilan mashq boshlash - avval so'zlarni ko'rsatish."""
    unit_id = int(cb.data.split(":")[2])
    user_id = cb.from_user.id

    # Unit ma'lumotlarini olish
    unit_info = await db_exec("""
                              SELECT eb.unit_number, eb.title, eb.word_count, es.name as series_name
                              FROM essential_books eb
                                       JOIN essential_series es ON eb.series_id = es.id
                              WHERE eb.id = %s
                                AND eb.is_active = TRUE
                              """, (unit_id,), fetch=True)

    if not unit_info:
        await cb.answer("❌ Unit topilmadi!", show_alert=True)
        return

    # So'zlarni olish
    words = await get_unit_words(unit_id)

    if len(words) < 4:
        await cb.answer("❌ Bu unitda yetarli so'z yo'q (kamida 4 ta kerak)!", show_alert=True)
        return

    user_data = await get_user_data(user_id)
    lang = user_data["lang"]

    # So'zlar ro'yxatini tayyorlash
    unit_title = f"{unit_info['series_name']} - Unit {unit_info['unit_number']}"
    words_list = []
    for idx, word in enumerate(words, 1):
        words_list.append(f"{idx}. <b>{word['word_src']}</b> - {word['word_trg']}")
    
    words_text = f"📖 <b>{unit_title}</b>\n"
    words_text += f"📊 Jami: {len(words)} ta so'z\n\n"
    words_text += "\n".join(words_list)
    words_text += "\n\n💡 So'zlarni ko'rib chiqing va tayyor bo'lganingizda mashqni boshlang!"

    # So'zlarni state'ga saqlash
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
    await state.set_state(EssentialStates.ready_to_start)

    await safe_edit_or_send(cb, words_text, start_practice_kb(lang), lang)
    await cb.answer()


@essential_router.callback_query(lambda c: c.data == "essential:begin_practice")
async def cb_begin_essential_practice(cb: CallbackQuery, state: FSMContext):
    """Mashqni boshlash."""
    current_state = await state.get_state()
    if current_state != EssentialStates.ready_to_start:
        await cb.answer("❌ Xato holat!", show_alert=True)
        return

    user_data = await get_user_data(cb.from_user.id)
    lang = user_data["lang"]

    await state.set_state(EssentialStates.practicing)
    
    # Eski xabarni o'chirish
    try:
        await cb.message.delete()
    except:
        pass
    
    await send_next_essential_question(cb.message, state, lang)
    await cb.answer()


@essential_router.callback_query(lambda c: c.data and c.data.startswith("essential_ans:"))
async def cb_essential_answer(cb: CallbackQuery, state: FSMContext):
    """Essential mashq javobini tekshirish."""
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
    await send_next_essential_question(cb.message, state, user_data["lang"])


@essential_router.callback_query(lambda c: c.data == "essential:finish")
async def cb_essential_finish(cb: CallbackQuery, state: FSMContext):
    """Essential mashqni tugatish."""
    data = await state.get_data()
    total_unique = data.get("total", 0)
    total_answers = data.get("answers", 0)
    total_correct = data.get("correct", 0)
    total_wrong = data.get("wrong", 0)
    unit_title = data.get("unit_title", "Essential Unit")
    cycles = data.get("cycles", 0)

    percent = (total_correct / total_answers * 100) if total_answers else 0.0

    user_data = await get_user_data(cb.from_user.id)
    L = get_locale(user_data["lang"])

    full_text = f"📖 {unit_title}\n"
    full_text += f"{L['results_header']}\n\n"
    full_text += f"{L['results_lines'].format(unique=total_unique, answers=total_answers, correct=total_correct, wrong=total_wrong, percent=percent)}"

    # Tsikllar haqida ma'lumot
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
    
    # Eski xabarni o'chirish
    try:
        await cb.message.delete()
    except:
        pass
    
    await cb.message.answer(full_text)
    await cb.message.answer(L["cabinet"], reply_markup=cabinet_kb(user_data["lang"]))
    await cb.answer()