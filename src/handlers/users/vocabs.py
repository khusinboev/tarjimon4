""" src/handlers/users/vocabs.py

To'liq modul: lug'atlar CRUD va mashq (quiz) bo'limi.

Ushbu fayl aiogram v3 ga mos yozilgan handlerlarni o'z ichiga oladi va soddalashtirilgan DB adapter (psycopg2 orqali) ishlatadi. Agar loyihada async DB (asyncpg yoki ORM) bo'lsa, DB funksiyalarini mos ravishda almashtiring.

Qisqacha:

/mybooks — foydalanuvchi lug'atlarini ko'rsatadi

Yaratish, So'z qo'shish (bulk), Mashq (quiz) — inline callbacklar orqali


CONFIG:

DATABASE_DSN muhit o'zgaruvchisidan olinadi (postgres://...)


Eslatma: Loyihaga joylagandan so'ng main.py ga from src.handlers.users.vocabs import router as vocab_router va dispatcher.include_router(vocab_router) deb qo'shing. """

import os import json import asyncio import re from datetime import datetime from typing import List, Tuple, Optional

import psycopg2 import psycopg2.extras

from aiogram import Router from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery from aiogram.filters import Command from aiogram.fsm.context import FSMContext from aiogram.fsm.state import StatesGroup, State

Router

router = Router()

----- FSM states -----

class VocabStates(StatesGroup): waiting_book_name = State() waiting_word_list = State()

----- Simple blocking DB adapter run in thread -----

DATABASE_DSN = os.getenv('DATABASE_DSN') or os.getenv('DATABASE_URL') or 'postgres://postgres:postgres@localhost:5432/postgres'

class DB: def init(self, dsn: str): self.dsn = dsn self._conn = None

def connect_sync(self):
    if self._conn is None or self._conn.closed:
        self._conn = psycopg2.connect(self.dsn, cursor_factory=psycopg2.extras.RealDictCursor)
        self._conn.autocommit = True
    return self._conn

def fetchall_sync(self, query: str, args: tuple = ()):  # returns list[dict]
    conn = self.connect_sync()
    with conn.cursor() as cur:
        cur.execute(query, args)
        return cur.fetchall()

def fetchone_sync(self, query: str, args: tuple = ()):  # returns dict or None
    conn = self.connect_sync()
    with conn.cursor() as cur:
        cur.execute(query, args)
        return cur.fetchone()

def execute_sync(self, query: str, args: tuple = ()):  # returns lastrowid if using RETURNING
    conn = self.connect_sync()
    with conn.cursor() as cur:
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

----- Helpers: parsing user text into pairs -----

SEP_PATTERN = re.compile(r"\s*[-—:|]\s*")

def parse_pairs_from_text(text: str) -> List[Tuple[str, str]]: """Parses text like: book-kitob, pen-qalam\napple - olma returns list of (left, right) """ pairs: List[Tuple[str, str]] = [] if not text: return pairs

# Split lines and commas
tokens = []
for line in re.split(r"[\n,]+", text):
    tok = line.strip()
    if tok:
        tokens.append(tok)

for tok in tokens:
    # try to split by separators
    parts = SEP_PATTERN.split(tok, maxsplit=1)
    if len(parts) >= 2:
        left = parts[0].strip()
        right = parts[1].strip()
        if left and right:
            pairs.append((left, right))
    else:
        # If only single token and contains space, try splitting by space
        if ' ' in tok:
            a, b = tok.split(None, 1)
            pairs.append((a.strip(), b.strip()))
        # otherwise ignore single words (could be handled differently)
return pairs

----- DB high-level helpers (async wrappers calling blocking adapters) -----

async def create_book(user_id: int, name: str, src_lang: Optional[str] = None, trg_lang: Optional[str] = None) -> int: query = """ INSERT INTO vocab_books (user_id, name, src_lang, trg_lang, created_at, updated_at) VALUES (%s, %s, %s, %s, now(), now()) ON CONFLICT (user_id, name) DO NOTHING RETURNING id; """ res = await db.execute(query, (user_id, name, src_lang, trg_lang)) if res and isinstance(res, dict) and 'id' in res: return res['id'] # If conflict happened and no row returned, fetch id q2 = "SELECT id FROM vocab_books WHERE user_id = %s AND name = %s" row = await db.fetchone(q2, (user_id, name)) return row['id'] if row else 0

async def list_books(user_id: int) -> List[dict]: q = "SELECT id, name, description, src_lang, trg_lang, created_at FROM vocab_books WHERE user_id = %s ORDER BY created_at DESC" return await db.fetchall(q, (user_id,))

