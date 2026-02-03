"""
🎹 Sophisticated Keyboard System for Tarjimon Bot
Enhanced UI with beautiful layouts, animations, and interactive elements
"""

from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
    WebAppInfo
)
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from typing import List, Optional, Dict, Any
from config import LANGUAGES


# 🎨 Color themes and visual styles
THEMES = {
    'default': {'primary': '🔵', 'secondary': '⚪', 'accent': '🟡'},
    'ocean': {'primary': '🌊', 'secondary': '💧', 'accent': '✨'},
    'forest': {'primary': '🌲', 'secondary': '🍃', 'accent': '🌟'},
    'sunset': {'primary': '🌅', 'secondary': '🟠', 'accent': '💫'},
    'cosmic': {'primary': '🌌', 'secondary': '⭐', 'accent': '🚀'},
    'royal': {'primary': '👑', 'secondary': '💎', 'accent': '🏆'},
}


class FancyButtons:
    """✨ Beautiful button presets with emojis and styling"""
    
    # Navigation
    BACK = "🔙 Ortga"
    BACK_ARROW = "⬅️ Orqaga"
    MAIN_MENU = "🏠 Bosh menu"
    CLOSE = "❌ Yopish"
    CANCEL = "🚫 Bekor qilish"
    NEXT = "➡️ Keyingi"
    PREV = "⬅️ Oldingi"
    CONTINUE = "▶️ Davom etish"
    CONFIRM = "✅ Tasdiqlash"
    REFRESH = "🔄 Yangilash"
    
    # Main Menu (must match original system exactly)
    TRANSLATE = "📝 Tarjima qilish"
    LANGUAGES = "🌐 Tilni tanlash"  # Note: Original uses "Tilni" not "Tillarni"
    VOCABULARY = "📚 Lug'atlar va Mashqlar"
    TIMETABLE = "📅 Dars jadvali"
    HELP = "ℹ️ Yordam"
    PROFILE = "👤 Profil"
    SETTINGS = "⚙️ Sozlamalar"
    STATISTICS = "📊 Statistika"
    ACHIEVEMENTS = "🏆 Yutuqlar"
    LEADERBOARD = "🥇 Reyting"
    
    # Translation
    VOICE_TRANSLATE = "🎙️ Ovozli tarjima"
    IMAGE_TRANSLATE = "📷 Rasm tarjima"
    HISTORY = "📜 Tarjima tarixi"
    FAVORITES = "⭐ Sevimlilar"
    QUICK_SWITCH = "🔄 Tez almashtirish"
    DETECT_LANG = "🔍 Tilni aniqlash"
    
    # Vocabulary
    MY_BOOKS = "📖 Mening lug'atlarim"
    PUBLIC_BOOKS = "🌐 Ommaviy lug'atlar"
    ESSENTIALS = "📚 Essentiallar"
    PARALLEL = "🌍 Parallel tarjimalar"
    PRACTICE = "🏋️ Mashq qilish"
    ADD_WORDS = "➕ So'z qo'shish"
    NEW_BOOK = "📗 Yangi lug'at"
    IMPORT = "📥 Import"
    EXPORT = "📤 Export"
    
    # Gamification
    DAILY_CHALLENGE = "🎯 Kunlik vazifa"
    STREAK = "🔥 Izchillik"
    XP_SHOP = "🛒 Do'kon"
    INVITE = "👥 Do'stlarni taklif"


