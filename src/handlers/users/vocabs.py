"""
src/handlers/users/vocabs_fixed.py

Tahrirlangan va tozalangan versiya — ilgari yuborilgan kodni chuqur tahlil qilib,
aniq xatolar va noaniqliklar tuzatildi.

Qisqacha o'zgartirishlar:
- FSMContext to'g'ri ishlatildi (state paramlarini handlerlarda qabul qilinadi)
- Global PENDING_BOOK_ADDITION olib tashlandi; o'rniga FSMContext storage ishlatiladi
- DB adapter toza, async wrapperlar bilan ishlaydi
- practice_sessions.meta ga current_question JSONB sifatida to'g'ri yozish va o'qish
- JSONB maydonlarga SQL da %s::jsonb cast qo'yildi, choices JSON sifatida yoziladi
- Xatoliklarni tekshiruvchi istisno va fallbacklar qo'shildi

Integratsiya:
- main.py ga: `from src.handlers.users.vocabs_fixed import router as vocab_router` va `dp.include_router(vocab_router)` qo'shing
- `psycopg2-binary` ni o'rnating va DATABASE_DSN muhit o'zgaruvchisini to'g'ri sozlang
"""

import os
import json
import asyncio
import re
import random
from datetime import datetime
from typing import List, Tuple, Optional

import psycopg2
import psycopg2.extras

from aiogram import Router
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

router = Router()

# FSM states
class VocabStates(StatesGroup):
    waiting_book_name = State()
    waiting_word_list = State()

# Config
DATABASE_DSN = os.getenv('DATABASE_DSN') or os.getenv('DATABASE_URL') or 'postgres://postgres:postgres@localhost:5432/postgres'

# Simple blocking DB adapter with async wrappers
class DB:
    def __init__(self, dsn: str):
        self.dsn = dsn
        self._conn = None

    def connect_sync(self):
        if self._conn is None or getattr(self._conn, 'closed', False):
            # create normal connection; we'll use RealDictCursor when fetching
            self._conn = psycopg2.connect(self.dsn)
            self._conn.autocommit = True
        return self._conn

    def fetchall_sync(self, query: str, args: tuple = ()):  # returns list[dict]
        conn = self.connect_sync()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, args)
            return cur.fetchall()

    def fetchone_sync(self, query: str, args: tuple = ()):  # returns dict or None
        conn = self.connect_sync()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, args)
            return cur.fetchone()

    def execute_sync(self, query: str, args: tuple = ()):  # for INSERT ... RETURNING etc
        conn = self.connect_sync()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, args)
            try:
                return cur.fetchone()
            except Exception:
                return None

    def executemany_sync(self, query: str, seq_of_args: list):
        conn = self.connect_sync()
        with conn.cursor() as cur:
            cur.executemany(query, seq_of_args)

    # Async wrappers
    async def fetchall(self, query: str, args: tuple = ()):  # pragma: no cover
        return await asyncio.to_thread(self.fetchall_sync, query, args)

    async def fetchone(self, query: str, args: tuple = ()):  # pragma: no cover
        return await asyncio.to_thread(self.fetchone_sync, query, args)

    async def execute(self, query: str, args: tuple = ()):  # pragma: no cover
        return await asyncio.to_thread(self.execute_sync, query, args)

    async def executemany(self, query: str, seq_of_args: list):  # pragma: no cover
        return await asyncio.to_thread(self.executemany_sync, query, seq_of_args)


db = DB(DATABASE_DSN)

# Parsing
SEP_PATTERN = re.compile(r"\s*[-—:|]\s*")

def parse_pairs_from_text(text: str) -> List[Tuple[str, str]]:
    pairs: List[Tuple[str, str]] = []
    if not text:
        return pairs
    tokens = []
    for line in re.split(r"[\n,]+", text):
        tok = line.strip()
        if tok:
            tokens.append(tok)
    for tok in tokens:
        parts = SEP_PATTERN.split(tok, maxsplit=1)
        if len(parts) >= 2:
            left = parts[0].strip()
            right = parts[1].strip()
            if left and right:
                pairs.append((left, right))
        else:
            if ' ' in tok:
                a, b = tok.split(None, 1)
                pairs.append((a.strip(), b.strip()))
    return pairs

