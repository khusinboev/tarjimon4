# # src/handlers/users/vocabs.py
import os
import json
import asyncio
import random
from datetime import datetime
from typing import List, Optional, Dict, Any

from contextlib import closing
from aiogram import Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

# 🔹 config.py dan tortamiz
from config import sql, db  

router = Router()

# ---- Async wrapper for blocking psycopg2 calls ----
async def db_exec(query: str, params: tuple = None, fetch: bool = False, many: bool = False) -> Optional[Any]:
    """
    sql va db (config.py) orqali so‘rov bajaradi
    """
    def run():
        cur = db.cursor()
        cur.execute(query, params or ())
        if fetch:
            if many:
                rows = cur.fetchall()
                # agar RealDictCursor ishlatilmagan bo‘lsa -> dict qilib qaytaramiz
                cols = [desc[0] for desc in cur.description]
                return [dict(zip(cols, row)) for row in rows]
            else:
                row = cur.fetchone()
                if not row:
                    return None
                cols = [desc[0] for desc in cur.description]
                return dict(zip(cols, row))
        return None
    return await asyncio.to_thread(run)

# ---- FSM states ----
class VocabStates(StatesGroup):
    waiting_book_name = State()
    waiting_word_list = State()
    practicing = State()

# ---- Helper: parse user-provided lines "word-translation" ----
def parse_pairs_from_text(text: str) -> List[tuple]:
    pairs: List[tuple] = []
    if not text:
        return pairs
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        for sep in ("-", ":", "|"):
            if sep in line:
                left, right = [p.strip() for p in line.split(sep, 1)]
                if left and right:
                    pairs.append((left, right))
                break
        else:
            if " " in line:
                a, b = line.split(None, 1)
                pairs.append((a.strip(), b.strip()))
    return pairs

# ---- DB helpers for domain logic ----
async def create_book(user_id: int, name: str) -> int:
    q = """
    INSERT INTO vocab_books (user_id, name, created_at, updated_at)
    VALUES (%s, %s, now(), now())
    ON CONFLICT (user_id, name) DO NOTHING
    RETURNING id
    """
    row = await db_exec(q, (user_id, name), fetch=True)
    if row and "id" in row:
        return row["id"]
    row2 = await db_exec("SELECT id FROM vocab_books WHERE user_id=%s AND name=%s", (user_id, name), fetch=True)
    return row2["id"] if row2 else 0

async def list_books(user_id: int) -> List[Dict[str, Any]]:
    rows = await db_exec("SELECT id, name FROM vocab_books WHERE user_id=%s ORDER BY created_at DESC", (user_id,), fetch=True, many=True)
    return rows or []

async def add_entries_bulk(book_id: int, pairs: List[tuple]) -> int:
    if not pairs:
        return 0
    args = [(book_id, left, right) for left, right in pairs]

    def run_many():
        cur = db.cursor()
        cur.executemany(
            "INSERT INTO vocab_entries (book_id, word_src, word_trg, created_at, updated_at) "
            "VALUES (%s, %s, %s, now(), now()) ON CONFLICT DO NOTHING",
            args
        )
        db.commit()
    await asyncio.to_thread(run_many)
    return len(args)

async def start_session(user_id: int, book_id: int) -> int:
    row = await db_exec(
        "INSERT INTO practice_sessions (user_id, book_id, started_at, meta) VALUES (%s, %s, now(), '{}'::jsonb) RETURNING id",
        (user_id, book_id),
        fetch=True
    )
    return row["id"] if row else 0

