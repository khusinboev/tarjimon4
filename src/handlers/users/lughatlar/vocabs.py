import asyncio
import random
import os
from typing import List, Dict, Any, Optional, Tuple

from aiogram import Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from openpyxl import Workbook
from config import db

vocabs_router = Router()

# Sahifalash uchun konstanta
BOOKS_PER_PAGE = 30

# =====================================================
# 📌 Localization (kengaytirilgan)
# =====================================================
LOCALES = {
    "uz": {
        "cabinet": "📚 Kabinet",
        "choose_lang": "Tilni tanlang:",
        "my_books": "📖 Lug'atlarim",
        "practice": "🏋️ Mashq",
        "public_vocabs": "🌐 Ommaviy lug'atlar",
        "settings": "⚙️ Sozlamalar",
        "back": "🔙 Orqaga",
        "add_words": "➕ So'z qo'shish",
        "delete": "❌ O'chirish",
        "export": "📤 Eksport",
        "confirm_delete": "❓ Ushbu lug'atni o'chirishga ishonchingiz komilmi?",
        "yes": "✅ Ha",
        "no": "❌ Yo'q",
        "results": "📊 Natijalar:\nJami: {total}\nTo'g'ri: {correct}\nXato: {wrong}",
        "results_header": "📊 Batafsil natijalar:",
        "results_lines": (
            "📹 Savollar soni: {unique}\n"
            "📹 Jami berilgan savollar: {answers}\n"
            "✅ To'g'ri javoblar: {correct}\n"
            "❌ Xato javoblar: {wrong}\n"
            "📊 Natijaviy ko'rsatgich: {percent:.1f}%"
        ),
        "no_books": "Sizda hali lug'at yo'q.",
        "enter_book_name": "Yangi lug'at nomini kiriting:",
        "book_created": "✅ Lug'at yaratildi: {name} (id={id})",
        "book_exists": "❌ Bu nom bilan lug'at mavjud.",
        "send_pairs": "So'zlarni yuboring (har qatorda: word-translation).",
        "added_pairs": "✅ {n} ta juftlik qo'shildi. Yana yuborishingiz mumkin 👇",
        "empty_book": "❌ Bu lug'atda yetarli so'zlar yo'q (kamida 4 ta kerak).",
        "question": "❓ {word}",
        "correct": "✅ To'g'ri",
        "wrong": "❌ Xato. To'g'ri javob: {correct}",
        "finish": "🏁 Tugatish",
        "session_end": "Mashq tugadi.",
        "back_to_book": "🔙 Orqaga",
        "main_menu": "🏠 Bosh menyu",
        "cancel": "❌ Bekor qilish",
        "next_page": "➡️ Keyingi",
        "prev_page": "⬅️ Oldingi",
        "page_info": "📄 {current}/{total}",
        "no_public_books": "Hozircha ommaviy lug'atlar yo'q.",
        "author": "👤 Muallif:",
        "word_count": "📊 So'zlar:",
        "created": "📅 Yaratilgan:",
        "status_public": "🌐 Ommaviy",
        "status_private": "🔒 Shaxsiy",
    },
    "en": {
        "cabinet": "📚 Cabinet",
        "choose_lang": "Choose your language:",
        "my_books": "📖 My vocabularies",
        "practice": "🏋️ Practice",
        "public_vocabs": "🌐 Public vocabularies",
        "settings": "⚙️ Settings",
        "back": "🔙 Back",
        "add_words": "➕ Add words",
        "delete": "❌ Delete",
        "export": "📤 Export",
        "confirm_delete": "❓ Are you sure you want to delete this book?",
        "yes": "✅ Yes",
        "no": "❌ No",
        "results": "📊 Results:\nTotal: {total}\nCorrect: {correct}\nWrong: {wrong}",
        "results_header": "📊 Detailed Results:",
        "results_lines": (
            "📹 Questions in set: {unique}\n"
            "📹 Total asked: {answers}\n"
            "✅ Correct: {correct}\n"
            "❌ Wrong: {wrong}\n"
            "📊 Performance: {percent:.1f}%"
        ),
        "no_books": "You have no books yet.",
        "enter_book_name": "Enter new book name:",
        "book_created": "✅ Book created: {name} (id={id})",
        "book_exists": "❌ Book with this name already exists.",
        "send_pairs": "Send word pairs (each line: word-translation).",
        "added_pairs": "✅ {n} pairs added. You can send more 👇",
        "empty_book": "❌ This book doesn't have enough words (min 4).",
        "question": "❓ {word}",
        "correct": "✅ Correct",
        "wrong": "❌ Wrong. Correct: {correct}",
        "finish": "🏁 Finish",
        "session_end": "Practice finished.",
        "back_to_book": "🔙 Back",
        "main_menu": "🏠 Main menu",
        "cancel": "❌ Cancel",
        "next_page": "➡️ Next",
        "prev_page": "⬅️ Previous",
        "page_info": "📄 {current}/{total}",
        "no_public_books": "No public vocabularies available yet.",
        "author": "👤 Author:",
        "word_count": "📊 Words:",
        "created": "📅 Created:",
        "status_public": "🌐 Public",
        "status_private": "🔒 Private",
    }
}


