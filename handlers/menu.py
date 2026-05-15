from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def menu_keyboard(items: list[dict]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{item['name']} ({item['volume']}) — {int(item['price'])}₽", callback_data=f"add_{item['id']}")]
        for item in items
    ])
    kb.inline_keyboard.append([InlineKeyboardButton(text="дополнительно >", callback_data="view_extras")])
    kb.inline_keyboard.append([InlineKeyboardButton(text="🛒 Корзина", callback_data="view_cart")])
    return kb

def extras_keyboard(items: list[dict]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{item['name']} — {int(item['price'])}₽", callback_data=f"add_{item['id']}")]
        for item in items
    ])
    kb.inline_keyboard.append([InlineKeyboardButton(text="🔙 Назад в меню", callback_data="view_extras_back")])
    return kb
