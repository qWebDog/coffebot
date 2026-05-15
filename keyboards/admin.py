from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def admin_main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="меню >", callback_data="admin_menu")],
        [InlineKeyboardButton(text="дополнительно >", callback_data="admin_extras")],
        [InlineKeyboardButton(text="продажи >", callback_data="admin_sales")]
    ])

def admin_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="обновить фото меню", callback_data="admin_upd_order_photo")],
        [InlineKeyboardButton(text="добавить категорию", callback_data="admin_add_cat")],
        [InlineKeyboardButton(text="добавить напиток", callback_data="admin_add_drink")],
        [InlineKeyboardButton(text="редактировать напитки", callback_data="admin_edit_drinks")],
        [InlineKeyboardButton(text="назад", callback_data="admin_main")]
    ])

def admin_extras_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="добавить", callback_data="admin_add_extra")],
        [InlineKeyboardButton(text="редактировать", callback_data="admin_edit_extras")],
        [InlineKeyboardButton(text="назад", callback_data="admin_main")]
    ])

def admin_categories_kb(categories: list[dict]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=c["name"], callback_data=f"admin_sel_cat_{c['id']}")] for c in categories
    ])
    kb.inline_keyboard.append([InlineKeyboardButton(text="назад", callback_data="admin_menu")])
    return kb

def admin_items_list_kb(items: list[dict], back_cb: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for d in items:
        kb.inline_keyboard.append([InlineKeyboardButton(
            text=f"{d['name']} | {d['price']}₽",
            callback_data=f"admin_edit_item_{d['id']}"
        )])
    kb.inline_keyboard.append([InlineKeyboardButton(text="назад", callback_data=back_cb)])
    return kb

def admin_edit_item_kb(item_id: int, back_cb: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Имя", callback_data=f"admin_upd_name_{item_id}")],
        [InlineKeyboardButton(text="💰 Цена", callback_data=f"admin_upd_price_{item_id}")],
        [InlineKeyboardButton(text="📏 Объем", callback_data=f"admin_upd_volume_{item_id}")],
        [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"admin_del_item_{item_id}")],
        [InlineKeyboardButton(text="назад", callback_data=back_cb)]
    ])

def admin_confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Сохранить", callback_data="admin_save_drink"),
         InlineKeyboardButton(text="❌ Отмена", callback_data="admin_cancel_drink")]
    ])

def admin_sales_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="сегодня", callback_data="admin_stats_today")],
        [InlineKeyboardButton(text="за месяц", callback_data="admin_stats_month")],
        [InlineKeyboardButton(text="назад", callback_data="admin_main")]
    ])

def back_kb(callback: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="назад", callback_data=callback)]])
