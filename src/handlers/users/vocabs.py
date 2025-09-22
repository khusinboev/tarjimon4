# src/handlers/users/vocabs.py
import json
import asyncio
import random
from datetime import datetime
from typing import List, Optional, Dict, Any

from aiogram import Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.utils.exceptions import MessageNotModified, TelegramAPIError

# config.py dan global obyektlar (db, sql, bot) olinadi
from config import sql, db, bot

router = Router()

# ---- FSM states ----
class VocabStates(StatesGroup):
    waiting_book_name = State()
    waiting_word_list = State()
    practicing = State()

# ---- DB helper: async wrapper ----
async def db_exec(query: str, params: tuple = None, fetch: bool = False, many: bool = False) -> Optional[Any]:
    """
    - fetch=False: bajaradi va None qaytaradi
    - fetch=True, many=False: bitta qator dict yoki None
    - fetch=True, many=True: ro'yxat (har element dict) yoki []
    """
    def run():
        cur = db.cursor()
        cur.execute(query, params or ())
        if fetch:
            desc = cur.description
            if not desc:
                return None
            cols = [d[0] for d in desc]
            if many:
                rows = cur.fetchall()
                return [dict(zip(cols, r)) for r in rows]
            row = cur.fetchone()
            return dict(zip(cols, row)) if row else None
        # commit only for non-fetch statements if needed (db.autocommit True in config, but keep for safety)
        try:
            db.commit()
        except Exception:
            pass
        return None
    return await asyncio.to_thread(run)

# ---- UI utility helpers ----
async def safe_edit_or_send(chat_id: int, message_id: int, text: str, reply_markup: InlineKeyboardMarkup = None) -> Dict[str, int]:
    """
    Try to edit message (chat_id, message_id) with text+markup.
    If editing fails (deleted / not-modified / permissions), try delete then send new message.
    Returns dict: {"chat_id":..., "message_id":...}
    """
    try:
        # try edit
        await bot.edit_message_text(text, chat_id=chat_id, message_id=message_id, reply_markup=reply_markup)
        return {"chat_id": chat_id, "message_id": message_id}
    except MessageNotModified:
        # nothing changed (still okay) - keep ids
        return {"chat_id": chat_id, "message_id": message_id}
    except Exception:
        # fallback: try delete then send
        try:
            await bot.delete_message(chat_id=chat_id, message_id=message_id)
        except Exception:
            pass
        m = await bot.send_message(chat_id, text, reply_markup=reply_markup)
        return {"chat_id": m.chat.id, "message_id": m.message_id}

def build_cabinet_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📚 Mening lug'atlarim", callback_data="cab_books")],
        [InlineKeyboardButton(text="➕ Yangi lug'at", callback_data="cab_new")],
        [InlineKeyboardButton(text="➕ So'z qo'shish", callback_data="cab_add")],
        [InlineKeyboardButton(text="▶ Mashq", callback_data="cab_practice")],
        [InlineKeyboardButton(text="🔙 Chiqish", callback_data="cab_close")],
    ])
    return kb

def build_books_kb(rows: List[Dict[str, Any]], prefix: str = "book:") -> InlineKeyboardMarkup:
    buttons = []
    for r in rows:
        buttons.append([InlineKeyboardButton(text=r["name"], callback_data=f"{prefix}{r['id']}")])
    # helper actions
    buttons.append([InlineKeyboardButton(text="➕ Yangi lug'at", callback_data="cab_new")])
    buttons.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="cab_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def build_book_menu_kb(book_id: int) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="▶ Mashq", callback_data=f"practice_book:{book_id}")],
        [InlineKeyboardButton(text="➕ So'z qo'shish", callback_data=f"add_to:{book_id}")],
        [InlineKeyboardButton(text="🗑️ O'chirish", callback_data=f"del_book:{book_id}")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="cab_books")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ---- Parsing helper ----
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

# ---- DB domain helpers (as before) ----
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
        try:
            db.commit()
        except Exception:
            pass
    await asyncio.to_thread(run_many)
    return len(args)

async def start_session(user_id: int, book_id: int) -> int:
    row = await db_exec(
        "INSERT INTO practice_sessions (user_id, book_id, started_at, meta) VALUES (%s, %s, now(), '{}'::jsonb) RETURNING id",
        (user_id, book_id),
        fetch=True
    )
    return row["id"] if row else 0

