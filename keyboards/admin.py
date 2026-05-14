from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def admin_main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить напиток", callback_data="admin_add")],
        [InlineKeyboardButton(text="✏️ Редактировать меню", callback_data="admin_edit_list")],
        [InlineKeyboardButton(text="📊 Сегодня", callback_data="admin_stats_today")],
        [InlineKeyboardButton(text="📈 Месяц", callback_data="admin_stats_month")],
        [InlineKeyboardButton(text="📅 Произвольный (7д)", callback_data="admin_stats_custom")],
    ])

def admin_items_kb(items: list) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for i in items:
        kb.inline_keyboard.append([InlineKeyboardButton(
            text=f"{i['name']} | {i['volume']} | {i['price']}₽",
            callback_data=f"admin_edit_{i['id']}"
        )])
    kb.inline_keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin_main")])
    return kb

def admin_edit_item_kb(item_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Имя", callback_data=f"admin_upd_name_{item_id}")],
        [InlineKeyboardButton(text="💰 Цена", callback_data=f"admin_upd_price_{item_id}")],
        [InlineKeyboardButton(text="📏 Объем", callback_data=f"admin_upd_volume_{item_id}")],
        [InlineKeyboardButton(text="🖼 Фото", callback_data=f"admin_upd_photo_{item_id}")],
        [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"admin_del_{item_id}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_edit_list")],
    ])