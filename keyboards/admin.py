from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def admin_main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="меню >", callback_data="admin_menu")],
        [InlineKeyboardButton(text="объемы >", callback_data="admin_volumes")],
        [InlineKeyboardButton(text="продажи >", callback_data="admin_sales")]
    ])

def admin_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="обновить фото", callback_data="admin_upd_photo")],
        [InlineKeyboardButton(text="добавить категорию", callback_data="admin_add_cat")],
        [InlineKeyboardButton(text="добавить напиток", callback_data="admin_add_drink")],
        [InlineKeyboardButton(text="редактировать напитки", callback_data="admin_edit_drinks")],
        [InlineKeyboardButton(text="добавить дополнение", callback_data="admin_add_extra")],
        [InlineKeyboardButton(text="назад", callback_data="admin_main")]
    ])

def admin_volumes_kb(vols: list[dict]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{v['name']}", callback_data=f"admin_edit_vol_{v['id']}")] for v in vols
    ])
    kb.inline_keyboard.append([InlineKeyboardButton(text="➕ Создать объем", callback_data="admin_create_vol")])
    kb.inline_keyboard.append([InlineKeyboardButton(text="назад", callback_data="admin_main")])
    return kb

def admin_toggle_volumes_kb(vols: list[dict], selected: list[int]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for v in vols:
        mark = "☑️" if v["id"] in selected else "☐"
        kb.inline_keyboard.append([InlineKeyboardButton(text=f"{mark} {v['name']}", callback_data=f"vol_toggle_{v['id']}")])
    kb.inline_keyboard.append([InlineKeyboardButton(text="✅ Далее", callback_data="vol_confirm")])
    return kb

def admin_items_list_kb(items: list[dict], back: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"{i['name']}", callback_data=f"admin_edit_item_{i['id']}")] for i in items])
    kb.inline_keyboard.append([InlineKeyboardButton(text="назад", callback_data=back)])
    return kb

def admin_confirm_kb(save_cb: str = "admin_save") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Сохранить", callback_data=save_cb), InlineKeyboardButton(text="❌ Отмена", callback_data="admin_cancel")]])

def back_kb(cb: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="назад", callback_data=cb)]])