async def finish_session(session_id: int):
    await db_exec("UPDATE practice_sessions SET finished_at = now() WHERE id = %s", (session_id,))

# ---- /cabinet handler ----
@router.message(Command("cabinet"))
async def cmd_cabinet(msg: Message, state: FSMContext):
    """
    Kabinetni ochadi va UI xabarini saqlaydi (so'nggi xabarni edit qilish uchun).
    """
    # Agar oldingi ui_message mavjud bo'lsa, o'chirishga harakat qilamiz (tozalash)
    data = await state.get_data()
    prev = data.get("ui_message")
    if prev:
        try:
            await bot.delete_message(prev["chat_id"], prev["message_id"])
        except Exception:
            pass

    text = "🔧 *Kabinet*\nBo'limni tanlang:"
    kb = build_cabinet_kb()
    sent = await msg.answer(text, reply_markup=kb)
    await state.update_data(ui_message={"chat_id": sent.chat.id, "message_id": sent.message_id})

# ---- Callback: asosiy kabinetga qaytish ----
@router.callback_query(lambda c: c.data == "cab_main")
async def cb_cab_main(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    ui = data.get("ui_message")
    text = "🔧 *Kabinet*\nBo'limni tanlang:"
    kb = build_cabinet_kb()
    if ui:
        res = await safe_edit_or_send(ui["chat_id"], ui["message_id"], text, kb)
        await state.update_data(ui_message=res)
    else:
        m = await cb.message.answer(text, reply_markup=kb)
        await state.update_data(ui_message={"chat_id": m.chat.id, "message_id": m.message_id})
    await cb.answer()

# ---- Callback: close kabinet (delete xabar) ----
@router.callback_query(lambda c: c.data == "cab_close")
async def cb_cab_close(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    ui = data.get("ui_message")
    if ui:
        try:
            await bot.delete_message(ui["chat_id"], ui["message_id"])
        except Exception:
            pass
    await state.clear()
    await cb.answer("Kabinet yopildi.", show_alert=True)

# ---- Callback: show books ----
@router.callback_query(lambda c: c.data == "cab_books")
async def cb_cab_books(cb: CallbackQuery, state: FSMContext):
    rows = await list_books(cb.from_user.id)
    text = "📚 *Sizning lug'atlaringiz:*" if rows else "📚 Sizda hozircha lug'at yo'q."
    kb = build_books_kb(rows, prefix="book:")
    data = await state.get_data()
    ui = data.get("ui_message")
    if ui:
        res = await safe_edit_or_send(ui["chat_id"], ui["message_id"], text, kb)
        await state.update_data(ui_message=res)
    else:
        m = await cb.message.answer(text, reply_markup=kb)
        await state.update_data(ui_message={"chat_id": m.chat.id, "message_id": m.message_id})
    await cb.answer()

# ---- Callback: single book menu ----
@router.callback_query(lambda c: c.data and c.data.startswith("book:"))
async def cb_book_menu(cb: CallbackQuery, state: FSMContext):
    book_id = int(cb.data.split(":", 1)[1])
    # show book menu (edit)
    text = "📘 Lug'at menyusi:"
    kb = build_book_menu_kb(book_id)
    data = await state.get_data()
    ui = data.get("ui_message")
    if ui:
        res = await safe_edit_or_send(ui["chat_id"], ui["message_id"], text, kb)
        await state.update_data(ui_message=res)
    else:
        m = await cb.message.answer(text, reply_markup=kb)
        await state.update_data(ui_message={"chat_id": m.chat.id, "message_id": m.message_id})
    await cb.answer()

# ---- Callback: create new book (show prompt) ----
@router.callback_query(lambda c: c.data == "cab_new")
async def cb_cab_new(cb: CallbackQuery, state: FSMContext):
    text = "➕ *Yangi lug'at yaratish*\nLug'at nomini kiriting:"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cab_main")]
    ])
    data = await state.get_data()
    ui = data.get("ui_message")
    if ui:
        res = await safe_edit_or_send(ui["chat_id"], ui["message_id"], text, kb)
        await state.update_data(ui_message=res)
    else:
        m = await cb.message.answer(text, reply_markup=kb)
        await state.update_data(ui_message={"chat_id": m.chat.id, "message_id": m.message_id})
    await state.set_state(VocabStates.waiting_book_name)
    await cb.answer()