async def add_entries_bulk(book_id: int, pairs: List[Tuple[str, str]], src_lang: Optional[str] = None, trg_lang: Optional[str] = None) -> int: if not pairs: return 0 args = [] for left, right in pairs: args.append((book_id, left, right, src_lang, trg_lang, 0, True)) q = """ INSERT INTO vocab_entries (book_id, word_src, word_trg, src_lang, trg_lang, position, is_active, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s, %s, now(), now()) ON CONFLICT DO NOTHING """ await db.executemany(q, args) return len(args)

async def get_random_entry(book_id: int) -> Optional[dict]: q = "SELECT id, word_src, word_trg FROM vocab_entries WHERE book_id = %s AND is_active = true ORDER BY random() LIMIT 1" return await db.fetchone(q, (book_id,))

async def get_distractors(book_id: int, exclude_id: int, n: int = 3) -> List[str]: q = "SELECT word_trg FROM vocab_entries WHERE book_id = %s AND id != %s ORDER BY random() LIMIT %s" rows = await db.fetchall(q, (book_id, exclude_id, n)) res = [r['word_trg'] for r in rows] if rows else []

# If not enough distractors, try same user's other books
if len(res) < n:
    q2 = "SELECT e.word_trg FROM vocab_entries e JOIN vocab_books b ON e.book_id = b.id WHERE b.user_id = (SELECT user_id FROM vocab_books WHERE id = %s) AND e.book_id != %s ORDER BY random() LIMIT %s"
    rows2 = await db.fetchall(q2, (book_id, book_id, n - len(res)))
    res.extend([r['word_trg'] for r in rows2])

# Still not enough -> global pool
if len(res) < n:
    q3 = "SELECT word_trg FROM vocab_entries WHERE id != %s ORDER BY random() LIMIT %s"
    rows3 = await db.fetchall(q3, (exclude_id, n - len(res)))
    res.extend([r['word_trg'] for r in rows3])

return res[:n]

async def start_session(user_id: int, book_id: int) -> int: q = "INSERT INTO practice_sessions (user_id, book_id, started_at, total_questions, correct_count, wrong_count, meta) VALUES (%s, %s, now(), 0, 0, 0, '{}'::jsonb) RETURNING id" row = await db.fetchone(q, (user_id, book_id)) return row['id'] if row else 0

async def record_question(session_id: int, entry_id: Optional[int], presented_text: str, correct_translation: str, choices: List[str], chosen_option: Optional[str], is_correct: Optional[bool]): q = """ INSERT INTO practice_questions (session_id, entry_id, presented_text, correct_translation, choices, chosen_option, is_correct, asked_at, answered_at) VALUES (%s, %s, %s, %s, %s, %s, %s, now(), %s) """ await db.execute(q, (session_id, entry_id, presented_text, correct_translation, json.dumps(choices, ensure_ascii=False), chosen_option, is_correct, (datetime.now() if chosen_option is not None else None)))

# update session counters
if chosen_option is not None:
    if is_correct:
        q2 = "UPDATE practice_sessions SET total_questions = total_questions + 1, correct_count = correct_count + 1 WHERE id = %s"
    else:
        q2 = "UPDATE practice_sessions SET total_questions = total_questions + 1, wrong_count = wrong_count + 1 WHERE id = %s"
    await db.execute(q2, (session_id,))

async def finish_session(session_id: int): q = "UPDATE practice_sessions SET finished_at = now() WHERE id = %s" await db.execute(q, (session_id,))

async def get_session(session_id: int) -> Optional[dict]: q = "SELECT * FROM practice_sessions WHERE id = %s" return await db.fetchone(q, (session_id,))

----- UI helpers -----

def make_books_keyboard(books: List[dict]) -> InlineKeyboardMarkup: kb = InlineKeyboardMarkup(row_width=1) kb.add(InlineKeyboardButton(text='➕ Yangi lug`at yaratish', callback_data='vb:create')) for b in books: kb.add(InlineKeyboardButton(text=f"📚 {b['name']}", callback_data=f"vb:b:{b['id']}:menu")) return kb

def make_book_menu(book_id: int) -> InlineKeyboardMarkup: kb = InlineKeyboardMarkup(row_width=2) kb.add( InlineKeyboardButton(text='▶ Mashq', callback_data=f'vb:b:{book_id}:practice'), InlineKeyboardButton(text='➕ Soz qoshish', callback_data=f'vb:b:{book_id}:add'), ) kb.add(InlineKeyboardButton(text='🔙 Orqaga', callback_data='vb:back')) return kb

async def send_question_for_session(chat_id: int, session_id: int, book_id: int, bot): # get correct entry entry = await get_random_entry(book_id) if not entry: await bot.send_message(chat_id, "Bu lug'atda hali so'z yo'q. Avval so'z qo'shing.") return