# =====================================================
# 📌 Database helpers (optimized)
# =====================================================

async def db_exec(query: str, params: tuple = None, fetch: bool = False, many: bool = False):
    def run():
        cur = db.cursor()
        cur.execute(query, params or ())
        if fetch:
            if many:
                rows = cur.fetchall()
                if not rows:
                    return []
                cols = [d[0] for d in cur.description]
                return [dict(zip(cols, r)) for r in rows]
            else:
                row = cur.fetchone()
                if not row:
                    return None
                cols = [d[0] for d in cur.description]
                return dict(zip(cols, row))
        db.commit()
        return None

    return await asyncio.to_thread(run)


async def get_user_data(user_id: int) -> Dict[str, Any]:
    """Fetch user lang and books in one query batch for optimization."""
    lang_row = await db_exec(
        "SELECT interface_lang FROM users WHERE user_id=%s",
        (user_id,), fetch=True
    )
    lang = lang_row["interface_lang"] if lang_row else "uz"

    # Lug'atlar bilan birga ularning holati ham olinadi
    books = await db_exec(
        """SELECT id,
                  name,
                  is_public,
                  (SELECT COUNT(*) FROM vocab_entries WHERE book_id = vocab_books.id) as word_count,
                  created_at::date as created_date
           FROM vocab_books
           WHERE user_id = %s
           ORDER BY created_at DESC""",
        (user_id,), fetch=True, many=True
    )
    return {"lang": lang, "books": books or []}


async def get_paginated_books(user_id: int, page: int = 0, per_page: int = BOOKS_PER_PAGE,
                              public_only: bool = False, exclude_user: bool = False,
                              min_words: int = 0) -> Tuple[List[Dict], int]:
    """
    Sahifalangan lug'atlar ro'yxatini olish.

    Args:
        user_id: Foydalanuvchi ID
        page: Sahifa raqami
        per_page: Har sahifadagi elementlar soni
        public_only: Faqat ommaviy lug'atlarni olish
        exclude_user: Foydalanuvchining o'z lug'atlarini chiqarib tashlash
        min_words: Minimal so'z soni (0 = cheklovsiz)
    """
    offset = page * per_page

    base_query = """
                 SELECT vb.id,
                        vb.name,
                        vb.is_public,
                        vb.user_id,
                        vb.created_at::date as created_date, COALESCE(a.user_id::text, 'Unknown') as author_name,
                        COUNT(ve.id) as word_count
                 FROM vocab_books vb
                          LEFT JOIN users a ON vb.user_id = a.user_id
                          LEFT JOIN vocab_entries ve ON vb.id = ve.book_id
                 WHERE 1 = 1 \
                 """

    params = []

    if public_only:
        base_query += " AND vb.is_public = TRUE"
        if exclude_user:
            base_query += " AND vb.user_id != %s"
            params.append(user_id)
    else:
        base_query += " AND vb.user_id = %s"
        params.append(user_id)

    base_query += """
        GROUP BY vb.id, vb.name, vb.is_public, vb.user_id, vb.created_at, a.user_id
    """

    # Minimal so'z soni cheklovi
    if min_words > 0:
        base_query += f" HAVING COUNT(ve.id) >= {min_words}"

    base_query += """
        ORDER BY vb.created_at DESC
        LIMIT %s OFFSET %s
    """

    params.extend([per_page, offset])

    books = await db_exec(base_query, tuple(params), fetch=True, many=True)

    # Umumiy soni
    count_query = base_query.replace(
        "SELECT vb.id, vb.name, vb.is_public, vb.user_id, vb.created_at::date as created_date, COALESCE(a.user_id::text, 'Unknown') as author_name, COUNT(ve.id) as word_count",
        "SELECT COUNT(DISTINCT vb.id)"
    )
    count_query = count_query.split("ORDER BY")[0].replace("LIMIT %s OFFSET %s", "")

    count_params = params[:-2] if params else []
    total_result = await db_exec(count_query, tuple(count_params), fetch=True)
    total_count = total_result.get('count', 0) if total_result else 0

    return books or [], total_count