@router.message(VocabStates.waiting_book_name)
async def process_book_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if not name:
        await message.reply("Nomi bo'sh bo'lishi mumkin emas. Qaytadan kiriting yoki /cabinet bilan chiqib qayta urin.")
        return
    bid = await create_book(message.from_user.id, name)
    # prepare response: show success and back to cabinet
    text = f"✅ Lug'at yaratildi: *{name}* (id={bid}).\nOrqaga qaytish:"
    kb = build_cabinet_kb()
    data = await state.get_data()
    ui = data.get("ui_message")
    if ui:
        res = await safe_edit_or_send(ui["chat_id"], ui["message_id"], text, kb)
        await state.update_data(ui_message=res)
    else:
        m = await message.answer(text, reply_markup=kb)
        await state.update_data(ui_message={"chat_id": m.chat.id, "message_id": m.message_id})
    await state.clear()

# ---- Callback: add words path (choose book) ----
@router.callback_query(lambda c: c.data == "cab_add")
async def cb_cab_add(cb: CallbackQuery, state: FSMContext):
    rows = await list_books(cb.from_user.id)
    if not rows:
        text = "Sizda lug'at yo'q. Avval lug'at yarating."
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton("➕ Yangi lug'at", callback_data="cab_new")],[InlineKeyboardButton("🔙 Orqaga", callback_data="cab_main")]])
        data = await state.get_data()
        ui = data.get("ui_message")
        if ui:
            res = await safe_edit_or_send(ui["chat_id"], ui["message_id"], text, kb)
            await state.update_data(ui_message=res)
        else:
            m = await cb.message.answer(text, reply_markup=kb)
            await state.update_data(ui_message={"chat_id": m.chat.id, "message_id": m.message_id})
        await cb.answer()
        return
    text = "➕ Qaysi lug'atga so'z qo'shasiz?"
    kb = build_books_kb(rows, prefix="add_to:")
    data = await state.get_data()
    ui = data.get("ui_message")
    if ui:
        res = await safe_edit_or_send(ui["chat_id"], ui["message_id"], text, kb)
        await state.update_data(ui_message=res)
    else:
        m = await cb.message.answer(text, reply_markup=kb)
        await state.update_data(ui_message={"chat_id": m.chat.id, "message_id": m.message_id})
    await cb.answer()

@router.callback_query(lambda c: c.data and c.data.startswith("add_to:"))
async def cb_add_to(cb: CallbackQuery, state: FSMContext):
    book_id = int(cb.data.split(":", 1)[1])
    # set state and ask for words
    text = "So'zlarni yuboring (har qatorda: word-translation yoki word:translation)."
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton("🔙 Orqaga", callback_data="cab_books")]])
    data = await state.get_data()
    ui = data.get("ui_message")
    if ui:
        res = await safe_edit_or_send(ui["chat_id"], ui["message_id"], text, kb)
        await state.update_data(ui_message=res)
    else:
        m = await cb.message.answer(text, reply_markup=kb)
        await state.update_data(ui_message={"chat_id": m.chat.id, "message_id": m.message_id})
    await state.update_data(book_id=book_id)
    await state.set_state(VocabStates.waiting_word_list)
    await cb.answer()

@router.message(VocabStates.waiting_word_list)
async def process_word_list(message: Message, state: FSMContext):
    data = await state.get_data()
    book_id = data.get("book_id")
    if not book_id:
        await message.reply("Qaysi lug'atga qo'shish kerakligi noma'lum. /cabinet orqali boshlang.")
        await state.clear()
        return
    pairs = parse_pairs_from_text(message.text)
    if not pairs:
        await message.reply("Hech qanday to'g'ri juftlik topilmadi. Format: word-translation (har qatorda).")
        return
    n = await add_entries_bulk(book_id, pairs)
    text = f"✅ {n} ta juftlik lug'atga qo'shildi."
    kb = build_cabinet_kb()
    data = await state.get_data()
    ui = data.get("ui_message")
    if ui:
        res = await safe_edit_or_send(ui["chat_id"], ui["message_id"], text, kb)
        await state.update_data(ui_message=res)
    else:
        m = await message.answer(text, reply_markup=kb)
        await state.update_data(ui_message={"chat_id": m.chat.id, "message_id": m.message_id})
    await state.clear()

