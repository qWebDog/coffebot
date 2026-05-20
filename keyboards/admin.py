from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def admin_main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🖼 Фото меню", callback_data="admin_menu_photo")],
        [InlineKeyboardButton(text="📂 Категории меню", callback_data="admin_cats")],
        [InlineKeyboardButton(text="📏 Объемы", callback_data="admin_vols")],
        [InlineKeyboardButton(text="🥐 Категории допов", callback_data="admin_extracats")],
        [InlineKeyboardButton(text="📝 Список допов", callback_data="admin_extras")],
        [InlineKeyboardButton(text="📊 Продажи", callback_data="admin_sales")]
    ])

def admin_cats_kb(cats: list[dict]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=c["name"], callback_data=f"admin_cat_{c['slug']}")] for c in cats] + 
                                [[InlineKeyboardButton(text="🔙 Назад", callback_data="admin_main")]])

def admin_cat_menu_kb(slug: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🖼 Заменить фото", callback_data=f"admin_photo_{slug}")],
        [InlineKeyboardButton(text="➕ Добавить позицию", callback_data=f"admin_add_{slug}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_cats")]
    ])

def admin_extracats_kb(cats: list[dict]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=c["name"], callback_data=f"admin_extracat_{c['id']}")] for c in cats] + 
                                [[InlineKeyboardButton(text="➕ Создать категорию", callback_data="admin_create_extracat")],
                                 [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_main")]])

def admin_extracat_menu_kb(cat_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🖼 Заменить фото", callback_data=f"admin_extraphoto_{cat_id}")],
        [InlineKeyboardButton(text="➕ Добавить доп", callback_data=f"admin_addextra_{cat_id}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_extracats")]
    ])

def admin_extras_kb(extras: list[dict]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"{e['name']} ({int(e['price'])}₽) 🗑", callback_data=f"admin_delextra_{e['id']}")] for e in extras])
    kb.inline_keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin_main")])
    return kb

def admin_vols_kb(vols: list[dict]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=v["name"], callback_data=f"admin_vol_{v['id']}")] for v in vols] + 
                                [[InlineKeyboardButton(text="➕ Создать объем", callback_data="admin_create_vol"), InlineKeyboardButton(text="🔙 Назад", callback_data="admin_main")]])

def admin_toggle_vols_kb(vols: list[dict], selected: list[int]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"{'✅' if v['id'] in selected else '☐'} {v['name']}", callback_data=f"admin_vol_toggle_{v['id']}")] for v in vols] + 
                                [[InlineKeyboardButton(text="✅ Далее", callback_data="admin_vol_confirm")]])

def back_kb(cb: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data=cb)]])