async def record_question(session_id: int, entry_id: int, presented: str, correct: str, choices: List[str], chosen: Optional[str], is_correct: Optional[bool]):
    choices_json = json.dumps(choices, ensure_ascii=False)
    await db_exec(
        "INSERT INTO practice_questions (session_id, entry_id, presented_text, correct_translation, choices, chosen_option, is_correct, asked_at, answered_at) "
        "VALUES (%s,%s,%s,%s,%s::jsonb,%s,%s,now(),%s)",
        (session_id, entry_id, presented, correct, choices_json, chosen, is_correct, (datetime.now() if chosen is not None else None))
    )
    if chosen is not None:
        if is_correct:
            await db_exec("UPDATE practice_sessions SET total_questions = total_questions + 1, correct_count = correct_count + 1 WHERE id = %s", (session_id,))
        else:
            await db_exec("UPDATE practice_sessions SET total_questions = total_questions + 1, wrong_count = wrong_count + 1 WHERE id = %s", (session_id,))

async def finish_session(session_id: int):
    await db_exec("UPDATE practice_sessions SET finished_at = now() WHERE id = %s", (session_id,))

async def get_session(session_id: int) -> Optional[Dict[str, Any]]:
    return await db_exec("SELECT * FROM practice_sessions WHERE id = %s", (session_id,), fetch=True)

# ---- UI helpers va Handlers (o‘zgarmagan) ----
# ... qolgan kodingiz xuddi o‘sha holda ishlaydi ...

