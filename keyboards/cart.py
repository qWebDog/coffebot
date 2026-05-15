from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def cart_keyboard(cart_items: dict, extras: list[dict], total: float, is_checkout: bool = False) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for key, qty in cart_items.items():
        kb.inline_keyboard.append([InlineKeyboardButton(text=f"{key} × {qty}", callback_data="cart_ignore")])
        if not is_checkout:
            kb.inline_keyboard.append([
                InlineKeyboardButton(text="➖", callback_data=f"cart_minus_{key}"),
                InlineKeyboardButton(text=f"{qty} шт.", callback_data="cart_ignore"),
                InlineKeyboardButton(text="➕", callback_data=f"cart_plus_{key}")
            ])
    
    kb.inline_keyboard.append([InlineKeyboardButton(text="➕ Добавить дополнение", callback_data="add_extra")])
    kb.inline_keyboard.append([InlineKeyboardButton(text=f"💰 Итого: {int(total)}₽", callback_data="cart_ignore")])
    
    if is_checkout:
        kb.inline_keyboard.append([InlineKeyboardButton(text="💳 Оплатить", callback_data="cart_pay"), InlineKeyboardButton(text="🔙 Назад", callback_data="cart_back")])
    else:
        kb.inline_keyboard.append([InlineKeyboardButton(text="✅ Оформить", callback_data="cart_checkout"), InlineKeyboardButton(text="🗑 Очистить", callback_data="cart_clear")])
    return kb

def extras_keyboard(extras: list[dict]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"{e['name']} — {int(e['price'])}₽", callback_data=f"add_extra_{e['id']}")] for e in extras])
    kb.inline_keyboard.append([InlineKeyboardButton(text="🔙 Назад в корзину", callback_data="back_to_cart")])
    return kb
