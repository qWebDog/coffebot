from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def cart_keyboard(items: dict, menu: list, is_checkout: bool = False) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    
    for item_id_str, qty in items.items():
        try:
            item_id = int(item_id_str)
            item = next((m for m in menu if m["id"] == item_id), None)
            if not item: continue
            
            line = f"• {item['name']} ({item['volume']}) × {qty} = {int(item['price'])*qty}₽"
            kb.inline_keyboard.append([InlineKeyboardButton(text=line, callback_data="cart_info")])
            
            if not is_checkout:
                kb.inline_keyboard.append([
                    InlineKeyboardButton(text="➖", callback_data=f"cart_minus_{item_id}"),
                    InlineKeyboardButton(text=f"{qty} шт.", callback_data="cart_ignore"),
                    InlineKeyboardButton(text="➕", callback_data=f"cart_plus_{item_id}")
                ])
        except: continue

    kb.inline_keyboard.append([InlineKeyboardButton(text="━━━━━━━━━━", callback_data="cart_ignore")])

    if is_checkout:
        kb.inline_keyboard.append([
            InlineKeyboardButton(text="💳 Оплатить заказ", callback_data="cart_pay"),
            InlineKeyboardButton(text="🔙 Назад в корзину", callback_data="cart_back")
        ])
    else:
        kb.inline_keyboard.append([
            InlineKeyboardButton(text="✅ Оформить заказ", callback_data="cart_checkout"),
            InlineKeyboardButton(text="🗑 Очистить", callback_data="cart_clear")
        ])
    return kb