# DB helpers
async def create_book(user_id: int, name: str, src_lang: Optional[str] = None, trg_lang: Optional[str] = None) -> int:
    q = """
    INSERT INTO vocab_books (user_id, name, src_lang, trg_lang, created_at, updated_at)
      VALUES (%s, %s, %s, %s, now(), now())
    ON CONFLICT (user_id, name) DO NOTHING
    RETURNING id;
    """
    row = await db.execute(q, (user_id, name, src_lang, trg_lang))
    if row and isinstance(row, dict) and 'id' in row:
        return row['id']
    r = await db.fetchone('SELECT id FROM vocab_books WHERE user_id = %s AND name = %s', (user_id, name))
    return r['id'] if r else 0

async def list_books(user_id: int) -> List[dict]:
    return await db.fetchall('SELECT id, name, description, src_lang, trg_lang, created_at FROM vocab_books WHERE user_id = %s ORDER BY created_at DESC', (user_id,))

async def add_entries_bulk(book_id: int, pairs: List[Tuple[str, str]], src_lang: Optional[str] = None, trg_lang: Optional[str] = None) -> int:
    if not pairs:
        return 0
    args = []
    for left, right in pairs:
        args.append((book_id, left, right, src_lang, trg_lang, 0, True))
    q = """
    INSERT INTO vocab_entries (book_id, word_src, word_trg, src_lang, trg_lang, position, is_active, created_at, updated_at)
    VALUES (%s, %s, %s, %s, %s, %s, %s, now(), now()) ON CONFLICT DO NOTHING
    """
    await db.executemany(q, args)
    return len(args)

async def get_random_entry(book_id: int) -> Optional[dict]:
    return await db.fetchone('SELECT id, word_src, word_trg FROM vocab_entries WHERE book_id = %s AND is_active = true ORDER BY random() LIMIT 1', (book_id,))

async def get_distractors(book_id: int, exclude_id: int, n: int = 3, direction: str = 'trg') -> List[str]:
    col = 'word_trg' if direction == 'trg' else 'word_src'
    q = f"SELECT {col} as val FROM vocab_entries WHERE book_id = %s AND id != %s ORDER BY random() LIMIT %s"
    rows = await db.fetchall(q, (book_id, exclude_id, n))
    res = [r['val'] for r in rows] if rows else []
    if len(res) < n:
        q2 = f"SELECT e.{col} as val FROM vocab_entries e JOIN vocab_books b ON e.book_id = b.id WHERE b.user_id = (SELECT user_id FROM vocab_books WHERE id = %s) AND e.book_id != %s ORDER BY random() LIMIT %s"
        rows2 = await db.fetchall(q2, (book_id, book_id, n - len(res)))
        res.extend([r['val'] for r in rows2])
    if len(res) < n:
        q3 = f"SELECT {col} as val FROM vocab_entries WHERE id != %s ORDER BY random() LIMIT %s"
        rows3 = await db.fetchall(q3, (exclude_id, n - len(res)))
        res.extend([r['val'] for r in rows3])
    return res[:n]

async def start_session(user_id: int, book_id: int) -> int:
    row = await db.fetchone("INSERT INTO practice_sessions (user_id, book_id, started_at, total_questions, correct_count, wrong_count, meta) VALUES (%s, %s, now(), 0, 0, 0, '{}'::jsonb) RETURNING id", (user_id, book_id))
    return row['id'] if row else 0

async def record_question(session_id: int, entry_id: Optional[int], presented_text: str, correct_translation: str, choices: List[str], chosen_option: Optional[str], is_correct: Optional[bool]):
    choices_json = json.dumps(choices, ensure_ascii=False)
    q = """
    INSERT INTO practice_questions (session_id, entry_id, presented_text, correct_translation, choices, chosen_option, is_correct, asked_at, answered_at)
    VALUES (%s, %s, %s, %s, %s::jsonb, %s, %s, now(), %s)
    """
    await db.execute(q, (session_id, entry_id, presented_text, correct_translation, choices_json, chosen_option, is_correct, (datetime.now() if chosen_option is not None else None)))
    if chosen_option is not None:
        if is_correct:
            q2 = "UPDATE practice_sessions SET total_questions = total_questions + 1, correct_count = correct_count + 1 WHERE id = %s"
        else:
            q2 = "UPDATE practice_sessions SET total_questions = total_questions + 1, wrong_count = wrong_count + 1 WHERE id = %s"
        await db.execute(q2, (session_id,))

async def finish_session(session_id: int):
    await db.execute('UPDATE practice_sessions SET finished_at = now() WHERE id = %s', (session_id,))