# ---- UI helpers ----
def make_books_kb(rows: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    # one button per row
    buttons = []
    for r in rows:
        buttons.append([InlineKeyboardButton(text=r["name"], callback_data=f"book:{r['id']}")])
    # add create new
    buttons.insert(0, [InlineKeyboardButton(text="➕ Yangi lug'at yaratish", callback_data="create_book")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def make_book_menu_kb(book_id: int) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="▶ Mashq", callback_data=f"practice:{book_id}")],
        [InlineKeyboardButton(text="➕ So'z qo'shish", callback_data=f"add:{book_id}")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ---- Handlers ----
@router.message(Command("mybooks"))
async def cmd_mybooks(msg: Message):
    rows = await list_books(msg.from_user.id)
    if not rows:
        await msg.answer("Sizda hali lug'at yo'q. /newbook bilan yarating.")
        return
    kb = make_books_kb(rows)
    await msg.answer("Sizning lug'atlaringiz:", reply_markup=kb)

@router.message(Command("newbook"))
async def cmd_newbook(msg: Message):
    parts = msg.text.split(maxsplit=1)
    if len(parts) < 2:
        await msg.answer("Iltimos: /newbook <nom> formatida yuboring. Misol: /newbook Inglizcha")
        return
    name = parts[1].strip()
    book_id = await create_book(msg.from_user.id, name)
    if book_id:
        await msg.answer(f"✅ '{name}' lug'ati yaratildi (id={book_id}).")
    else:
        await msg.answer("Lug'at yaratilishda muammo bo'ldi yoki shunday nom bilan lug'at mavjud.")

@router.callback_query(lambda c: c.data == "create_book")
async def cb_create_book(cb: CallbackQuery, state: FSMContext):
    await cb.message.answer("Yangi lug'at nomini kiriting:")
    await state.set_state(VocabStates.waiting_book_name)
    await cb.answer()

@router.message(VocabStates.waiting_book_name)
async def process_book_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if not name:
        await message.reply("Nomi bo'sh bo'lishi mumkin emas. Qaytadan kiriting:")
        return
    bid = await create_book(message.from_user.id, name)
    await message.answer(f"Lug'at yaratildi: {name} (id={bid})")
    await state.clear()

@router.callback_query(lambda c: c.data and c.data.startswith("book:"))
async def cb_book_menu(cb: CallbackQuery):
    book_id = int(cb.data.split(":", 1)[1])
    kb = make_book_menu_kb(book_id)
    await cb.message.answer("Lug'at menyusi:", reply_markup=kb)
    await cb.answer()

@router.callback_query(lambda c: c.data and c.data.startswith("add:"))
async def cb_add_from_menu(cb: CallbackQuery, state: FSMContext):
    book_id = int(cb.data.split(":", 1)[1])
    await state.update_data(book_id=book_id)
    await state.set_state(VocabStates.waiting_word_list)
    await cb.message.answer("So'zlarni yuboring (har qatorda: word-translation yoki word:translation).")
    await cb.answer()

@router.message(VocabStates.waiting_word_list)
async def process_word_list(message: Message, state: FSMContext):
    data = await state.get_data()
    book_id = data.get("book_id")
    if not book_id:
        await message.reply("Qaysi lug'atga qo'shish kerakligi noma'lum. /mybooks orqali tanlang yoki /addwords <book_id> bilan boshlang.")
        await state.clear()
        return
    pairs = parse_pairs_from_text(message.text)
    if not pairs:
        await message.reply("Hech qanday to'g'ri juftlik topilmadi. Format: word-translation")
        return
    n = await add_entries_bulk(book_id, pairs)
    await message.answer(f"✅ {n} ta juftlik lug'atga qo'shildi.")
    await state.clear()

@router.message(Command("addwords"))
async def cmd_addwords(msg: Message, state: FSMContext):
    parts = msg.text.strip().split()
    if len(parts) < 2:
        await msg.reply("Iltimos: /addwords <book_id>")
        return
    try:
        book_id = int(parts[1])
    except ValueError:
        await msg.reply("Noto'g'ri book_id.")
        return
    # boshqalar tekshirish: owner tekshirish
    owner = await db_exec("SELECT id FROM vocab_books WHERE id=%s AND user_id=%s", (book_id, msg.from_user.id), fetch=True)
    if not owner:
        await msg.reply("Bunday lug'at topilmadi yoki sizga tegishli emas.")
        return
    await state.update_data(book_id=book_id)
    await state.set_state(VocabStates.waiting_word_list)
    await msg.answer("So'zlarni yuboring (har qatorda: word-translation).")

# ---- Practice handlers ----
@router.callback_query(lambda c: c.data and c.data.startswith("practice:"))
async def start_practice(cb: CallbackQuery, state: FSMContext):
    book_id = int(cb.data.split(":", 1)[1])
    session = await start_session(cb.from_user.id, book_id)
    if not session:
        await cb.answer("Sessiya yaratib bo'lmadi.", show_alert=True)
        return
    await state.update_data(session_id=session, book_id=book_id)
    await state.set_state(VocabStates.practicing)
    await cb.answer()
    await send_question(cb.message, state)

async def send_question(msg: Message, state: FSMContext):
    data = await state.get_data()
    book_id = data.get("book_id")
    session_id = data.get("session_id")
    if not book_id or not session_id:
        await msg.answer("Sessiya ma'lumotlari yo'q.")
        return
    entries = await db_exec("SELECT id, word_src, word_trg FROM vocab_entries WHERE book_id=%s AND is_active=TRUE", (book_id,), fetch=True, many=True)
    if not entries:
        await msg.answer("❌ Bu lug'at bo'sh. Avval so'z qo'shing.")
        await state.clear()
        return
    entry = random.choice(entries)
    ask_src = random.choice([True, False])
    presented = entry["word_src"] if ask_src else entry["word_trg"]
    correct = entry["word_trg"] if ask_src else entry["word_src"]

    # prepare distractors
    pool = [e["word_trg"] if ask_src else e["word_src"] for e in entries if e["id"] != entry["id"]]
    wrongs = random.sample(pool, min(3, len(pool))) if pool else []
    # if not enough wrongs, get additional from DB global pool
    if len(wrongs) < 3:
        more = await db_exec(
            ("SELECT word_trg as val FROM vocab_entries WHERE id != %s ORDER BY random() LIMIT %s") if ask_src else
            ("SELECT word_src as val FROM vocab_entries WHERE id != %s ORDER BY random() LIMIT %s"),
            (entry["id"], 3 - len(wrongs)), fetch=True, many=True
        )
        if more:
            wrongs.extend([m["val"] for m in more])

    choices = wrongs + [correct]
    random.shuffle(choices)

    # save current question to session.meta
    current = {"entry_id": entry["id"], "presented": presented, "choices": choices, "direction": "src2trg" if ask_src else "trg2src"}
    await db_exec("UPDATE practice_sessions SET meta = jsonb_set(coalesce(meta, '{}'::jsonb), '{current_question}', %s::jsonb, true) WHERE id = %s", (json.dumps(current, ensure_ascii=False), session_id))

    # build keyboard
    buttons = [[InlineKeyboardButton(text=opt, callback_data=f"ans:{entry['id']}:{idx}")] for idx, opt in enumerate(choices)]
    buttons.append([InlineKeyboardButton(text="🏁 Tugatish", callback_data="end")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    # persist question record (without chosen yet)
    await db_exec(
        "INSERT INTO practice_questions (session_id, entry_id, presented_text, correct_translation, choices, asked_at) VALUES (%s,%s,%s,%s,%s::jsonb,now())",
        (session_id, entry["id"], presented, correct, json.dumps(choices, ensure_ascii=False))
    )

    await msg.answer(f"❓ {presented}", reply_markup=kb)

@router.callback_query(lambda c: c.data and c.data.startswith("ans:"))
async def answer_question(cb: CallbackQuery, state: FSMContext):
    # data: ans:{entry_id}:{choice_idx}
    parts = cb.data.split(":", 2)
    if len(parts) != 3:
        await cb.answer()
        return
    _, entry_id_s, choice_idx_s = parts
    try:
        entry_id = int(entry_id_s)
        choice_idx = int(choice_idx_s)
    except ValueError:
        await cb.answer()
        return

    data = await state.get_data()
    session_id = data.get("session_id")
    if not session_id:
        await cb.answer("Sessiya topilmadi.", show_alert=True)
        return

    # get last question record for this entry and session
    q = await db_exec("SELECT id, correct_translation, choices FROM practice_questions WHERE session_id=%s AND entry_id=%s ORDER BY id DESC LIMIT 1", (session_id, entry_id), fetch=True)
    if not q:
        await cb.answer("Savol topilmadi yoki muddati o'tgan.", show_alert=True)
        return

    qid = q["id"]
    correct = q["correct_translation"]
    choices = json.loads(q["choices"]) if isinstance(q["choices"], str) else q["choices"]
    try:
        chosen_text = choices[choice_idx]
    except Exception:
        await cb.answer("Noto'g'ri javob tanlandi.", show_alert=True)
        return

    is_correct = (chosen_text == correct)
    # update question row with answer
    await db_exec("UPDATE practice_questions SET chosen_option=%s, is_correct=%s, answered_at=now() WHERE id=%s", (chosen_text, is_correct, qid))
    # update session stats
    if is_correct:
        await db_exec("UPDATE practice_sessions SET correct_count = correct_count + 1, total_questions = total_questions + 1 WHERE id = %s", (session_id,))
        await cb.answer("✅ To'g'ri")
    else:
        await db_exec("UPDATE practice_sessions SET wrong_count = wrong_count + 1, total_questions = total_questions + 1 WHERE id = %s", (session_id,))
        await cb.answer(f"❌ Noto'g'ri. To'g'ri: {correct}")

    # send next question
    await send_question(cb.message, state)

@router.callback_query(lambda c: c.data == "end")
async def end_practice(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    session_id = data.get("session_id")
    if not session_id:
        await cb.answer("Sessiya topilmadi.", show_alert=True)
        return
    s = await db_exec("SELECT total_questions, correct_count, wrong_count FROM practice_sessions WHERE id=%s", (session_id,), fetch=True)
    if s:
        await cb.message.answer(f"📊 Natijalar:\nJami: {s['total_questions']}\nTo'g'ri: {s['correct_count']}\nXato: {s['wrong_count']}")
    await state.clear()
    await cb.answer("Mashq tugadi.")

# Export router
__all__ = ["router"]