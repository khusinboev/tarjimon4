"""
🔗 Comprehensive Callback Handlers for Tarjimon Bot
Handles all inline keyboard callbacks
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest

from config import sql, db, LANGUAGES
from src.keyboards.sophisticated_keyboards import (
    user_kb, lang_selector, practice_kb, game_kb, FancyButtons
)
from src.keyboards.buttons import UserPanels

# Create router for callbacks
callback_router = Router()


# ==========================================
# 🌐 LANGUAGE CALLBACKS
# ==========================================

@callback_router.callback_query(F.data == "lang:categories")
async def show_language_categories(callback: CallbackQuery):
    """Show language category selector"""
    await callback.message.edit_text(
        "🌐 <b>TILLAR KATEGORIYALARI</b>\n\n"
        "Qaysi kategoriyadan til tanlamoqchisiz?",
        reply_markup=lang_selector.category_selector(),
        parse_mode="HTML"
    )
    await callback.answer()


@callback_router.callback_query(F.data == "lang:all")
async def show_all_languages(callback: CallbackQuery):
    """Show all languages"""
    await callback.message.edit_text(
        "🌐 <b>BARCHA TILLAR</b>\n\n"
        "Kerakli tilni tanlang:",
        reply_markup=lang_selector.language_grid('all', 0),
        parse_mode="HTML"
    )
    await callback.answer()


@callback_router.callback_query(F.data.startswith("langcat:"))
async def handle_language_category(callback: CallbackQuery):
    """Handle language category selection"""
    category = callback.data.split(":")[1]
    
    if category == "all":
        await show_all_languages(callback)
        return
    
    category_names = {
        'popular': '🔥 Mashhur tillar',
        'turkic': '🐺 Turkiy tillar',
        'european': '🏰 Yevropa tillari',
        'asian': '🏯 Osiyo tillari',
        'middle_east': "🕌 O'rta Osiyo va Sharq",
        'slavic': '❄️ Slavyan tillari',
        'african': '🦁 Afrika tillari',
    }
    
    await callback.message.edit_text(
        f"{category_names.get(category, category)}\n\n"
        f"Kerakli tilni tanlang:",
        reply_markup=lang_selector.language_grid(category, 0),
        parse_mode="HTML"
    )
    await callback.answer()


@callback_router.callback_query(F.data.startswith("lang:page:"))
async def handle_language_page(callback: CallbackQuery):
    """Handle language pagination"""
    parts = callback.data.split(":")
    category = parts[2]
    page = int(parts[3])
    
    await callback.message.edit_reply_markup(
        reply_markup=lang_selector.language_grid(category, page)
    )
    await callback.answer()


@callback_router.callback_query(F.data == "lang:back")
async def back_from_language(callback: CallbackQuery):
    """Back from language selection"""
    try:
        await callback.message.delete()
    except:
        pass
    await callback.answer()


# ==========================================
# 📝 TRANSLATION MENU CALLBACKS
# ==========================================

@callback_router.callback_query(F.data == "trans:text")
async def translation_text(callback: CallbackQuery):
    """Handle text translation selection"""
    await callback.message.answer(
        "📝 <b>MATN TARJIMA</b>\n\n"
        "Tarjima qilish uchun matn yuboring.\n"
        "Avval tilni tanlashni unutmang!",
        parse_mode="HTML"
    )
    await callback.answer()


@callback_router.callback_query(F.data == "trans:voice")
async def translation_voice(callback: CallbackQuery):
    """Handle voice translation selection"""
    await callback.message.answer(
        "🎙️ <b>OVOZLI TARJIMA</b>\n\n"
        "Ovozli xabar yuboring.\n"
        "Tez orada qo'shiladi!",
        parse_mode="HTML"
    )
    await callback.answer("Tez orada!", show_alert=True)


@callback_router.callback_query(F.data == "trans:image")
async def translation_image(callback: CallbackQuery):
    """Handle image/OCR translation selection"""
    await callback.message.answer(
        "📷 <b>RASM TARJIMA (OCR)</b>\n\n"
        "Rasm yuboring va matn aniqlansin.\n"
        "Tez orada qo'shiladi!",
        parse_mode="HTML"
    )
    await callback.answer("Tez orada!", show_alert=True)


@callback_router.callback_query(F.data == "trans:doc")
async def translation_doc(callback: CallbackQuery):
    """Handle document translation selection"""
    await callback.message.answer(
        "📎 <b>HUJJAT TARJIMA</b>\n\n"
        "PDF yoki boshqa hujjat yuboring.\n"
        "Tez orada qo'shiladi!",
        parse_mode="HTML"
    )
    await callback.answer("Tez orada!", show_alert=True)


@callback_router.callback_query(F.data == "trans:favorites")
async def translation_favorites(callback: CallbackQuery):
    """Show favorite translations"""
    await callback.message.answer(
        "⭐ <b>SEVIMLI TARJIMALAR</b>\n\n"
        "Bu funksiya tez orada qo'shiladi!",
        parse_mode="HTML"
    )
    await callback.answer("Tez orada!", show_alert=True)


@callback_router.callback_query(F.data == "trans:history")
async def translation_history(callback: CallbackQuery):
    """Show translation history"""
    # Import here to avoid circular imports
    from src.handlers.users.translate import show_translation_history
    await show_translation_history(callback.message)
    await callback.answer()


@callback_router.callback_query(F.data == "trans:settings")
async def translation_settings(callback: CallbackQuery):
    """Show translation settings"""
    await callback.message.answer(
        "⚙️ <b>TARJIMA SOZLAMALARI</b>\n\n"
        "Tez orada qo'shiladi!",
        reply_markup=user_kb.settings_menu(),
        parse_mode="HTML"
    )
    await callback.answer()


# ==========================================
# 📚 VOCABULARY MENU CALLBACKS
# ==========================================
# Note: vocab:* callbacks are handled by original handlers in lughatlar modules
# This section is reserved for additional vocabulary-related callbacks


# ==========================================
# ⚙️ SETTINGS CALLBACKS
# ==========================================

@callback_router.callback_query(F.data == "settings:lang")
async def settings_language(callback: CallbackQuery):
    """Change interface language"""
    await callback.message.answer(
        "🌐 <b>TILNI TANLASH</b>\n\n"
        "Interfeys tilini tanlang:",
        reply_markup=user_kb.settings_menu(),
        parse_mode="HTML"
    )
    await callback.answer("Tez orada!", show_alert=True)


@callback_router.callback_query(F.data == "settings:notifications")
async def settings_notifications(callback: CallbackQuery):
    """Notification settings"""
    await callback.message.answer(
        "🔔 <b>BILDIRISHNOMALAR</b>\n\n"
        "Bu funksiya tez orada qo'shiladi!",
        parse_mode="HTML"
    )
    await callback.answer("Tez orada!", show_alert=True)


@callback_router.callback_query(F.data == "settings:theme")
async def settings_theme(callback: CallbackQuery):
    """Theme settings"""
    await callback.message.answer(
        "🎨 <b>MAVZU SOZLAMALARI</b>\n\n"
        "Bu funksiya tez orada qo'shiladi!",
        parse_mode="HTML"
    )
    await callback.answer("Tez orada!", show_alert=True)


@callback_router.callback_query(F.data == "settings:sound")
async def settings_sound(callback: CallbackQuery):
    """Sound settings"""
    await callback.message.answer(
        "🔊 <b>OVoz SOZLAMALARI</b>\n\n"
        "Bu funksiya tez orada qo'shiladi!",
        parse_mode="HTML"
    )
    await callback.answer("Tez orada!", show_alert=True)


@callback_router.callback_query(F.data == "settings:export")
async def settings_export(callback: CallbackQuery):
    """Export user data"""
    await callback.message.answer(
        "📊 <b>MA'LUMOTLARNI EKSPORT</b>\n\n"
        "Bu funksiya tez orada qo'shiladi!",
        parse_mode="HTML"
    )
    await callback.answer("Tez orada!", show_alert=True)


@callback_router.callback_query(F.data == "settings:delete")
async def settings_delete(callback: CallbackQuery):
    """Delete user data"""
    await callback.message.answer(
        "🗑️ <b>MA'LUMOTLARNI O'CHIRISH</b>\n\n"
        "⚠️ Diqqat! Bu amal qaytarib bo'lmaydi.\n\n"
        "O'chirishni tasdiqlaysizmi?",
        parse_mode="HTML"
    )
    await callback.answer("Diqqat!", show_alert=True)


@callback_router.callback_query(F.data == "settings:help")
async def settings_help(callback: CallbackQuery):
    """Show help"""
    from src.handlers.users.translate import cmd_help
    await cmd_help(callback.message)
    await callback.answer()


@callback_router.callback_query(F.data == "settings:back")
async def settings_back(callback: CallbackQuery):
    """Back from settings"""
    try:
        await callback.message.delete()
    except:
        pass
    await callback.answer()


# ==========================================
# 🏋️ PRACTICE CALLBACKS
# ==========================================

@callback_router.callback_query(F.data == "practice:flashcards")
async def practice_flashcards(callback: CallbackQuery):
    """Start flashcard practice"""
    from src.handlers.users.lughatlar.mashqlar import start_practice
    await start_practice(callback)


@callback_router.callback_query(F.data == "practice:writing")
async def practice_writing(callback: CallbackQuery):
    """Start writing practice"""
    await callback.message.answer(
        "✏️ <b>YOZMA MASHQ</b>\n\n"
        "Bu funksiya tez orada qo'shiladi!",
        parse_mode="HTML"
    )
    await callback.answer("Tez orada!", show_alert=True)


@callback_router.callback_query(F.data == "practice:choice")
async def practice_choice(callback: CallbackQuery):
    """Start multiple choice practice"""
    await callback.message.answer(
        "🔤 <b>TANLASH MASHQI</b>\n\n"
        "Bu funksiya tez orada qo'shiladi!",
        parse_mode="HTML"
    )
    await callback.answer("Tez orada!", show_alert=True)


@callback_router.callback_query(F.data == "practice:listening")
async def practice_listening(callback: CallbackQuery):
    """Start listening practice"""
    await callback.message.answer(
        "👂 <b>TINGLASH MASHQI</b>\n\n"
        "Bu funksiya tez orada qo'shiladi!",
        parse_mode="HTML"
    )
    await callback.answer("Tez orada!", show_alert=True)


@callback_router.callback_query(F.data == "practice:quick")
async def practice_quick(callback: CallbackQuery):
    """Start quick practice"""
    from src.handlers.users.lughatlar.mashqlar import start_practice
    await start_practice(callback)


@callback_router.callback_query(F.data == "practice:game")
async def practice_game(callback: CallbackQuery):
    """Start game mode"""
    await callback.message.answer(
        "🎮 <b>O'YIN REJIMI</b>\n\n"
        "Bu funksiya tez orada qo'shiladi!",
        parse_mode="HTML"
    )
    await callback.answer("Tez orada!", show_alert=True)


@callback_router.callback_query(F.data == "practice:level")
async def practice_level(callback: CallbackQuery):
    """Start level test"""
    await callback.message.answer(
        "📊 <b>DARAJA TESTI</b>\n\n"
        "Bu funksiya tez orada qo'shiladi!",
        parse_mode="HTML"
    )
    await callback.answer("Tez orada!", show_alert=True)


@callback_router.callback_query(F.data == "practice:back")
async def practice_back(callback: CallbackQuery):
    """Back from practice"""
    await callback.message.edit_text(
        "📚 <b>LUG'ATLAR VA MASHQLAR</b>",
        reply_markup=user_kb.vocabulary_menu(),
        parse_mode="HTML"
    )
    await callback.answer()


# ==========================================
# 🏆 ACHIEVEMENT CALLBACKS
# ==========================================

@callback_router.callback_query(F.data == "ach:all")
async def achievements_all(callback: CallbackQuery):
    """Show all achievements using the enhanced user panel"""
    from src.handlers.users.enhanced_user_panel import show_achievements_callback
    await show_achievements_callback(callback)


@callback_router.callback_query(F.data == "ach:back")
async def achievements_back(callback: CallbackQuery):
    """Back from achievements"""
    try:
        await callback.message.delete()
    except:
        pass
    await callback.answer()


# ==========================================
# 🎯 DAILY CHALLENGE CALLBACKS
# ==========================================

@callback_router.callback_query(F.data == "daily:info")
async def daily_info(callback: CallbackQuery):
    """Show daily challenge info"""
    from src.utils.gamification import DailyChallengeManager
    user_id = callback.from_user.id
    
    challenge = DailyChallengeManager.get_user_challenge(user_id)
    if challenge.get('success'):
        text = f"🎯 <b>{challenge['title']}</b>\n\n{challenge['description']}\n\n"
        text += f"🎯 Maqsad: {challenge['target']}\n"
        text += f"📊 Joriy: {challenge['current']}\n"
        text += f"🎁 Mukofot: +{challenge['reward']} XP"
        await callback.answer(text[:200], show_alert=True)
    else:
        await callback.answer("Bugun vazifa yo'q!", show_alert=True)


@callback_router.callback_query(F.data == "daily:progress")
async def daily_progress(callback: CallbackQuery):
    """Show daily challenge progress"""
    from src.utils.gamification import DailyChallengeManager
    user_id = callback.from_user.id
    
    challenge = DailyChallengeManager.get_user_challenge(user_id)
    if challenge.get('success'):
        percent = challenge['progress']
        filled = percent // 10
        bar = '█' * filled + '░' * (10 - filled)
        await callback.answer(
            f"Progress: {bar} {percent}%\n{challenge['current']}/{challenge['target']}",
            show_alert=True
        )
    else:
        await callback.answer("Bugun vazifa yo'q!", show_alert=True)


@callback_router.callback_query(F.data == "daily:claim")
async def daily_claim(callback: CallbackQuery):
    """Claim daily challenge reward - handled automatically"""
    await callback.answer("✅ Mukofot avtomatik berildi!", show_alert=True)


@callback_router.callback_query(F.data == "daily:start")
async def daily_start(callback: CallbackQuery):
    """Start daily challenge - redirect to translation"""
    await callback.message.answer(
        "🚀 <b>BAJARISHNI BOSHLANG!</b>\n\n"
        "Tarjima qilish uchun matn yuboring!",
        parse_mode="HTML"
    )
    await callback.answer("Omad!", show_alert=True)


@callback_router.callback_query(F.data == "daily:back")
async def daily_back(callback: CallbackQuery):
    """Back from daily challenge"""
    try:
        await callback.message.delete()
    except:
        pass
    await callback.answer()


# ==========================================
# 📖 BOOK MANAGEMENT CALLBACKS
# ==========================================

@callback_router.callback_query(F.data == "book:back")
async def book_back(callback: CallbackQuery):
    """Back from book view"""
    await callback.message.edit_text(
        "📚 <b>LUG'ATLAR VA MASHQLAR</b>",
        reply_markup=user_kb.vocabulary_menu(),
        parse_mode="HTML"
    )
    await callback.answer()


# ==========================================
# ❓ NOOP / PLACEHOLDER CALLBACKS
# ==========================================

@callback_router.callback_query(F.data == "noop")
async def noop_callback(callback: CallbackQuery):
    """Handle noop callbacks (page info, etc.)"""
    await callback.answer()


@callback_router.callback_query(F.data == "lang:current")
async def lang_current(callback: CallbackQuery):
    """Current language info"""
    await callback.answer("Joriy til sozlamalari", show_alert=True)


@callback_router.callback_query(F.data.startswith("lang:header:"))
async def lang_header(callback: CallbackQuery):
    """Language header info"""
    await callback.answer("Tilni tanlang", show_alert=True)