class VisualLanguageSelector:
    """🌐 Beautiful language selection interface"""
    
    # Language categories with emojis
    CATEGORIES = {
        'popular': {'emoji': '🔥', 'name': 'Mashhur tillar', 'langs': ['en', 'ru', 'uz', 'tr', 'ar']},
        'turkic': {'emoji': '🐺', 'name': 'Turkiy tillar', 'langs': ['uz', 'tr', 'kk', 'ky', 'az', 'tk', 'ug']},
        'european': {'emoji': '🏰', 'name': 'Yevropa tillari', 'langs': ['en', 'de', 'fr', 'es', 'it', 'pt', 'pl', 'nl']},
        'asian': {'emoji': '🏯', 'name': 'Osiyo tillari', 'langs': ['zh', 'ja', 'ko', 'hi', 'id', 'th', 'vi', 'ms']},
        'middle_east': {'emoji': '🕌', 'name': "O'rta Osiyo va Sharq", 'langs': ['ar', 'fa', 'he', 'ur', 'ps', 'ku']},
        'slavic': {'emoji': '❄️', 'name': 'Slavyan tillari', 'langs': ['ru', 'uk', 'pl', 'cs', 'bg', 'sr', 'hr']},
        'african': {'emoji': '🦁', 'name': 'Afrika tillari', 'langs': ['am', 'sw', 'ha', 'yo', 'zu', 'af', 'so']},
    }
    
    LANGUAGE_EMOJIS = {
        'en': '🇬🇧', 'uz': '🇺🇿', 'ru': '🇷🇺', 'tr': '🇹🇷', 'ar': '🇸🇦',
        'de': '🇩🇪', 'fr': '🇫🇷', 'es': '🇪🇸', 'it': '🇮🇹', 'pt': '🇵🇹',
        'zh': '🇨🇳', 'ja': '🇯🇵', 'ko': '🇰🇷', 'hi': '🇮🇳', 'id': '🇮🇩',
        'fa': '🇮🇷', 'kk': '🇰🇿', 'ky': '🇰🇬', 'az': '🇦🇿', 'tk': '🇹🇲',
        'tg': '🇹🇯', 'pl': '🇵🇱', 'am': '🇪🇹', 'nl': '🇳🇱', 'auto': '🌐',
        'uk': '🇺🇦', 'cs': '🇨🇿', 'bg': '🇧🇬', 'ro': '🇷🇴', 'el': '🇬🇷',
        'th': '🇹🇭', 'vi': '🇻🇳', 'ms': '🇲🇾', 'he': '🇮🇱', 'ur': '🇵🇰',
        'sw': '🇹🇿', 'ha': '🇳🇬', 'yo': '🇳🇬', 'zu': '🇿🇦', 'af': '🇿🇦',
        'so': '🇸🇴', 'sv': '🇸🇪', 'no': '🇳🇴', 'da': '🇩🇰', 'fi': '🇫🇮',
        'hu': '🇭🇺', 'sk': '🇸🇰', 'hr': '🇭🇷', 'sr': '🇷🇸', 'sl': '🇸🇮',
        'lt': '🇱🇹', 'lv': '🇱🇻', 'et': '🇪🇪', 'be': '🇧🇾', 'mk': '🇲🇰',
        'ka': '🇬🇪', 'hy': '🇦🇲', 'ta': '🇮🇳', 'te': '🇮🇳', 'mr': '🇮🇳',
        'bn': '🇧🇩', 'gu': '🇮🇳', 'kn': '🇮🇳', 'ml': '🇮🇳', 'pa': '🇮🇳',
        'ne': '🇳🇵', 'si': '🇱🇰', 'my': '🇲🇲', 'km': '🇰🇭', 'lo': '🇱🇦',
    }
    
    @classmethod
    def get_language_emoji(cls, lang_code: str) -> str:
        """Get emoji for language code"""
        return cls.LANGUAGE_EMOJIS.get(lang_code, '🏳️')
    
    @classmethod
    def category_selector(cls) -> InlineKeyboardMarkup:
        """Create category selection keyboard"""
        builder = InlineKeyboardBuilder()
        
        for code, data in cls.CATEGORIES.items():
            builder.button(
                text=f"{data['emoji']} {data['name']}",
                callback_data=f"langcat:{code}"
            )
        
        builder.button(text="🔍 Barcha tillar", callback_data="langcat:all")
        builder.button(text=FancyButtons.BACK, callback_data="lang:back")
        
        builder.adjust(2, 2, 2, 2)
        return builder.as_markup()
    
    @classmethod
    def language_grid(cls, category: str = 'all', page: int = 0) -> InlineKeyboardMarkup:
        """Create paginated language grid"""
        builder = InlineKeyboardBuilder()
        
        if category == 'all':
            languages = list(LANGUAGES.items())
        else:
            lang_codes = cls.CATEGORIES.get(category, {}).get('langs', [])
            languages = [(code, LANGUAGES[code]) for code in lang_codes if code in LANGUAGES]
        
        # Add auto detect at the top
        builder.button(text="🌐 Avto-aniqlash", callback_data="lang:auto")
        
        items_per_page = 16
        start = page * items_per_page
        end = start + items_per_page
        page_langs = languages[start:end]
        
        for code, data in page_langs:
            if code == 'auto':
                continue
            emoji = cls.get_language_emoji(code)
            builder.button(
                text=f"{emoji} {data['name']}",
                callback_data=f"lang:select:{code}"
            )
        
        # Navigation
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton(
                text=FancyButtons.PREV,
                callback_data=f"lang:page:{category}:{page-1}"
            ))
        if end < len(languages):
            nav_buttons.append(InlineKeyboardButton(
                text=FancyButtons.NEXT,
                callback_data=f"lang:page:{category}:{page+1}"
            ))
        
        if nav_buttons:
            builder.row(*nav_buttons)
        
        builder.button(text=FancyButtons.BACK_ARROW, callback_data="lang:categories")
        
        builder.adjust(1, 4, 4, 4, 4)
        return builder.as_markup()
    
    @classmethod
    def dual_language_selector(cls, user_id: int, current_from: str = 'auto', current_to: str = 'uz') -> InlineKeyboardMarkup:
        """Beautiful dual language selector (source → target)"""
        builder = InlineKeyboardBuilder()
        
        # Header with current selection
        from_emoji = cls.get_language_emoji(current_from) if current_from != 'auto' else '🌐'
        to_emoji = cls.get_language_emoji(current_to)
        from_name = LANGUAGES.get(current_from, {}).get('name', 'Avto') if current_from != 'auto' else 'Avto-aniqlash'
        to_name = LANGUAGES.get(current_to, {}).get('name', 'Tanlanmagan')
        
        builder.button(
            text=f"🎯 {from_emoji} {from_name} → {to_emoji} {to_name}",
            callback_data="lang:current"
        )
        
        # Quick switch button
        builder.button(text="🔄 Almashtirish", callback_data="lang:switch")
        
        # Source languages section
        builder.button(text="📥 Manba tili:", callback_data="lang:header:from")
        popular_from = ['auto', 'en', 'ru', 'uz', 'tr']
        for code in popular_from:
            if code == 'auto':
                prefix = '✅' if current_from == 'auto' else '  '
                builder.button(text=f"{prefix} 🌐 Avto", callback_data="lang:set:from:auto")
            else:
                prefix = '✅' if current_from == code else '  '
                emoji = cls.get_language_emoji(code)
                name = LANGUAGES[code]['name']
                builder.button(text=f"{prefix} {emoji} {name}", callback_data=f"lang:set:from:{code}")
        
        # Target languages section
        builder.button(text="📤 Maqsad tili:", callback_data="lang:header:to")
        popular_to = ['uz', 'en', 'ru', 'tr', 'ar']
        for code in popular_to:
            prefix = '✅' if current_to == code else '  '
            emoji = cls.get_language_emoji(code)
            name = LANGUAGES[code]['name']
            builder.button(text=f"{prefix} {emoji} {name}", callback_data=f"lang:set:to:{code}")
        
        # More options
        builder.button(text="🔍 Barcha tillar...", callback_data="lang:all")
        builder.button(text=FancyButtons.CONFIRM, callback_data="lang:done")
        
        builder.adjust(1, 1, 1, 5, 1, 5, 2)
        return builder.as_markup()