async def set_user_lang(user_id: int, lang: str):
    row = await db_exec(
        "SELECT id FROM users WHERE user_id=%s",
        (user_id,), fetch=True
    )
    if row:
        await db_exec("UPDATE users SET interface_lang=%s WHERE id=%s", (lang, row["id"]))
    else:
        await db_exec("INSERT INTO users (user_id, interface_lang) VALUES (%s,%s)", (user_id, lang))


# =====================================================
# 📌 UI Builders (improved)
# =====================================================
def two_col_rows(buttons: List[InlineKeyboardButton]) -> List[List[InlineKeyboardButton]]:
    rows = []
    for i in range(0, len(buttons), 2):
        row = buttons[i:i + 2]
        rows.append(row)
    return rows


def get_locale(lang: str) -> Dict[str, str]:
    return LOCALES.get(lang, LOCALES["uz"])


def get_book_emoji(is_public: bool, is_own: bool = True) -> str:
    """Lug'at holati bo'yicha emoji qaytarish."""
    if is_own:
        return "🌐" if is_public else "🔒"
    else:
        return "👥" if is_public else "🔒"


def cabinet_kb(lang: str) -> InlineKeyboardMarkup:
    """Asosiy kabinet menyu klaviaturasi."""
    L = get_locale(lang)
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=L["practice"], callback_data="mashq:list")],
        [InlineKeyboardButton(text=L["my_books"], callback_data="lughat:list:0"),
         InlineKeyboardButton(text=L["public_vocabs"], callback_data="ommaviy:list:0")],
        [InlineKeyboardButton(text="📚 Essentiallar", callback_data="essential:main"),
         InlineKeyboardButton(text="🌍 Parallel", callback_data="parallel:main")],  # ⭐ YANGI
        [InlineKeyboardButton(text=L["settings"], callback_data="cab:settings")]
    ])


def settings_kb(lang: str) -> InlineKeyboardMarkup:
    L = get_locale(lang)
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇺🇿 O'zbek", callback_data="lang:uz"),
            InlineKeyboardButton(text="🇬🇧 English", callback_data="lang:en")
        ],
        [InlineKeyboardButton(text=L["back"], callback_data="settings:back_to_cabinet")]
    ])


def create_paginated_kb(books: List[Dict], current_page: int, total_pages: int, prefix: str,
                        lang: str) -> InlineKeyboardMarkup:
    """Sahifalangan klaviatura yaratish."""
    L = get_locale(lang)
    rows = []

    # Lug'atlar tugmalari
    for book in books:
        is_own = prefix == "lughat"
        emoji = get_book_emoji(book["is_public"], is_own)
        text = f"{emoji} {book['name']} ({book['word_count']})"
        callback = f"{prefix}:open:{book['id']}"
        rows.append([InlineKeyboardButton(text=text, callback_data=callback)])

    # Sahifalash tugmalari
    if total_pages > 1:
        nav_row = []
        if current_page > 0:
            nav_row.append(InlineKeyboardButton(text=L["prev_page"], callback_data=f"{prefix}:list:{current_page - 1}"))

        if current_page < total_pages - 1:
            nav_row.append(InlineKeyboardButton(text=L["next_page"], callback_data=f"{prefix}:list:{current_page + 1}"))

        if nav_row:
            rows.append(nav_row)

        # Sahifa ma'lumoti
        page_info = L["page_info"].format(current=current_page + 1, total=total_pages)
        rows.append([InlineKeyboardButton(text=page_info, callback_data="noop")])

    # Boshqa tugmalar
    if prefix == "lughat":
        rows.append([InlineKeyboardButton(text="➕ Yangi lug'at", callback_data="lughat:new")])

    back_callback = {
        "lughat": "lughat:back_to_cabinet",
        "ommaviy": "ommaviy:back_to_cabinet",
        "mashq": "mashq:back_to_cabinet",
    }.get(prefix, "cab:back")
    
    rows.append([InlineKeyboardButton(text=L["back"], callback_data=back_callback)])

    return InlineKeyboardMarkup(inline_keyboard=rows)


