# keyboards/user.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta

def main_menu_kb(cats: list[dict]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=c["name"], callback_data=f"cat_{c['slug']}")] for c in cats])
    kb.inline_keyboard.append([InlineKeyboardButton(text="🛒 Корзина", callback_data="view_cart")])
    return kb

def category_items_kb(items: list[dict]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=i["name"], callback_data=f"item_{i['id']}")] for i in items])
    kb.inline_keyboard.append([InlineKeyboardButton(text="🔙 Назад в меню", callback_data="back_to_main")])
    return kb

def item_volumes_kb(volumes: dict) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{vol_data['name']} — {int(vol_data['price'])}₽", callback_data=f"vol_{vid}")]
        for vid, vol_data in volumes.items()
    ])
    kb.inline_keyboard.append([InlineKeyboardButton(text="🔙 Отмена", callback_data="back_to_main")])
    return kb

def extras_kb(extras: list[dict], selected_ids: list[int]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for e in extras:
        mark = "✅" if e["id"] in selected_ids else "☐"
        kb.inline_keyboard.append([InlineKeyboardButton(text=f"{mark} {e['name']} ({int(e['price'])}₽)", callback_data=f"extra_toggle_{e['id']}")])
    kb.inline_keyboard.append([InlineKeyboardButton(text="➕ Добавить в заказ", callback_data="confirm_extras"), InlineKeyboardButton(text="Без допов", callback_data="no_extras")])
    kb.inline_keyboard.append([InlineKeyboardButton(text="🔙 Отмена", callback_data="back_to_main")])
    return kb

def cart_kb(cart_lines: list[dict]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for idx, line in enumerate(cart_lines):
        extras_txt = f" + {', '.join(e['name'] for e in line['extras'])}" if line['extras'] else ""
        kb.inline_keyboard.append([InlineKeyboardButton(text=f"{line['name']} ({line['vol']}){extras_txt} x{line['qty']} = {int(line['line_total'])}₽", callback_data=f"cart_info_{idx}")])
        kb.inline_keyboard.append([InlineKeyboardButton(text="➖", callback_data=f"cart_minus_{idx}"), InlineKeyboardButton(text="➕", callback_data=f"cart_plus_{idx}")])
    
    # ✅ Кнопка-разделитель убрана по запросу
    kb.inline_keyboard.append([InlineKeyboardButton(text="✅ Оформить", callback_data="checkout"), InlineKeyboardButton(text="🗑 Очистить", callback_data="clear_cart")])
    return kb

def time_selection_kb(offset_minutes: int) -> InlineKeyboardMarkup:
    target_time = datetime.now() + timedelta(minutes=offset_minutes)
    time_str = target_time.strftime("%H:%M")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ -5 мин", callback_data="time_minus"),
         InlineKeyboardButton(text=f"🕒 {time_str}", callback_data="time_ignore"),
         InlineKeyboardButton(text="➕ +5 мин", callback_data="time_plus")]
    ])
    kb.inline_keyboard.append([InlineKeyboardButton(text="✅ Подтвердить время", callback_data="time_confirm")])
    kb.inline_keyboard.append([InlineKeyboardButton(text="🔙 Назад к корзине", callback_data="back_to_cart")])
    return kb