class UserPanelKeyboards:
    """👤 Sophisticated User Panel Keyboards"""
    
    @staticmethod
    async def main_menu(theme: str = 'default') -> ReplyKeyboardMarkup:
        """Beautiful main menu with organized layout"""
        builder = ReplyKeyboardBuilder()
        
        # First row - Core features (match original system)
        builder.row(
            KeyboardButton(text=FancyButtons.LANGUAGES),
            KeyboardButton(text=FancyButtons.TRANSLATE)
        )
        
        # Second row - Schedule and Help
        builder.row(
            KeyboardButton(text=FancyButtons.TIMETABLE),
            KeyboardButton(text=FancyButtons.HELP)
        )
        
        # Third row - Vocabulary (single button like original)
        builder.row(
            KeyboardButton(text=FancyButtons.VOCABULARY)
        )
        
        return builder.as_markup(resize_keyboard=True)
    
    @staticmethod
    def translation_menu() -> InlineKeyboardMarkup:
        """Enhanced translation options"""
        builder = InlineKeyboardBuilder()
        
        builder.button(text="📝 Matn tarjima", callback_data="trans:text")
        builder.button(text="🎙️ Ovozli", callback_data="trans:voice")
        builder.button(text="📷 Rasm/OCR", callback_data="trans:image")
        builder.button(text="📎 Hujjat", callback_data="trans:doc")
        builder.button(text="⭐ Sevimlilar", callback_data="trans:favorites")
        builder.button(text="📜 Tarix", callback_data="trans:history")
        builder.button(text="🔄 Sozlamalar", callback_data="trans:settings")
        
        builder.adjust(2, 2, 2, 1)
        return builder.as_markup()
    
    @staticmethod
    def vocabulary_menu() -> InlineKeyboardMarkup:
        """Rich vocabulary menu - uses existing callback patterns"""
        builder = InlineKeyboardBuilder()
        
        # Using existing callback patterns from original handlers
        builder.button(text="📖 Mening lug'atlarim", callback_data="lughat:list:0")
        builder.button(text="🌐 Ommaviy", callback_data="ommaviy:list:0")
        builder.button(text="📚 Essentiallar", callback_data="essential:main")
        builder.button(text="🌍 Parallel", callback_data="parallel:main")
        builder.button(text="🏋️ Mashqlar", callback_data="mashq:list")
        builder.button(text="📊 Statistika", callback_data="cab:stats")
        builder.button(text="➕ Yangi lug'at", callback_data="lughat:new")
        builder.button(text=FancyButtons.BACK, callback_data="cab:back")
        
        builder.adjust(2, 2, 2, 2)
        return builder.as_markup()
    
    @staticmethod
    def profile_menu(user_data: Dict[str, Any]) -> InlineKeyboardMarkup:
        """Beautiful profile menu with user stats"""
        builder = InlineKeyboardBuilder()
        
        level = user_data.get('level', 1)
        xp = user_data.get('xp', 0)
        streak = user_data.get('streak', 0)
        
        # Stats display
        builder.button(
            text=f"⭐ Level {level} | 🔥 {streak} kun | 💎 {xp} XP",
            callback_data="profile:stats"
        )
        
        builder.button(text="📊 Batafsil statistika", callback_data="profile:detailed")
        builder.button(text="🏆 Yutuqlarim", callback_data="profile:achievements")
        builder.button(text="🥇 Reyting", callback_data="profile:leaderboard")
        builder.button(text="📅 Kunlik vazifa", callback_data="profile:daily")
        builder.button(text="⚙️ Sozlamalar", callback_data="profile:settings")
        builder.button(text=FancyButtons.BACK, callback_data="profile:back")
        
        builder.adjust(1, 2, 2, 2)
        return builder.as_markup()
    
    @staticmethod
    def settings_menu() -> InlineKeyboardMarkup:
        """Comprehensive settings menu"""
        builder = InlineKeyboardBuilder()
        
        builder.button(text="🌐 Til / Language", callback_data="settings:lang")
        builder.button(text="🔔 Bildirishnomalar", callback_data="settings:notifications")
        builder.button(text="🎨 Mavzu", callback_data="settings:theme")
        builder.button(text="🔊 Ovoz", callback_data="settings:sound")
        builder.button(text="📊 Ma'lumotlarni eksport", callback_data="settings:export")
        builder.button(text="🗑️ Ma'lumotlarni o'chirish", callback_data="settings:delete")
        builder.button(text="❓ Yordam", callback_data="settings:help")
        builder.button(text=FancyButtons.BACK, callback_data="settings:back")
        
        builder.adjust(2, 2, 2, 2)
        return builder.as_markup()
    
    @staticmethod
    def book_card(book_data: Dict[str, Any], is_owner: bool = True) -> InlineKeyboardMarkup:
        """Beautiful book display card"""
        builder = InlineKeyboardBuilder()
        
        word_count = book_data.get('word_count', 0)
        is_public = book_data.get('is_public', False)
        
        # Action buttons
        actions = []
        if word_count >= 4:
            actions.append(InlineKeyboardButton(text="🏋️ Mashq", callback_data=f"book:practice:{book_data['id']}"))
        actions.append(InlineKeyboardButton(text="👁️ Ko'rish", callback_data=f"book:view:{book_data['id']}"))
        
        if actions:
            builder.row(*actions)
        
        # Management buttons
        if is_owner:
            builder.button(text="➕ So'z qo'shish", callback_data=f"book:add:{book_data['id']}")
            builder.button(text="✏️ Tahrirlash", callback_data=f"book:edit:{book_data['id']}")
            builder.button(text="📤 Eksport", callback_data=f"book:export:{book_data['id']}")
            
            visibility = "🔒 Yashirish" if is_public else "🌐 Ommaviylashtirish"
            builder.button(text=visibility, callback_data=f"book:toggle:{book_data['id']}")
            builder.button(text="❌ O'chirish", callback_data=f"book:delete:{book_data['id']}")
        else:
            builder.button(text="💾 Saqlash", callback_data=f"book:save:{book_data['id']}")
            builder.button(text="👤 Muallif", callback_data=f"book:author:{book_data['id']}")
        
        builder.button(text=FancyButtons.BACK, callback_data="book:back")
        builder.adjust(2, 2, 2, 1)
        
        return builder.as_markup()


