from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from config import bot
from src.keyboards.buttons import UserPanels

other_router = Router()
# some code...

@other_router.message()
async def chosen_lang(message: Message, state: FSMContext):
    await message.answer("<b>Bu tur topilmadi</b>", parse_mode="html")


# Shu yerda keyingi bosqichni (fac5 va hokazo) davom ettirishingiz mumkin.
# NOTE: Removed catch-all callback handler that was causing inline buttons to disappear
# All callbacks should be handled by specific handlers in their respective routers