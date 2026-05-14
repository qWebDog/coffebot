# handlers/commands.py
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from keyboards.menu import menu_keyboard
from db.database import db

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message):
    menu_items = await db.get_menu_items()
    
    if not menu_items:
        return await message.answer(
            "📭 Меню пока пусто.\nАдминистратор скоро добавит напитки ☕"
        )
    
    # 🖼 Берём общее фото меню из настроек
    menu_photo = await db.get_setting("menu_photo")
    
    caption = "☕ *Добро пожаловать!* Выберите напиток:"
    
    if menu_photo:
        await message.answer_photo(
            photo=menu_photo,
            caption=caption,
            reply_markup=menu_keyboard(menu_items),
            parse_mode="Markdown"
        )
    else:
        # Фолбэк: если админ ещё не загрузил фото меню
        await message.answer(
            caption,
            reply_markup=menu_keyboard(menu_items),
            parse_mode="Markdown"
        )