class AdminPanelKeyboards:
    """👨‍💼 Advanced Admin Panel Keyboards"""
    
    @staticmethod
    def main_admin_menu() -> ReplyKeyboardMarkup:
        """Comprehensive admin menu"""
        builder = ReplyKeyboardBuilder()
        
        builder.row(
            KeyboardButton(text="📊 Statistika"),
            KeyboardButton(text="👥 Foydalanuvchilar")
        )
        builder.row(
            KeyboardButton(text="📢 Xabar yuborish"),
            KeyboardButton(text="🔧 Kanallar")
        )
        builder.row(
            KeyboardButton(text="📚 Kontent"),
            KeyboardButton(text="⚙️ Tizim")
        )
        builder.row(
            KeyboardButton(text="🎮 Gamification"),
            KeyboardButton(text="🔙 Chiqish")
        )
        
        return builder.as_markup(resize_keyboard=True)
    
    @staticmethod
    def statistics_menu() -> InlineKeyboardMarkup:
        """Rich statistics navigation"""
        builder = InlineKeyboardBuilder()
        
        builder.button(text="📊 Umumiy statistika", callback_data="stats:overview")
        builder.button(text="📈 O'sish dinamikasi", callback_data="stats:growth")
        builder.button(text="🌍 Tillar bo'yicha", callback_data="stats:languages")
        builder.button(text="⏰ Faollik", callback_data="stats:activity")
        builder.button(text="👥 Foydalanuvchilar", callback_data="stats:users")
        builder.button(text="🔄 Tarjimalar", callback_data="stats:translations")
        builder.button(text="📚 Lug'atlar", callback_data="stats:vocab")
        builder.button(text="🎮 Gamification", callback_data="stats:game")
        builder.button(text="📥 Hisobot yuklash", callback_data="stats:export")
        builder.button(text=FancyButtons.BACK, callback_data="stats:back")
        
        builder.adjust(2, 2, 2, 2, 2)
        return builder.as_markup()
    
    @staticmethod
    def user_management_menu() -> InlineKeyboardMarkup:
        """User management options"""
        builder = InlineKeyboardBuilder()
        
        builder.button(text="🔍 Qidirish", callback_data="users:search")
        builder.button(text="📋 Ro'yxat", callback_data="users:list")
        builder.button(text="🚫 Bloklanganlar", callback_data="users:blocked")
        builder.button(text="⭐ Premium", callback_data="users:premium")
        builder.button(text="🔥 Faol foydalanuvchilar", callback_data="users:active")
        builder.button(text="⚠️ Shubhali", callback_data="users:suspicious")
        builder.button(text=FancyButtons.BACK, callback_data="users:back")
        
        builder.adjust(2, 2, 2, 1)
        return builder.as_markup()
    
    @staticmethod
    def broadcast_menu() -> InlineKeyboardMarkup:
        """Broadcast message options"""
        builder = InlineKeyboardBuilder()
        
        builder.button(text="📨 Forward xabar", callback_data="broadcast:forward")
        builder.button(text="📬 Oddiy xabar", callback_data="broadcast:copy")
        builder.button(text="🎯 Maqsadli yuborish", callback_data="broadcast:targeted")
        builder.button(text="📅 Rejalashtirish", callback_data="broadcast:schedule")
        builder.button(text="📊 Yuborishlar tarixi", callback_data="broadcast:history")
        builder.button(text=FancyButtons.BACK, callback_data="broadcast:back")
        
        builder.adjust(2, 2, 2)
        return builder.as_markup()
    
    @staticmethod
    def gamification_admin() -> InlineKeyboardMarkup:
        """Gamification management"""
        builder = InlineKeyboardBuilder()
        
        builder.button(text="🏆 Yutuqlar", callback_data="game:achievements")
        builder.button(text="🎯 Kunlik vazifalar", callback_data="game:daily")
        builder.button(text="🥇 Reyting sozlamalari", callback_data="game:leaderboard")
        builder.button(text="🎁 Sovg'alar", callback_data="game:rewards")
        builder.button(text="📊 Gamification statistikasi", callback_data="game:stats")
        builder.button(text=FancyButtons.BACK, callback_data="game:back")
        
        builder.adjust(2, 2, 2)
        return builder.as_markup()