# ---- Callback: start practice (choose book) ----
@router.callback_query(lambda c: c.data == "cab_practice")
async def cb_cab_practice(cb: CallbackQuery, state: FSMContext):
    rows = await list_books(cb.from_user.id)
    if not rows:
        text = "Sizda lug'at yo'q. Avval lug'at yaratib oling."
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton("➕ Yangi lug'at", callback_data="cab_new")],[InlineKeyboardButton("🔙 Orqaga", callback_data="cab_main")]])
        data = await state.get_data()
        ui = data.get("ui_message")
        if ui:
            res = await safe_edit_or_send(ui["chat_id"], ui["message_id"], text, kb)
            await state.update_data(ui_message=res)
        else:
            m = await cb.message.answer(text, reply_markup=kb)
            await state.update_data(ui_message={"chat_id": m.chat.id, "message_id": m.message_id})
        await cb.answer()
        return
    text = "▶ Qaysi lug'atdan mashq qilamiz?"
    kb = build_books_kb(rows, prefix="practice_book:")
    data = await state.get_data()
    ui = data.get("ui_message")
    if ui:
        res = await safe_edit_or_send(ui["chat_id"], ui["message_id"], text, kb)
        await state.update_data(ui_message=res)
    else:
        m = await cb.message.answer(text, reply_markup=kb)
        await state.update_data(ui_message={"chat_id": m.chat.id, "message_id": m.message_id})
    await cb.answer()

# ---- Callback: choose specific book to practice ----
@router.callback_query(lambda c: c.data and c.data.startswith("practice_book:"))
async def cb_practice_book(cb: CallbackQuery, state: FSMContext):
    book_id = int(cb.data.split(":", 1)[1])
    session = await start_session(cb.from_user.id, book_id)
    if not session:
        await cb.answer("Sessiya yaratib bo'lmadi.", show_alert=True)
        return
    await state.update_data(session_id=session, book_id=book_id)
    await state.set_state(VocabStates.practicing)
    # kirish xabari (oldingi ui_messageni tahrirlaymiz) va darhol savol yuboramiz (edit orqali)
    text = "▶ Mashq boshlandi. Savollar quyida."
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Tugatish", callback_data="end_practice")]])
    data = await state.get_data()
    ui = data.get("ui_message")
    if ui:
        res = await safe_edit_or_send(ui["chat_id"], ui["message_id"], text, kb)
        await state.update_data(ui_message=res)
    else:
        m = await cb.message.answer(text, reply_markup=kb)
        await state.update_data(ui_message={"chat_id": m.chat.id, "message_id": m.message_id})
    await cb.answer()
    # yuborish birinchi savolini
    await send_question(state)

