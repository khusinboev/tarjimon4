from aiogram import Router, F
from aiogram.enums import ChatType
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from config import bot, ADMIN_ID
from src.keyboards.buttons import UserPanels
from src.keyboards.keyboard_func import CheckData
from src.utils.messages import MSG

user_router = Router()

# Main menu button handlers
@user_router.message(F.text == "🌐 Tilni tanlash")
async def menu_lang(msg: Message):
    try:
        from src.handlers.users.translate import get_language_keyboard
        await msg.answer(
            MSG["lang_title"],
            reply_markup=get_language_keyboard(msg.from_user.id),
            parse_mode="HTML"
        )
    except Exception as e:
        await msg.answer(MSG["langs_loading_error"])
        print(f"[ERROR] menu_lang: {e}")


@user_router.message(F.text == "ℹ️ Yordam")
async def menu_help(msg: Message):
    try:
        from src.handlers.users.translate import cmd_help
        await cmd_help(msg)
    except Exception as e:
        await msg.answer(
            "❌ Yordam ma'lumotlarini yuklashda xatolik yuz berdi.\n"
            "❌ Error loading help information."
        )
        print(f"[ERROR] menu_help: {e}")


@user_router.message(F.text == "📚 Lug'atlar va Mashqlar")
async def menu_cabinet(msg: Message):
    try:
        from src.handlers.users.lughatlar.vocabs import get_user_data, get_locale, cabinet_kb
        data = await get_user_data(msg.from_user.id)
        L = get_locale(data["lang"])
        await msg.answer(L["cabinet"], reply_markup=cabinet_kb(data["lang"]))
    except Exception as e:
        await msg.answer(
            "📚 <b>Lug'atlar va Mashqlar</b>\n\n"
            "🎯 Mashqlar - So'zlarni mashq qilish\n"
            "📖 Lug'atlarim - Shaxsiy lug'atlaringiz\n"
            "📚 Ommaviy lug'atlar - Boshqalar bilan ulashilgan\n"
            "📚 Essentiallar - Asosiy lug'atlar\n"
            "�� Parallel - Parallel tarjimalar\n\n"
            "Kabinetni ochish uchun /cabinet buyrug'idan foydalaning.",
            parse_mode="HTML"
        )
        print(f"[ERROR] menu_cabinet: {e}")


# Blocked user handler
@user_router.message(F.from_user.id == 7638932125)
async def blocked_user_handler(message: Message):
    await message.answer(MSG["blocked"], parse_mode="HTML")


@user_router.message(CommandStart())
async def start_cmd1(message: Message):
    try:
        try:
            from src.utils.gamification import GamificationEngine
            streak_result = GamificationEngine.check_streak(message.from_user.id)
            if streak_result.get('success') and streak_result.get('xp_reward', 0) > 0:
                await message.answer(
                    f"🔥 <b>Izchillik: {streak_result['streak']} kun!</b>\n"
                    f"🎁 +{streak_result['xp_reward']} XP bonus!",
                    parse_mode="HTML"
                )
        except Exception as e:
            print(f"[DEBUG] Streak check on start: {e}")

        await message.answer(
            MSG["welcome"],
            reply_markup=await UserPanels.user_main_menu(),
            parse_mode="HTML"
        )
    except Exception as e:
        await message.answer(
            "👋 Botimizga xush kelibsiz!\n\n"
            "Iltimos, /start buyrug'ini qaytadan bosing."
        )
        print(f"[ERROR] start_cmd1: {e}")


@user_router.callback_query(F.data == "check", F.message.chat.type == ChatType.PRIVATE)
async def check(call: CallbackQuery):
    user_id = call.from_user.id
    try:
        check_status, channels = await CheckData.check_member(bot, user_id)
        if check_status:
            await call.message.delete()
            await bot.send_message(
                chat_id=user_id,
                text=MSG["welcome"],
                reply_markup=await UserPanels.user_main_menu(),
                parse_mode="HTML"
            )
            try:
                await call.answer()
            except Exception as e:
                print(f"[WARNING] Failed to answer callback: {e}")
        else:
            try:
                await call.answer(show_alert=True, text="Botimizdan foydalanish uchun barcha kanallarga a'zo bo'ling")
            except Exception as e:
                print(f"[WARNING] Failed to show alert: {e}")
                try:
                    await call.answer()
                except Exception as e2:
                    print(f"[WARNING] Failed to answer callback after alert: {e2}")
    except Exception as e:
        print(f"[ERROR] check callback handler: {e}")
        try:
            await bot.forward_message(chat_id=ADMIN_ID[0], from_chat_id=call.message.chat.id, message_id=call.message.message_id)
        except Exception as e2:
            print(f"[WARNING] Failed to forward error message to admin: {e2}")
        try:
            await bot.send_message(chat_id=ADMIN_ID[0], text=f"❌ Error in check callback:\n\nUser: {call.from_user.id}\nError: {str(e)}")
        except Exception as e3:
            print(f"[ERROR] Failed to notify admin about error: {e3}")
