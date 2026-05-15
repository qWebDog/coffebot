from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from keyboards.menu import menu_keyboard
from db.database import db

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message):
    drinks = await db.get_drinks()
    
    if not drinks:
        return await message.answer("📭 Меню пока пусто.\nАдминистратор скоро добавит напитки ☕")
        
    menu_photo = await db.get_setting("menu_photo")
    caption = "☕ *Добро пожаловать!* Выберите напиток:"
    
    if menu_photo:
        await message.answer_photo(
            photo=menu_photo,
            caption=caption,
            reply_markup=menu_keyboard(drinks),
            parse_mode="Markdown"
        )
    else:
        await message.answer(
            caption,
            reply_markup=menu_keyboard(drinks),
            parse_mode="Markdown"
        )
