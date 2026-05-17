from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def admin_main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📂 Категории (фото/товары)", callback_data="admin_cats")],
        [InlineKeyboardButton(text="📏 Объемы", callback_data="admin_vols")],
        [InlineKeyboardButton(text="🥐 Допы", callback_data="admin_extras")],
        [InlineKeyboardButton(text="📊 Продажи", callback_data="admin_sales")]
    ])

def admin_cats_kb(cats: list[dict]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=c["name"], callback_data=f"admin_cat_{c['slug']}")] for c in cats])
    kb.inline_keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin_main")])
    return kb

def admin_cat_menu_kb(slug: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🖼 Заменить фото категории", callback_data=f"admin_photo_{slug}")],
        [InlineKeyboardButton(text="➕ Добавить позицию", callback_data=f"admin_add_{slug}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_cats")]
    ])

def admin_vols_kb(vols: list[dict]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=v["name"], callback_data=f"admin_vol_{v['id']}")] for v in vols])
    kb.inline_keyboard.append([InlineKeyboardButton(text="➕ Создать объем", callback_data="admin_create_vol"), InlineKeyboardButton(text="🔙 Назад", callback_data="admin_main")])
    return kb

def admin_extras_kb(extras: list[dict]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"{e['name']} ({int(e['price'])}₽)", callback_data=f"admin_extra_{e['id']}")] for e in extras])
    kb.inline_keyboard.append([InlineKeyboardButton(text="➕ Добавить доп", callback_data="admin_add_extra"), InlineKeyboardButton(text="🔙 Назад", callback_data="admin_main")])
    return kb

def admin_toggle_vols_kb(vols: list[dict], selected: list[int]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"{'✅' if v['id'] in selected else '☐'} {v['name']}", callback_data=f"admin_vol_toggle_{v['id']}")] for v in vols])
    kb.inline_keyboard.append([InlineKeyboardButton(text="✅ Далее", callback_data="admin_vol_confirm")])
    return kb

def back_kb(cb: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data=cb)]])
