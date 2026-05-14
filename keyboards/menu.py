from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import settings

MENU = [
    {"id": "espresso", "name": "Эспрессо", "price": 120.0, "photo_url": "https://img.icons8.com/color/480/espresso-cup.png"},
    {"id": "latte", "name": "Латте", "price": 180.0, "photo_url": "https://img.icons8.com/color/480/latte.png"},
    {"id": "cappuccino", "name": "Капучино", "price": 190.0, "photo_url": "https://img.icons8.com/color/480/cappuccino.png"},
]

def menu_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{m['name']} — {int(m['price'])}₽", callback_data=f"add_{m['id']}")]
        for m in MENU
    ])
    kb.inline_keyboard.append([InlineKeyboardButton(text="🛒 Корзина", callback_data="view_cart")])
    return kb