# ---- Core: send_question (edits existing UI message used for session) ----
async def send_question(state: FSMContext):
    data = await state.get_data()
    book_id = data.get("book_id")
    session_id = data.get("session_id")
    ui = data.get("ui_message")
    if not book_id or not session_id:
        # fallback: show cabinet
        text = "Sessiya ma'lumotlari yetarli emas. /cabinet orqali qayta boshlang."
        kb = build_cabinet_kb()
        if ui:
            res = await safe_edit_or_send(ui["chat_id"], ui["message_id"], text, kb)
            await state.update_data(ui_message=res)
        return

    entries = await db_exec("SELECT id, word_src, word_trg FROM vocab_entries WHERE book_id=%s AND is_active=TRUE", (book_id,), fetch=True, many=True)
    if not entries:
        text = "❌ Bu lug'at bo'sh. Mashqni tugataman."
        kb = build_cabinet_kb()
        if ui:
            res = await safe_edit_or_send(ui["chat_id"], ui["message_id"], text, kb)
            await state.update_data(ui_message=res)
        await state.clear()
        return

    entry = random.choice(entries)
    ask_src = random.choice([True, False])
    presented = entry["word_src"] if ask_src else entry["word_trg"]
    correct = entry["word_trg"] if ask_src else entry["word_src"]

    # distractors
    pool = [e["word_trg"] if ask_src else e["word_src"] for e in entries if e["id"] != entry["id"]]
    wrongs = random.sample(pool, min(3, len(pool))) if pool else []
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

    # update session.meta current question
    current = {"entry_id": entry["id"], "presented": presented, "choices": choices, "direction": "src2trg" if ask_src else "trg2src"}
    await db_exec("UPDATE practice_sessions SET meta = jsonb_set(coalesce(meta, '{}'::jsonb), '{current_question}', %s::jsonb, true) WHERE id = %s", (json.dumps(current, ensure_ascii=False), session_id))

    # persist question record (without chosen yet)
    await db_exec(
        "INSERT INTO practice_questions (session_id, entry_id, presented_text, correct_translation, choices, asked_at) VALUES (%s,%s,%s,%s,%s::jsonb,now())",
        (session_id, entry["id"], presented, correct, json.dumps(choices, ensure_ascii=False))
    )

    # build keyboard
    buttons = [[InlineKeyboardButton(text=opt, callback_data=f"ans:{entry['id']}:{idx}")] for idx, opt in enumerate(choices)]
    buttons.append([InlineKeyboardButton(text="🏁 Tugatish", callback_data="end_practice")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    text = f"❓ *{presented}*"
    if ui:
        res = await safe_edit_or_send(ui["chat_id"], ui["message_id"], text, kb)
        await state.update_data(ui_message=res)
    else:
        # send fresh message if no ui saved
        m = await bot.send_message(chat_id=data.get("chat_id") or 0, text=text, reply_markup=kb)
        await state.update_data(ui_message={"chat_id": m.chat.id, "message_id": m.message_id})

# ---- Answer handler (practice) ----
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
        await db_exec("UPDATE practice_sessions SET correct_count = coalesce(correct_count,0) + 1, total_questions = coalesce(total_questions,0) + 1 WHERE id = %s", (session_id,))
        await cb.answer("✅ To'g'ri")
    else:
        await db_exec("UPDATE practice_sessions SET wrong_count = coalesce(wrong_count,0) + 1, total_questions = coalesce(total_questions,0) + 1 WHERE id = %s", (session_id,))
        await cb.answer(f"❌ Noto'g'ri. To'g'ri: {correct}")

    # send next question (edit same message)
    await send_question(state)

# ---- End practice callback ----
@router.callback_query(lambda c: c.data == "end_practice" or c.data == "end")
async def end_practice(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    session_id = data.get("session_id")
    ui = data.get("ui_message")
    if not session_id:
        await cb.answer("Sessiya topilmadi.", show_alert=True)
        return
    s = await db_exec("SELECT total_questions, correct_count, wrong_count FROM practice_sessions WHERE id=%s", (session_id,), fetch=True)
    if s:
        text = f"📊 *Natijalar:*\nJami: {s.get('total_questions',0)}\nTo'g'ri: {s.get('correct_count',0)}\nXato: {s.get('wrong_count',0)}"
    else:
        text = "Sessiya haqida ma'lumot topilmadi."
    kb = build_cabinet_kb()
    if ui:
        res = await safe_edit_or_send(ui["chat_id"], ui["message_id"], text, kb)
        await state.update_data(ui_message=res)
    await finish_session(session_id)
    await state.clear()
    await cb.answer("Mashq tugadi.")

# ---- Optional: delete book (minimal safety) ----
@router.callback_query(lambda c: c.data and c.data.startswith("del_book:"))
async def cb_delete_book(cb: CallbackQuery, state: FSMContext):
    book_id = int(cb.data.split(":", 1)[1])
    # minimal ownership check
    owner = await db_exec("SELECT id FROM vocab_books WHERE id=%s AND user_id=%s",(book_id, cb.from_user.id), fetch=True)
    if not owner:
        await cb.answer("Bunday lug'at topilmadi yoki sizga tegishli emas.", show_alert=True)
        return
    # delete (soft or hard — ovqatga moslab o'zgartiring)
    await db_exec("DELETE FROM vocab_entries WHERE book_id=%s", (book_id,))
    await db_exec("DELETE FROM vocab_books WHERE id=%s", (book_id,))
    data = await state.get_data()
    ui = data.get("ui_message")
    text = "🗑️ Lug'at o'chirildi."
    kb = build_cabinet_kb()
    if ui:
        res = await safe_edit_or_send(ui["chat_id"], ui["message_id"], text, kb)
        await state.update_data(ui_message=res)
    await cb.answer("Lug'at o'chirildi.", show_alert=True)

# Export router
__all__ = ["router"]