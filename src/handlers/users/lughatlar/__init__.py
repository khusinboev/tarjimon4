from aiogram import Router
from .vocabs import vocabs_router
from .lughatlarim import lughatlarim_router
from .mashqlar import mashqlar_router
from .ommaviylar import ommaviylar_router

# Barcha routerlarni birlashtirish
lughatlar_router = Router()

# # Routerlarni qo'shish (tartib muhim!)
# lughatlar_router.include_router(vocabs_router)        # Asosiy kabinet va sozlamalar
# lughatlar_router.include_router(mashqlar_router)      # Mashqlar
# lughatlar_router.include_router(lughatlarim_router)   # Shaxsiy lug'atlar
# lughatlar_router.include_router(ommaviylar_router)    # Ommaviy lug'atlar

__all__ = ['lughatlar_router']