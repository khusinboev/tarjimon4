import os

from aiogram import Bot
from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, User, FSInputFile, Message

from config import sql, db, bot, ADMIN_ID


class CheckData:
    @staticmethod
    async def check_member(bot: Bot, user_id: int):
        """
        Foydalanuvchi barcha majburiy kanallarga a'zo bo'lganini tekshirish
        """
        try:
            sql.execute("SELECT chat_id FROM public.mandatorys")
            mandatory = sql.fetchall()
            if not mandatory:
                return True, []

            channels = []
            for chat_id in mandatory:
                try:
                    r = await bot.get_chat_member(chat_id=chat_id[0], user_id=user_id)
                    if r.status == "left" and user_id not in ADMIN_ID:
                        channels.append(chat_id[0])
                except Exception as e:
                    # Kanal topilmadi yoki boshqa xato
                    print(f"[WARNING] Channel check error for {user_id}: {e}")
            
            return (len(channels) == 0), channels
        except Exception as e:
            print(f"[ERROR] check_member error: {e}")
            return True, []  # Xatolik bo'lsa ruxsat berish

    @staticmethod
    async def channels_btn(channels: list):
        keyboard = []
        for index, channel_id in enumerate(channels, 1):
            sql.execute("SELECT username FROM public.mandatorys WHERE chat_id=%s", (channel_id,))
            link = sql.fetchone()
            if link:
                keyboard.append([
                    InlineKeyboardButton(
                        text=f"📢 Kanal-{index}",
                        url=link[0]
                    )
                ])
        keyboard.append([InlineKeyboardButton(text="✅Qo'shildim", callback_data="check")])
        return InlineKeyboardMarkup(inline_keyboard=keyboard)


class PanelFunc:
    @staticmethod
    async def channel_add(chat_id, link):
        sql.execute("INSERT INTO public.mandatorys(chat_id, username) VALUES(%s, %s)", (chat_id, link))
        db.commit()

    @staticmethod
    async def channel_delete(id):
        sql.execute("DELETE FROM public.mandatorys WHERE chat_id=%s", (id,))
        db.commit()

    @staticmethod
    async def channel_list():
        sql.execute("SELECT chat_id, username from public.mandatorys")
        result = ''
        for row in sql.fetchall():
            chat_id = row[0]
            username_or_link = row[1] or f"ID: {chat_id}"
            try:
                all_details = await bot.get_chat(chat_id=chat_id)
                title = all_details.title
                channel_id = all_details.id
                info = all_details.description
                result += f"------------------------------------------------\nKanal useri: > @{all_details.username}\nKamal nomi: > {title}\nKanal id si: > {channel_id}\nKanal haqida: > {info}\n"
            except Exception as e:
                # Include username or link in the error for easier deletion
                result += (
                    f"Kanalni admin qiling yoki o'chiring:\n"
                    f"User/Link: {username_or_link}\n"
                    f"ID: {chat_id}\n"
                    f"Error: {e}\n"
                    f"O'chirish uchun: ❌Kanalni olib tashlash tugmasidan foydalaning."
                )
        return result

    @staticmethod
    async def admin_add(chat_id):
        sql.execute("INSERT INTO public.admins(user_id) VALUES(%s)", (chat_id,))
        db.commit()

    @staticmethod
    async def admin_delete(id):
        sql.execute("DELETE FROM public.admins WHERE user_id=%s", (id,))
        db.commit()

    @staticmethod
    async def admin_list():
        sql.execute("SELECT user_id from public.admins")
        str = ""
        for row in sql.fetchall():
            chat_id = row[0]
            try:
                user: User = await bot.get_chat(chat_id)
                username = f"@{user.username}" if user.username else "❌ Topilmadi"
                full_name = user.full_name
                str += f"👤 Foydalanuvchi:\n🔹 Ism: {full_name}\n🔹 Username: {username}\n🔹 ID: <code>{user.id}</code>\n\n"
            except Exception as e:
                str += f"xatolik:\n" + f"🔹 ID: <code>{chat_id}</code>\n\n"
        return str