async def get_session(session_id: int) -> Optional[dict]:
    return await db.fetchone('SELECT * FROM practice_sessions WHERE id = %s', (session_id,))

# UI helpers

def make_books_keyboard(books: List[dict]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton(text='➕ Yangi lug`at yaratish', callback_data='vb:create'))
    for b in books:
        kb.add(InlineKeyboardButton(text=f"📚 {b['name']}", callback_data=f"vb:b:{b['id']}:menu"))
    return kb


def make_book_menu(book_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton(text='▶ Mashq', callback_data=f'vb:b:{book_id}:practice'),
        InlineKeyboardButton(text='➕ So`z qo`shish', callback_data=f'vb:b:{book_id}:add'),
    )
    kb.add(InlineKeyboardButton(text='🔙 Orqaga', callback_data='vb:back'))
    return kb

async def send_question_for_session(chat_id: int, session_id: int, book_id: int, bot):
    entry = await get_random_entry(book_id)
    if not entry:
        await bot.send_message(chat_id, "Bu lug'atda hali so'z yo'q. Avval so'z qo'shing.")
        return
    direction = 'src2trg' if random.choice([True, False]) else 'trg2src'
    if direction == 'src2trg':
        presented = entry['word_src']
        correct = entry['word_trg']
        distractors = await get_distractors(book_id, entry['id'], n=3, direction='trg')
        choices = [correct] + distractors
    else:
        presented = entry['word_trg']
        correct = entry['word_src']
        distractors = await get_distractors(book_id, entry['id'], n=3, direction='src')
        choices = [correct] + distractors
    random.shuffle(choices)
    kb = InlineKeyboardMarkup(row_width=2)
    for idx, ch in enumerate(choices):
        cb = f"vb:ans:{session_id}:{entry['id']}:{idx}"
        kb.add(InlineKeyboardButton(text=ch, callback_data=cb))
    kb.add(InlineKeyboardButton(text='🏁 Tugatish', callback_data=f'vb:finish:{session_id}'))
    await bot.send_message(chat_id, f"Savol: {presented}", reply_markup=kb)
    current = {
        'entry_id': entry['id'],
        'presented': presented,
        'choices': choices,
        'direction': direction,
    }
    await db.execute("UPDATE practice_sessions SET meta = jsonb_set(coalesce(meta, '{}'::jsonb), '{current_question}', %s::jsonb, true) WHERE id = %s", (json.dumps(current, ensure_ascii=False), session_id))

# Handlers
@router.message(Command('mybooks'))
async def cmd_mybooks(message: Message):
    user_id = message.from_user.id
    books = await list_books(user_id)
    kb = make_books_keyboard(books)
    await message.answer("Sizning lug'atlar:", reply_markup=kb)

@router.callback_query(lambda c: c.data == 'vb:create')
async def cb_create_book(query: CallbackQuery, state: FSMContext):
    await query.message.answer("Yangi lug`at nomini kiriting:")
    await state.set_state(VocabStates.waiting_book_name)
    await query.answer()

@router.message(VocabStates.waiting_book_name)
async def process_book_name(message: Message, state: FSMContext):
    user_id = message.from_user.id
    name = message.text.strip()
    if not name:
        await message.reply("Nom bo`sh bo`lishi mumkin emas, qayta kiriting:")
        return
    book_id = await create_book(user_id, name)
    await message.answer(f"Lug`at yaratildi: {name} (id={book_id})")
    await state.clear()

@router.callback_query(lambda c: c.data and c.data.startswith('vb:b:'))
async def cb_book_menu(query: CallbackQuery, state: FSMContext):
    data = query.data.split(':')
    if len(data) < 4:
        await query.answer()
        return
    book_id = int(data[2])
    action = data[3]
    if action == 'menu':
        kb = make_book_menu(book_id)
        await query.message.answer("Lug' at menyusi:", reply_markup=kb)
        await query.answer()
        return
    if action == 'add':
        await state.update_data(book_id=book_id)
        await state.set_state(VocabStates.waiting_word_list)
        await query.message.answer("So`zlarni quyidagi shaklda yuboring (har bir juftlik yangi qatorda yoki vergul bilan):\n`book-kitob, pen-qalam, ...`")
        await query.answer()
        return
    if action == 'practice':
        user_id = query.from_user.id
        session_id = await start_session(user_id, book_id)
        await send_question_for_session(query.message.chat.id, session_id, book_id, query.bot)
        await query.answer()
        return

