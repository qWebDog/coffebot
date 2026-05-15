from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def menu_keyboard(drinks: list[dict]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=d["name"], callback_data=f"show_vols_{d['id']}")] for d in drinks
    ])
    kb.inline_keyboard.append([InlineKeyboardButton(text="🛒 Корзина", callback_data="view_cart")])
    return kb

def volume_keyboard(drink_id: int, vols: dict) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{v['name']} — {int(v['price'])}₽", callback_data=f"add_to_cart_{drink_id}_{vid}")]
        for vid, v in vols.items()
    ])
    kb.inline_keyboard.append([InlineKeyboardButton(text="🔙 Назад в меню", callback_data="back_to_menu")])
    return kb
