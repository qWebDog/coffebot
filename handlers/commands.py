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
    
    # 🔍 Берём первое фото, которое НЕ None
    photo_id = None
    for item in menu_items:
        if item.get("photo_id"):
            photo_id = item["photo_id"]
            break
    
    caption = "☕ *Добро пожаловать!* Выберите напиток:"
    
    if photo_id:
        # ✅ Отправляем с фото
        await message.answer_photo(
            photo=photo_id,
            caption=caption,
            reply_markup=menu_keyboard(menu_items),
            parse_mode="Markdown"
        )
    else:
        # ⚠️ Фолбэк: если ни у одного товара нет фото
        await message.answer(
            caption,
            reply_markup=menu_keyboard(menu_items),
            parse_mode="Markdown"
        )