@router.message(Command('addwords'))
async def cmd_addwords(message: Message, state: FSMContext):
    parts = message.text.strip().split()
    if len(parts) < 2:
        await message.reply('Iltimos: /addwords <book_id> formatida yuboring.')
        return
    try:
        book_id = int(parts[1])
    except ValueError:
        await message.reply("Noto`g`ri book_id")
        return
    row = await db.fetchone('SELECT id FROM vocab_books WHERE id = %s AND user_id = %s', (book_id, message.from_user.id))
    if not row:
        await message.reply("Bunday lug' at topilmadi yoki sizga tegishli emas.")
        return
    await state.update_data(book_id=book_id)
    await state.set_state(VocabStates.waiting_word_list)
    await message.answer("So`zlarni yuboring (har bir juftlik yangi qatorda yoki vergul bilan):\n`book-kitob, pen-qalam, ...`")

@router.message(VocabStates.waiting_word_list)
async def process_word_list(message: Message, state: FSMContext):
    data = await state.get_data()
    book_id = data.get('book_id')
    if not book_id:
        await message.reply("Qaysi lug`atga qo`shayotganingiz noma`lum. /addwords <book_id> orqali boshlang yoki lug'at menyusidan Add tanlang.")
        await state.clear()
        return
    text = message.text
    pairs = parse_pairs_from_text(text)
    if not pairs:
        await message.reply("Hech qanday to`g`ri juftlik topilmadi. Format: `word1-word2`")
        return
    n = await add_entries_bulk(book_id, pairs)
    await message.answer(f"{n} ta juftlik lug`atga qo`shildi.")
    await state.clear()

@router.callback_query(lambda c: c.data and c.data.startswith('vb:ans:'))
async def cb_answer(query: CallbackQuery):
    parts = query.data.split(':')
    if len(parts) != 5:
        await query.answer()
        return
    _, _, session_id_s, entry_id_s, choice_idx_s = parts
    try:
        session_id = int(session_id_s)
        entry_id = int(entry_id_s)
        choice_idx = int(choice_idx_s)
    except ValueError:
        await query.answer()
        return
    sess = await get_session(session_id)
    if not sess:
        await query.answer('Sessiya topilmadi')
        return
    meta = sess.get('meta') or {}
    current = meta.get('current_question') if isinstance(meta, dict) else None
    if not current:
        await query.answer("Savol ma'lumotlari topilmadi, davom etilmaydi.")
        return
    choices = current.get('choices')
    direction = current.get('direction')
    presented = current.get('presented')
    row = await db.fetchone('SELECT word_trg, word_src FROM vocab_entries WHERE id = %s', (entry_id,))
    if not row:
        await query.answer('Savol entry topilmadi')
        return
    correct_text = row['word_trg'] if direction == 'src2trg' else row['word_src']
    try:
        chosen_text = choices[choice_idx]
    except Exception:
        await query.answer('Noto`g`ri javob tanlandi')
        return
    is_correct = (chosen_text == correct_text)
    await record_question(session_id, entry_id, presented, correct_text, choices, chosen_text, is_correct)
    if is_correct:
        await query.answer('✅ To`g`ri')
    else:
        await query.answer(f"❌ Noto`g`ri. To`g`ri javob: {correct_text}")
    s = await get_session(session_id)
    book_id = s.get('book_id') if s else None
    if book_id:
        await send_question_for_session(query.message.chat.id, session_id, book_id, query.bot)
    else:
        await query.message.answer('Sessiya davom ettirilmaydi (book topilmadi).')

@router.callback_query(lambda c: c.data and c.data.startswith('vb:finish:'))
async def cb_finish(query: CallbackQuery):
    parts = query.data.split(':')
    if len(parts) < 3:
        await query.answer()
        return
    try:
        session_id = int(parts[2])
    except ValueError:
        await query.answer()
        return
    await finish_session(session_id)
    s = await get_session(session_id)
    if not s:
        await query.answer('Sessiya topilmadi')
        return
    correct = s.get('correct_count', 0)
    wrong = s.get('wrong_count', 0)
    total = s.get('total_questions', 0)
    pct = int((correct / total) * 100) if total else 0
    await query.message.answer(f"Sessiya tugadi. Natija: {correct}/{total} ({pct}%) — To'g'ri: {correct}, Noto'g'ri: {wrong}")
    await query.answer()

__all__ = ['router']
