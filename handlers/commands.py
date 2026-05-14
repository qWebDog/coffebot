from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from keyboards.menu import menu_keyboard, MENU

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message):
    # Отправляем фото первого товара как "приветствие" (Telegram не поддерживает фото в inline)
    await message.answer_photo(
        photo=MENU[0]["photo_url"],
        caption="☕ Добро пожаловать! Выберите напиток:",
        reply_markup=menu_keyboard()
    )