# randomly decide direction: src->trg yoki trg->src
direction = 'src2trg' if bool(os.urandom(1)[0] % 2) else 'trg2src'
if direction == 'src2trg':
    presented = entry['word_src']
    correct = entry['word_trg']
    distractors = await get_distractors(book_id, entry['id'], n=3)
    choices = [correct] + distractors
else:
    presented = entry['word_trg']
    correct = entry['word_src']
    # distractors should be src variants from other entries
    q = "SELECT word_src FROM vocab_entries WHERE book_id = %s AND id != %s ORDER BY random() LIMIT 3"
    rows = await db.fetchall(q, (book_id, entry['id'], 3))
    distractors = [r['word_src'] for r in rows] if rows else []
    # fallback to trg pool
    if len(distractors) < 3:
        rows2 = await db.fetchall("SELECT word_src FROM vocab_entries WHERE id != %s ORDER BY random() LIMIT %s", (entry['id'], 3 - len(distractors)))
        distractors.extend([r['word_src'] for r in rows2])
    choices = [correct] + distractors

# shuffle choices
import random
random.shuffle(choices)

# send message with inline keyboard (4 choices + finish)
kb = InlineKeyboardMarkup(row_width=2)
for idx, ch in enumerate(choices):
    cb = f"vb:ans:{session_id}:{entry['id']}:{idx}"
    kb.add(InlineKeyboardButton(text=ch, callback_data=cb))
kb.add(InlineKeyboardButton(text='🏁 Tugatish', callback_data=f'vb:finish:{session_id}'))

await bot.send_message(chat_id, f"Savol: {presented}", reply_markup=kb)

# store current question in session meta (optional)
q_upd = "UPDATE practice_sessions SET meta = jsonb_set(coalesce(meta, '{}'::jsonb), '{current_question}', to_jsonb(%s::text), true) WHERE id = %s"
await db.execute(q_upd, (json.dumps({'entry_id': entry['id'], 'presented': presented, 'choices': choices, 'direction': direction}, ensure_ascii=False), session_id))

----- Handlers -----