class PracticeKeyboards:
    """🏋️ Interactive Practice Keyboards"""
    
    @staticmethod
    def practice_modes() -> InlineKeyboardMarkup:
        """Select practice mode"""
        builder = InlineKeyboardBuilder()
        
        builder.button(text="🎯 Flashcards", callback_data="practice:flashcards")
        builder.button(text="✏️ Yozma mashq", callback_data="practice:writing")
        builder.button(text="🔤 Tanlash", callback_data="practice:choice")
        builder.button(text="👂 Tinglash", callback_data="practice:listening")
        builder.button(text="⚡ Tez mashq", callback_data="practice:quick")
        builder.button(text="🎮 O'yin rejimi", callback_data="practice:game")
        builder.button(text="📊 Daraja testi", callback_data="practice:level")
        builder.button(text=FancyButtons.BACK, callback_data="practice:back")
        
        builder.adjust(2, 2, 2, 2)
        return builder.as_markup()
    
    @staticmethod
    def flashcard_card(word: str, translation: str, show_answer: bool = False) -> InlineKeyboardMarkup:
        """Interactive flashcard"""
        builder = InlineKeyboardBuilder()
        
        if not show_answer:
            builder.button(text="👁️ Javobni ko'rish", callback_data="flash:show")
        else:
            builder.button(text="❌ Bilmayman", callback_data="flash:hard")
            builder.button(text="🤔 Bir oz", callback_data="flash:medium")
            builder.button(text="✅ Bilaman", callback_data="flash:easy")
        
        builder.button(text="🔊 Talaffuz", callback_data="flash:audio")
        builder.button(text="⭐ Saqlash", callback_data="flash:save")
        builder.button(text="⏸️ Toxtatish", callback_data="flash:stop")
        
        builder.adjust(3 if show_answer else 1, 3)
        return builder.as_markup()
    
    @staticmethod
    def quiz_question(question: str, options: List[str], correct_idx: int) -> InlineKeyboardMarkup:
        """Multiple choice quiz"""
        builder = InlineKeyboardBuilder()
        
        emojis = ['🅰️', '🅱️', '🅲️', '🅳️']
        for i, option in enumerate(options[:4]):
            builder.button(
                text=f"{emojis[i]} {option[:30]}",
                callback_data=f"quiz:answer:{i}:{correct_idx}"
            )
        
        builder.button(text="⏭️ O'tkazish", callback_data="quiz:skip")
        builder.button(text="🛑 Tugatish", callback_data="quiz:stop")
        
        builder.adjust(1, 1, 1, 1, 2)
        return builder.as_markup()


