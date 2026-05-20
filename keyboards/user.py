from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def main_menu_kb(cats: list[dict]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=c["name"], callback_data=f"cat_{c['slug']}")] for c in cats] + 
                                [[InlineKeyboardButton(text="🛒 Корзина", callback_data="view_cart")]])

def category_items_kb(items: list[dict]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=i["name"], callback_data=f"item_{i['id']}")] for i in items] + 
                                [[InlineKeyboardButton(text="🔙 Назад в меню", callback_data="back_to_main")]])

def item_volumes_kb(volumes: dict) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"{vd['name']} — {int(vd['price'])}₽", callback_data=f"vol_{vid}")] for vid, vd in volumes.items()] + 
                                [[InlineKeyboardButton(text="🔙 Отмена", callback_data="back_to_main")]])

def extra_cats_kb(cats: list[dict]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=c["name"], callback_data=f"excat_{c['id']}")] for c in cats] + 
                                [[InlineKeyboardButton(text="✅ Готово", callback_data="back_to_cart_from_extras")]])

def extras_kb(extras: list[dict]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"{e['name']} ({e.get('volume', 'Стд')}) — {int(e['price'])}₽", callback_data=f"add_ex_{e['id']}")] for e in extras] + 
                                [[InlineKeyboardButton(text="🔙 Назад к списку допов", callback_data="back_to_excats")]])

def cart_kb(cart_lines: list[dict]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for idx, line in enumerate(cart_lines):
        extras_txt = f" + {', '.join(e['name'] for e in line.get('extras', []))}" if line.get('extras') else ""
        kb.inline_keyboard.append([InlineKeyboardButton(text=f"{line['name']} ({line['vol']}){extras_txt} x{line['qty']} = {int(line['line_total'])}₽", callback_data=f"cart_info_{idx}")])
        kb.inline_keyboard.append([
            InlineKeyboardButton(text="📦 Допы ➕", callback_data=f"cart_add_extras_{idx}"),
            InlineKeyboardButton(text="➖", callback_data=f"cart_minus_{idx}"),
            InlineKeyboardButton(text="➕", callback_data=f"cart_plus_{idx}")
        ])
    kb.inline_keyboard.append([
        InlineKeyboardButton(text="✅ Оформить заказ", callback_data="checkout"),
        InlineKeyboardButton(text="🗑 Очистить корзину", callback_data="clear_cart")
    ])
    return kb

def time_kb(offset: int) -> InlineKeyboardMarkup:
    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo
    now = datetime.now(tz=ZoneInfo("Europe/Moscow")) + timedelta(minutes=offset)
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ -5 мин", callback_data="time_minus"),
         InlineKeyboardButton(text=f"🕒 {now.strftime('%H:%M')}", callback_data="time_ignore"),
         InlineKeyboardButton(text="➕ +5 мин", callback_data="time_plus")],
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data="time_confirm")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_cart")]
    ])

def post_time_question_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Вернуться в меню", callback_data="after_time_menu")],
        [InlineKeyboardButton(text="💳 Перейти к оплате", callback_data="after_time_pay")]
    ])
