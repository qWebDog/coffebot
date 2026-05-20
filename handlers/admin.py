import re, json
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramBadRequest
from keyboards.admin import *
from db.database import db
from config import settings
from utils.safe_edit import safe_edit

router = Router()

class AdminFSM(StatesGroup):
    main = State()
    set_menu_photo = State()
    wait_menu_cat_photo = State()   # ✅ Явное состояние для фото категорий меню
    wait_extra_cat_photo = State()  # ✅ Явное состояние для фото категорий допов
    add_item_name = State()
    add_item_vols = State()
    add_item_prices = State()
    add_vol_name = State()
    add_extra_name = State()
    add_extra_volume = State()
    add_extra_price = State()

def is_admin(uid: int) -> bool:
    return str(uid) in [x.strip() for x in settings.admin_ids.split(",") if x.strip()]

# 🔹 ВХОД
@router.message(Command("admin"))
async def cmd_admin(msg: Message, state: FSMContext, bot: Bot):
    if not is_admin(msg.from_user.id): return await msg.answer("🚫 Доступ запрещён")
    sent = await msg.answer("👨‍💼 Админ-панель", reply_markup=admin_main_kb())
    await state.set_state(AdminFSM.main)
    await state.update_data({"cid": msg.chat.id, "mid": sent.message_id})

@router.callback_query(F.data == "admin_main")
async def back_main(call: CallbackQuery, state: FSMContext, bot: Bot):
    await state.set_state(AdminFSM.main)
    await safe_edit(bot, call.from_user.id, call.message.message_id, "👨‍💼 Админ-панель", admin_main_kb())
    await call.answer()

# 🖼 ФОТО ГЛАВНОГО МЕНЮ
@router.callback_query(F.data == "admin_menu_photo")
async def prompt_menu_photo(call: CallbackQuery, state: FSMContext, bot: Bot):
    await state.set_state(AdminFSM.set_menu_photo)
    await state.update_data({"cid": call.from_user.id, "mid": call.message.message_id})
    try: await call.message.edit_text("📸 Отправьте фото для /start:", reply_markup=back_kb("admin_main"))
    except: await call.message.answer("📸 Отправьте фото для /start:", reply_markup=back_kb("admin_main"))
    await call.answer()

@router.message(F.photo, AdminFSM.set_menu_photo)
async def save_menu_photo(msg: Message, state: FSMContext, bot: Bot):
    await db.set_setting("menu_photo", msg.photo[-1].file_id)
    data = await state.get_data()
    await state.set_state(AdminFSM.main)
    await safe_edit(bot, data["cid"], data["mid"], "✅ Фото меню обновлено!", admin_main_kb())
    await msg.delete()

# 📂 КАТЕГОРИИ МЕНЮ + ФОТО
@router.callback_query(F.data == "admin_cats")
async def show_cats(call: CallbackQuery, bot: Bot):
    cats = await db.get_categories()
    try: await call.message.edit_text("📂 Управление категориями", reply_markup=admin_cats_kb(cats))
    except: await call.message.answer("📂 Управление категориями", reply_markup=admin_cats_kb(cats))
    await call.answer()

@router.callback_query(F.data.startswith("admin_cat_"))
async def cat_menu(call: CallbackQuery, bot: Bot):
    slug = "_".join(call.data.split("_")[2:])
    cats = await db.get_categories()
    cat = next((c for c in cats if c["slug"] == slug), None)
    name = cat["name"] if cat else slug
    try: await call.message.edit_text(f"📂 Категория: {name}", reply_markup=admin_cat_menu_kb(slug))
    except: await call.message.answer(f"📂 Категория: {name}", reply_markup=admin_cat_menu_kb(slug))
    await call.answer()

@router.callback_query(F.data.startswith("admin_photo_"))
async def prompt_cat_photo(call: CallbackQuery, state: FSMContext, bot: Bot):
    slug = "_".join(call.data.split("_")[2:])
    await state.set_state(AdminFSM.wait_menu_cat_photo)
    await state.update_data({"cat_slug": slug, "cid": call.from_user.id, "mid": call.message.message_id})
    try: await call.message.edit_text(f"📸 Отправьте фото для '{slug}':", reply_markup=back_kb("admin_cats"))
    except: await call.message.answer(f"📸 Отправьте фото для '{slug}':", reply_markup=back_kb("admin_cats"))
    await call.answer()