class GamificationKeyboards:
    """🎮 Gamification Interface"""
    
    @staticmethod
    def achievements_list(achievements: List[Dict], page: int = 0) -> InlineKeyboardMarkup:
        """Display achievements list"""
        builder = InlineKeyboardBuilder()
        
        items_per_page = 5
        start = page * items_per_page
        end = start + items_per_page
        page_ach = achievements[start:end]
        
        for ach in page_ach:
            status = "✅" if ach.get('unlocked') else "🔒"
            builder.button(
                text=f"{status} {ach.get('icon', '🏆')} {ach.get('name', 'Unknown')}",
                callback_data=f"ach:view:{ach.get('id')}"
            )
        
        # Navigation
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton(
                text=FancyButtons.PREV,
                callback_data=f"ach:page:{page-1}"
            ))
        if end < len(achievements):
            nav_buttons.append(InlineKeyboardButton(
                text=FancyButtons.NEXT,
                callback_data=f"ach:page:{page+1}"
            ))
        
        if nav_buttons:
            builder.row(*nav_buttons)
        
        builder.button(text=FancyButtons.BACK, callback_data="ach:back")
        return builder.as_markup()
    
    @staticmethod
    def daily_challenge(challenge: Dict[str, Any]) -> InlineKeyboardMarkup:
        """Daily challenge display"""
        builder = InlineKeyboardBuilder()
        
        builder.button(
            text=f"🎯 {challenge.get('title', 'Kunlik vazifa')}",
            callback_data="daily:info"
        )
        
        progress = challenge.get('current', 0)
        target = challenge.get('target', 1)
        percent = min(100, int(progress / target * 100))
        
        # Progress bar
        filled = percent // 10
        bar = '█' * filled + '░' * (10 - filled)
        builder.button(
            text=f"{bar} {percent}%",
            callback_data="daily:progress"
        )
        
        if challenge.get('completed'):
            builder.button(text="✅ Bajardim!", callback_data="daily:claim")
        else:
            builder.button(text="🚀 Boshlash", callback_data="daily:start")
        
        builder.button(text=FancyButtons.BACK, callback_data="daily:back")
        builder.adjust(1, 1, 1, 1)
        return builder.as_markup()
    
    @staticmethod
    def leaderboard_entry(rank: int, user_data: Dict, is_current_user: bool = False) -> str:
        """Format leaderboard entry with medals"""
        medals = {1: '🥇', 2: '🥈', 3: '🥉'}
        rank_display = medals.get(rank, f"{rank}.")
        
        name = user_data.get('name', 'Anonymous')
        if is_current_user:
            name = f"👉 {name} (Siz)"
        
        xp = user_data.get('xp', 0)
        level = user_data.get('level', 1)
        
        return f"{rank_display} {name} | L{level} | {xp} XP"


# Quick access instances
user_kb = UserPanelKeyboards()
admin_kb = AdminPanelKeyboards()
lang_selector = VisualLanguageSelector()
practice_kb = PracticeKeyboards()
game_kb = GamificationKeyboards()