@router.message(Command('mybooks')) async def cmd_mybooks(message: Message): user_id = message.from_user.id books = await list_books(user_id) kb = make_books_keyboard(books) await message.answer('Sizning lug'atlar:', reply_markup=kb)

@router.callback_query(lambda c: c.data == 'vb:create') async def cb_create_book(query: CallbackQuery, state: FSMContext): await query.message.answer('Yangi lug`at nomini kiriting:') await state.set_state(VocabStates.waiting_book_name) await query.answer()

@router.message(VocabStates.waiting_book_name) async def process_book_name(message: Message, state: FSMContext): user_id = message.from_user.id name = message.text.strip() if not name: await message.reply('Nom bosh bolishi mumkin emas, qayta kiriting:') return book_id = await create_book(user_id, name) await message.answer(f"Lug`at yaratildi: {name} (id={book_id})") await state.clear()

@router.callback_query(lambda c: c.data and c.data.startswith('vb:b:')) async def cb_book_menu(query: CallbackQuery): # format vb:b:{book_id}:menu data = query.data.split(':') # expected ['vb','b','{id}','menu' or 'add' or 'practice'] if len(data) < 4: await query.answer() return book_id = int(data[2]) action = data[3] if action == 'menu': kb = make_book_menu(book_id) await query.message.answer('Lug'at menyusi:', reply_markup=kb) await query.answer() return if action == 'add': # ask for words await query.message.answer('Sozlarni quyidagi shaklda yuboring (har bir juftlik yangi qatorda yoki vergul bilan):\nbook-kitob, pen-qalam, ...') # store book_id in state await VocabStates.waiting_word_list.set() await query.answer() # save book_id in FSM data # There is no FSMContext in callback handler signature by default, so skip—user will reply and we need to know book; store mapping in a temp way: include book_id in message? Simpler: instruct user to send: #book:{id}\nbook-kitobbut to keep UX simple, we'll use per-user temporary file mapping in DB: create a practice_sessions trick not ideal. # Instead, send special hidden message with book id and ask user to start the add flow with/addwords {book_id}. Simpler implementation below. await query.message.answer(f'Agar davom ettirmoqchi bolsangiz, quyidagicha yuboring: /addwords {book_id}') return if action == 'practice': # start practice user_id = query.from_user.id session_id = await start_session(user_id, book_id) # send first question await send_question_for_session(query.message.chat.id, session_id, book_id, query.bot) await query.answer() return

@router.message(Command('addwords')) async def cmd_addwords(message: Message): # syntax: /addwords <book_id> parts = message.text.strip().split() if len(parts) < 2: await message.reply('Iltimos: /addwords <book_id> formatida yuboring.') return try: book_id = int(parts[1]) except ValueError: await message.reply('Notogri book_id') return # check ownership row = await db.fetchone('SELECT id FROM vocab_books WHERE id = %s AND user_id = %s', (book_id, message.from_user.id)) if not row: await message.reply('Bunday lug'at topilmadi yoki sizga tegishli emas.') return # set FSM to waiting_word_list and store book_id in state await message.answer('Sozlarni yuboring (har bir juftlik yangi qatorda yoki vergul bilan):\nbook-kitob, pen-qalam, ...`') await VocabStates.waiting_word_list.set() # store book_id in FSMContext state = FSMContext(storage=None)  # placeholder — aiogram requires context; we'll instead store mapping in-memory # Simpler: use global in-memory dict mapping user_id -> pending_book_id PENDING_BOOK_ADDITION[message.from_user.id] = book_id

In-memory temporal mapping for addwords flow (simple approach)

PENDING_BOOK_ADDITION = {}

@router.message(VocabStates.waiting_word_list) async def process_word_list(message: Message, state: FSMContext): user_id = message.from_user.id book_id = PENDING_BOOK_ADDITION.get(user_id) if not book_id: await message.reply('Qaysi lugatga qoshayotganingiz nomalum. /addwords <book_id> orqali boshlang.') await state.clear() return text = message.text pairs = parse_pairs_from_text(text) if not pairs: await message.reply('Hech qanday togri juftlik topilmadi. Format: word1-word2') return n = await add_entries_bulk(book_id, pairs) await message.answer(f'{n} ta juftlik lugatga qo`shildi.') # cleanup PENDING_BOOK_ADDITION.pop(user_id, None) await state.clear()

@router.callback_query(lambda c: c.data and c.data.startswith('vb:ans:')) async def cb_answer(query: CallbackQuery): # format vb:ans:{session_id}:{entry_id}:{choice_idx} parts = query.data.split(':') if len(parts) != 5: await query.answer() return _, _, session_id_s, entry_id_s, choice_idx_s = parts session_id = int(session_id_s) entry_id = int(entry_id_s) choice_idx = int(choice_idx_s)

# fetch session meta to get choices
sess = await get_session(session_id)
if not sess:
    await query.answer('Sessiya topilmadi')
    return
# get current question info from meta
meta = sess.get('meta') or {}
try:
    current = json.loads(meta.get('current_question')) if isinstance(meta.get('current_question'), str) else meta.get('current_question')
except Exception:
    current = meta.get('current_question')

if not current:
    await query.answer('Savol ma`lumotlari topilmadi, davom etilmaydi.')
    return

choices = current.get('choices')
direction = current.get('direction')
presented = current.get('presented')
correct_text = None
if direction == 'src2trg':
    # correct is word_trg
    # we need to fetch entry to be safe
    row = await db.fetchone('SELECT word_trg, word_src FROM vocab_entries WHERE id = %s', (entry_id,))
    if not row:
        await query.answer('Savol entry topilmadi')
        return
    correct_text = row['word_trg']
else:
    row = await db.fetchone('SELECT word_trg, word_src FROM vocab_entries WHERE id = %s', (entry_id,))
    if not row:
        await query.answer('Savol entry topilmadi')
        return
    correct_text = row['word_src']

try:
    chosen_text = choices[choice_idx]
except Exception:
    await query.answer('Noto`g`ri javob tanlandi')
    return

is_correct = (chosen_text == correct_text)
# record question
await record_question(session_id, entry_id, presented, correct_text, choices, chosen_text, is_correct)

# feedback
if is_correct:
    await query.answer('✅ To`g`ri')
else:
    await query.answer(f'❌ Noto`g`ri. To`g`ri javob: {correct_text}')

# send next question
# get book id from session
s = await get_session(session_id)
book_id = s.get('book_id')
await send_question_for_session(query.message.chat.id, session_id, book_id, query.bot)

@router.callback_query(lambda c: c.data and c.data.startswith('vb:finish:')) async def cb_finish(query: CallbackQuery): # vb:finish:{session_id} parts = query.data.split(':') session_id = int(parts[2]) if len(parts) > 2 else None if not session_id: await query.answer() return await finish_session(session_id) s = await get_session(session_id) if not s: await query.answer('Sessiya topilmadi') return correct = s.get('correct_count', 0) wrong = s.get('wrong_count', 0) total = s.get('total_questions', 0) pct = int((correct / total) * 100) if total else 0 await query.message.answer(f"Sessiya tugadi. Natija: {correct}/{total} ({pct}%) — To'g'ri: {correct}, Noto'g'ri: {wrong}") await query.answer()

Export router for main.py

all = ['router']