@router.message(F.photo, AdminFSM.wait_menu_cat_photo)
async def handle_menu_cat_photo(msg: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    await db.update_cat_photo(data["cat_slug"], msg.photo[-1].file_id)
    await state.set_state(AdminFSM.main)
    await safe_edit(bot, data["cid"], data["mid"], "✅ Фото категории обновлено!", admin_cat_menu_kb(data["cat_slug"]))
    await msg.delete()

# 🥐 КАТЕГОРИИ ДОПОВ + ФОТО
@router.callback_query(F.data == "admin_extracats")
async def show_extracats(call: CallbackQuery, bot: Bot):
    cats = await db.get_extra_categories()
    try: await call.message.edit_text("📂 Категории допов", reply_markup=admin_extracats_kb(cats))
    except: await call.message.answer("📂 Категории допов", reply_markup=admin_extracats_kb(cats))
    await call.answer()

@router.callback_query(F.data == "admin_create_extracat")
async def prompt_extracat(call: CallbackQuery, state: FSMContext, bot: Bot):
    await state.update_data({"action": "new_extracat", "cid": call.from_user.id, "mid": call.message.message_id})
    try: await call.message.edit_text("📝 Введите название категории допов:", reply_markup=back_kb("admin_extracats"))
    except: await call.message.answer("📝 Введите название категории допов:", reply_markup=back_kb("admin_extracats"))
    await call.answer()

@router.message(F.text, AdminFSM.main)
async def handle_text(msg: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    if data.get("action") == "new_extracat":
        await db.add_extra_category(msg.text.strip())
        await state.clear()
        await safe_edit(bot, data["cid"], data["mid"], "✅ Категория создана!", admin_extracats_kb(await db.get_extra_categories()))
        await msg.delete()

@router.callback_query(F.data.startswith("admin_extracat_"))
async def extracat_menu(call: CallbackQuery, bot: Bot):
    cat_id = int(call.data.split("_")[2])
    try: await call.message.edit_text("📂 Управление категорией допов", reply_markup=admin_extracat_menu_kb(cat_id))
    except: await call.message.answer("📂 Управление категорией допов", reply_markup=admin_extracat_menu_kb(cat_id))
    await call.answer()

@router.callback_query(F.data.startswith("admin_extraphoto_"))
async def prompt_extraphoto(call: CallbackQuery, state: FSMContext, bot: Bot):
    cat_id = int(call.data.split("_")[2])
    await state.set_state(AdminFSM.wait_extra_cat_photo)
    await state.update_data({"extra_cat_id": cat_id, "cid": call.from_user.id, "mid": call.message.message_id})
    try: await call.message.edit_text("📸 Отправьте фото для этой категории допов:", reply_markup=back_kb("admin_extracats"))
    except: await call.message.answer("📸 Отправьте фото для этой категории допов:", reply_markup=back_kb("admin_extracats"))
    await call.answer()

@router.message(F.photo, AdminFSM.wait_extra_cat_photo)
async def handle_extra_cat_photo(msg: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    await db.update_extra_cat_photo(data["extra_cat_id"], msg.photo[-1].file_id)
    await state.set_state(AdminFSM.main)
    await safe_edit(bot, data["cid"], data["mid"], "✅ Фото категории допов обновлено!", admin_extracat_menu_kb(data["extra_cat_id"]))
    await msg.delete()

# 📝 СОЗДАНИЕ ДОПА
@router.callback_query(F.data.startswith("admin_addextra_"))
async def start_add_extra(call: CallbackQuery, state: FSMContext, bot: Bot):
    cat_id = int(call.data.split("_")[2])
    await state.set_state(AdminFSM.add_extra_name)
    await state.update_data({"extra_cat_id": cat_id, "cid": call.from_user.id, "mid": call.message.message_id})
    try: await call.message.edit_text("📝 Введите название дополнения:", reply_markup=back_kb("admin_extracats"))
    except: await call.message.answer("📝 Введите название дополнения:", reply_markup=back_kb("admin_extracats"))
    await call.answer()

@router.message(AdminFSM.add_extra_name)
async def proc_extra_name(msg: Message, state: FSMContext, bot: Bot):
    await state.update_data({"extra_name": msg.text.strip()})
    await state.set_state(AdminFSM.add_extra_volume)
    data = await state.get_data()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭ Пропустить объем", callback_data="skip_extra_vol")],
        [InlineKeyboardButton(text="🔙 Отмена", callback_data="admin_extracats")]
    ])
    await safe_edit(bot, data["cid"], data["mid"], "📏 Введите объем (напр. 30мл, шот) или нажмите пропустить:", kb)
    await msg.delete()

@router.callback_query(F.data == "skip_extra_vol")
async def skip_extra_vol(call: CallbackQuery, state: FSMContext, bot: Bot):
    await state.update_data({"extra_volume": "Стандарт"})
    await state.set_state(AdminFSM.add_extra_price)
    data = await state.get_data()
    await safe_edit(bot, data["cid"], data["mid"], "💰 Введите цену:", back_kb("admin_extracats"))
    await call.answer()

@router.message(AdminFSM.add_extra_volume)
async def proc_extra_volume(msg: Message, state: FSMContext, bot: Bot):
    await state.update_data({"extra_volume": msg.text.strip()})
    await state.set_state(AdminFSM.add_extra_price)
    data = await state.get_data()
    await safe_edit(bot, data["cid"], data["mid"], "💰 Введите цену:", back_kb("admin_extracats"))
    await msg.delete()

@router.message(AdminFSM.add_extra_price)
async def proc_extra_price(msg: Message, state: FSMContext, bot: Bot):
    if not re.match(r"^\d+(\.\d+)?$", msg.text.strip()): return await msg.answer("❌ Введите число")
    data = await state.get_data()
    await db.add_extra(data["extra_cat_id"], data["extra_name"], float(msg.text.strip()), data.get("extra_volume", "Стандарт"))
    await state.set_state(AdminFSM.main)
    extras = await db.get_extras_by_category(data["extra_cat_id"])
    kb = admin_extras_kb(extras) if extras else admin_extracat_menu_kb(data["extra_cat_id"])
    await safe_edit(bot, data["cid"], data["mid"], "✅ Дополнение сохранено!", kb)
    await msg.delete()

# 📝 СПИСОК ДОПОВ & УДАЛЕНИЕ
@router.callback_query(F.data == "admin_extras")
async def show_extras(call: CallbackQuery, bot: Bot):
    all_extras = []
    for cat in await db.get_extra_categories():
        for ex in await db.get_extras_by_category(cat["id"]):
            all_extras.append({"id": ex["id"], "name": ex["name"], "volume": ex["volume"], "price": ex["price"], "cat": cat["name"]})
    try: await call.message.edit_text("📝 Список допов", reply_markup=admin_extras_kb(all_extras))
    except: await call.message.answer("📝 Список допов", reply_markup=admin_extras_kb(all_extras))
    await call.answer()

@router.callback_query(F.data.startswith("admin_delextra_"))
async def del_extra(call: CallbackQuery, bot: Bot):
    await db.delete_extra(int(call.data.split("_")[2]))
    all_extras = [{"id": e["id"], "name": e["name"], "price": e["price"], "cat": "Все"} 
                  for c in await db.get_extra_categories() for e in await db.get_extras_by_category(c["id"])]
    try: await call.message.edit_text("📝 Список допов", reply_markup=admin_extras_kb(all_extras))
    except: await call.message.answer("📝 Список допов", reply_markup=admin_extras_kb(all_extras))
    await call.answer()

# ☕ ДОБАВЛЕНИЕ НАПИТКА (без изменений, но безопасно)
@router.callback_query(F.data.startswith("admin_add_"))
async def start_add_item(call: CallbackQuery, state: FSMContext, bot: Bot):
    slug = "_".join(call.data.split("_")[2:])
    cats = await db.get_categories()
    cat = next((c for c in cats if c["slug"] == slug), None)
    cat_id = cat["id"] if cat else 1
    await state.set_state(AdminFSM.add_item_name)
    await state.update_data({"cat_id": cat_id, "cid": call.from_user.id, "mid": call.message.message_id})
    name = cat["name"] if cat else slug
    try: await call.message.edit_text(f"📝 Введите название для '{name}':", reply_markup=back_kb(f"admin_cat_{slug}"))
    except: await call.message.answer(f"📝 Введите название для '{name}':", reply_markup=back_kb(f"admin_cat_{slug}"))
    await call.answer()

@router.message(AdminFSM.add_item_name)
async def proc_item_name(msg: Message, state: FSMContext, bot: Bot):
    await state.update_data({"item_name": msg.text.strip()})
    await state.set_state(AdminFSM.add_item_vols)
    vols = await db.get_volumes()
    data = await state.get_data()
    await safe_edit(bot, data["cid"], data["mid"], "📏 Выберите объемы:", admin_toggle_vols_kb(vols, []))
    await state.update_data({"sel_vols": []})
    await msg.delete()

@router.callback_query(F.data.startswith("admin_vol_toggle_"))
async def toggle_vol(call: CallbackQuery, state: FSMContext, bot: Bot):
    vid = int(call.data.split("_")[-1])
    data = await state.get_data()
    sel = data.get("sel_vols", [])
    if vid in sel: sel.remove(vid)
    else: sel.append(vid)
    await state.update_data({"sel_vols": sel})
    await call.message.edit_reply_markup(reply_markup=admin_toggle_vols_kb(await db.get_volumes(), sel))
    await call.answer()

@router.callback_query(F.data == "admin_vol_confirm")
async def confirm_vols(call: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    if not data.get("sel_vols"): return await call.answer("⚠️ Выберите объем", show_alert=True)
    await state.set_state(AdminFSM.add_item_prices)
    vols = await db.get_volumes()
    target = [v for v in vols if v["id"] in data["sel_vols"]]
    await state.update_data({"vol_list": target, "vol_idx": 0, "vol_prices": {}})
    await safe_edit(bot, data["cid"], data["mid"], f"💰 Цена для: {target[0]['name']}", back_kb("admin_vols"))
    await call.answer()

@router.message(AdminFSM.add_item_prices)
async def proc_price(msg: Message, state: FSMContext, bot: Bot):
    if not re.match(r"^\d+(\.\d+)?$", msg.text.strip()): return await msg.answer("❌ Введите число")
    data = await state.get_data()
    vol = data["vol_list"][data["vol_idx"]]
    data["vol_prices"][vol["id"]] = float(msg.text.strip())
    data["vol_idx"] += 1
    await state.update_data(data)
    if data["vol_idx"] >= len(data["vol_list"]):
        await db.add_item(data["cat_id"], data["item_name"], json.dumps(data["vol_prices"]))
        await state.set_state(AdminFSM.main)
        await safe_edit(bot, data["cid"], data["mid"], "✅ Напиток сохранён!", admin_main_kb())
    else:
        next_vol = data["vol_list"][data["vol_idx"]]
        await safe_edit(bot, data["cid"], data["mid"], f"💰 Цена для: {next_vol['name']}", back_kb("admin_vols"))
    await msg.delete()

# 📏 ОБЪЕМЫ
@router.callback_query(F.data == "admin_vols")
async def show_vols(call: CallbackQuery, bot: Bot):
    try: await call.message.edit_text("📏 Объемы", reply_markup=admin_vols_kb(await db.get_volumes()))
    except: await call.message.answer("📏 Объемы", reply_markup=admin_vols_kb(await db.get_volumes()))
    await call.answer()

@router.callback_query(F.data == "admin_create_vol")
async def prompt_vol(call: CallbackQuery, state: FSMContext, bot: Bot):
    await state.set_state(AdminFSM.add_vol_name)
    await state.update_data({"cid": call.from_user.id, "mid": call.message.message_id})
    try: await call.message.edit_text("📏 Название объема:", reply_markup=back_kb("admin_vols"))
    except: await call.message.answer("📏 Название объема:", reply_markup=back_kb("admin_vols"))
    await call.answer()

@router.message(AdminFSM.add_vol_name)
async def save_vol(msg: Message, state: FSMContext, bot: Bot):
    await db.add_volume(msg.text.strip())
    data = await state.get_data()
    await state.set_state(AdminFSM.main)
    await safe_edit(bot, data["cid"], data["mid"], "✅ Создано!", admin_vols_kb(await db.get_volumes()))
    await msg.delete()

@router.callback_query(F.data == "admin_sales")
async def show_sales(call: CallbackQuery, bot: Bot):
    try: await call.message.edit_text("📊 Статистика в разработке", reply_markup=back_kb("admin_main"))
    except: await call.message.answer("📊 Статистика в разработке", reply_markup=back_kb("admin_main"))
    await call.answer()
