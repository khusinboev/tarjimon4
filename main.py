import asyncio
import logging

from config import dp, bot
from src.db.init_db import create_all_base, init_languages_table, create_indexes_and_constraints
from src.handlers.admins.admin import admin_router
from src.handlers.admins.messages import msg_router
from src.handlers.others.channels import channel_router
from src.handlers.others.groups import group_router
from src.handlers.others.other import other_router
from src.handlers.users.inline_translate import inline_router
from src.handlers.users.lughatlar import vocabs_router
from src.handlers.users.lughatlar.essential import essential_router
from src.handlers.users.lughatlar.lughatlarim import lughatlarim_router
from src.handlers.users.lughatlar.mashqlar import mashqlar_router
from src.handlers.users.lughatlar.ommaviylar import ommaviylar_router
from src.handlers.users.lughatlar.parallel import parallel_router
from src.handlers.users.translate import translate_router
from src.handlers.users.users import user_router
from src.middlewares.middleware import RegisterUserMiddleware


async def on_startup() -> None:
    try:
        # Asosiy jadvallarni yaratish
        await create_all_base()

        # Tillar jadvalini to'ldirish
        init_languages_table()

        # Qo'shimcha indekslar
        create_indexes_and_constraints()

        print("🎉 Ma'lumotlar bazasi muvaffaqiyatli sozlandi!")

    except Exception as e:
        print(f"❌ Ma'lumotlar bazasi sozlashda xato: {e}")
        raise e


async def main():
    await on_startup()
    logging.basicConfig(level=logging.INFO)

    dp.update.middleware(RegisterUserMiddleware())

    #for admin
    dp.include_router(admin_router)
    dp.include_router(msg_router)

    #for user
    dp.include_router(vocabs_router)        # Asosiy kabinet va sozlamalar
    dp.include_router(lughatlarim_router)   # Lug'atlarim bo'limi
    dp.include_router(mashqlar_router)      # Mashqlar bo'limi
    dp.include_router(ommaviylar_router)    # Ommaviy lug'atlar bo'limi
    dp.include_router(essential_router)    # essential_router lug'atlar bo'limi
    dp.include_router(parallel_router)  # ⭐ YANGI: Parallel tarjimalar
    dp.include_router(user_router)
    dp.include_router(translate_router)
    dp.include_router(inline_router)
    
    #for other
    dp.include_router(group_router)
    dp.include_router(channel_router)
    dp.include_router(other_router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())