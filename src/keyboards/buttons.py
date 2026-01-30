from aiogram.types import ReplyKeyboardMarkup, InlineKeyboardButton, KeyboardButton, InlineKeyboardMarkup

from config import sql, bot


class AdminPanel:
    @staticmethod
    async def admin_menu():
        btn=ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="📊 Statistika"), KeyboardButton(text="👥 Foydalanuvchilar")],
                [KeyboardButton(text="📢 Xabar yuborish"), KeyboardButton(text="🔧 Kanallar")],
                [KeyboardButton(text="🎮 Gamification"), KeyboardButton(text="🔙 Chiqish")],
            ],
            resize_keyboard=True,
        )
        return btn

    @staticmethod
    async def admin_channel():
        admin_channel=ReplyKeyboardMarkup(
                    keyboard=[
                        [
                            KeyboardButton(text="➕Kanal qo'shish"),
                            KeyboardButton(text="❌Kanalni olib tashlash"),
                        ],
                        [
                            KeyboardButton(text="📋 Kanallar ro'yxati"),
                            KeyboardButton(text="🔙Orqaga qaytish"),
                        ]
                    ],
                    resize_keyboard=True,
                )
        return admin_channel

    @staticmethod
    async def admin_add():
        admin_channel=ReplyKeyboardMarkup(
                    keyboard=[
                        [
                            KeyboardButton(text="➕Admin qo'shish"),
                            KeyboardButton(text="❌Admin o'chirish"),
                        ],
                        [
                            KeyboardButton(text="📋 Adminlar ro'yxati"),
                            KeyboardButton(text="🔙Orqaga qaytish"),
                        ]
                    ],
                    resize_keyboard=True,
                )
        return admin_channel

    @staticmethod
    async def admin_msg():
        admin_channel = ReplyKeyboardMarkup(
            keyboard=[
                [
                    KeyboardButton(text="📨Forward xabar yuborish"),
                    KeyboardButton(text="📬Oddiy xabar yuborish"),
                ],
                [
                    KeyboardButton(text="🧪Sinov: Copy yuborish"),
                    KeyboardButton(text="🧪Sinov: Forward yuborish")
                ],
                [
                    KeyboardButton(text="🔙Orqaga qaytish"),
                ]
            ],
            resize_keyboard=True,
        )
        return admin_channel


class UserPanels:
    @staticmethod
    async def join_btn(user_id):
        sql.execute("SELECT chat_id FROM public.mandatorys")
        rows = sql.fetchall()
        join_inline = []
        title = 1
        for row in rows:
            all_details = await bot.get_chat(chat_id=row[0])
            url = all_details.invite_link
            if not url:
                url = await bot.export_chat_invite_link(row[0])
            join_inline.append([InlineKeyboardButton(text=f"{title} - kanal", url=url)])
            title += 1
        join_inline.append([InlineKeyboardButton(text="✅Obuna bo'ldim", callback_data="check")])
        button = InlineKeyboardMarkup(inline_keyboard=join_inline)
        return button

    @staticmethod
    async def user_main_menu():
        btn = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="🌐 Tilni tanlash"), KeyboardButton(text="📝 Tarjima qilish")],
                [KeyboardButton(text="📅 Dars jadvali"), KeyboardButton(text="ℹ️ Yordam")],
                [KeyboardButton(text="📚 Lug'atlar va Mashqlar")],
            ],
            resize_keyboard=True,
        )
        return btn


    @staticmethod
    async def to_back():
        btn = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="🔙 Ortga"), KeyboardButton(text="🔙 Bosh menu")]], resize_keyboard=True,
        )
        return btn