# =====================================================
# 📌 Export helper (optimized)
# =====================================================
async def export_book_to_excel(book_id: int, user_id: int) -> Optional[str]:
    rows = await db_exec(
        "SELECT word_src, word_trg FROM vocab_entries WHERE book_id=%s ORDER BY id",
        (book_id,), fetch=True, many=True
    )
    if len(rows) < 1:
        return None

    wb = Workbook()
    ws = wb.active
    ws.title = "Vocabulary"
    ws.append(["Word", "Translation"])
    for r in rows:
        ws.append([r["word_src"], r["word_trg"]])

    file_path = f"export_{user_id}_{book_id}.xlsx"
    wb.save(file_path)
    return file_path


# =====================================================
# 📌 Helper to send message
# =====================================================

async def safe_edit_or_send(cb: CallbackQuery, text: str, kb: InlineKeyboardMarkup, lang: str):
    """Try to edit message first; if fails, delete and send new one."""
    try:
        await cb.message.edit_text(text, reply_markup=kb, parse_mode="html")
    except Exception:
        try:
            await cb.message.delete()
        except Exception:
            pass
        await cb.message.answer(text, reply_markup=kb, parse_mode="html")


# =====================================================
# 📌 Cabinet menu (main)
# =====================================================

@vocabs_router.message(Command("cabinet"))
async def cmd_cabinet(msg: Message):
    data = await get_user_data(msg.from_user.id)
    L = get_locale(data["lang"])
    await msg.answer(L["cabinet"], reply_markup=cabinet_kb(data["lang"]))


@vocabs_router.callback_query(lambda c: c.data and (c.data.startswith("cab:") or 
                                                      c.data in ["settings:back_to_cabinet", 
                                                                 "lughat:back_to_cabinet",
                                                                 "ommaviy:back_to_cabinet",
                                                                 "mashq:back_to_cabinet",
                                                                 "essential:back_to_cabinet",
                                                                 "parallel:back_to_cabinet"]))
async def cb_cabinet(cb: CallbackQuery, state: FSMContext):
    user_id = cb.from_user.id
    data = await get_user_data(user_id)
    lang = data["lang"]
    L = get_locale(lang)

    if cb.data == "cab:settings":
        await safe_edit_or_send(cb, L["choose_lang"], settings_kb(lang), lang)

    elif cb.data in ["cab:back", "settings:back_to_cabinet", "lughat:back_to_cabinet", 
                     "ommaviy:back_to_cabinet", "mashq:back_to_cabinet",
                     "essential:back_to_cabinet", "parallel:back_to_cabinet"]:
        await safe_edit_or_send(cb, L["cabinet"], cabinet_kb(lang), lang)

    try:
        await cb.answer()
    except:
        pass


@vocabs_router.callback_query(lambda c: c.data and c.data.startswith("lang:"))
async def cb_change_lang(cb: CallbackQuery):
    lang = cb.data.split(":")[1]
    await set_user_lang(cb.from_user.id, lang)
    L = get_locale(lang)
    await safe_edit_or_send(cb, L["cabinet"], cabinet_kb(lang), lang)
    await cb.answer()


# Noop callback (sahifa ma'lumoti uchun)
@vocabs_router.callback_query(lambda c: c.data == "noop")
async def cb_noop(cb: CallbackQuery):
    await cb.answer()