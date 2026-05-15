import re, json
from datetime import datetime
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramBadRequest
from keyboards.admin import *
from db.database import db
from config import settings

router = Router()

class AdminFSM(StatesGroup):
    main = State()
    add_drink_name = State()
    add_drink_vols = State()
    add_drink_prices = State()
    add_vol_name = State()
    edit_vol_name = State()

def is_admin(uid: int) -> bool:
    return str(uid) in [x.strip() for x in settings.admin_ids.split(",") if x.strip()]

async def safe_edit(bot: Bot, chat_id: int, msg_id: int, text: str, kb=None):
    try: await bot.edit_message_text(text, chat_id, msg_id, reply_markup=kb)
    except TelegramBadRequest: pass

@router.message(Command("admin"))
async def cmd_admin(msg: Message, state: FSMContext, bot: Bot):
    if not is_admin(msg.from_user.id): return await msg.answer("🚫 Доступ запрещён")
    sent = await msg.answer("админ-панель", reply_markup=admin_main_kb())
    await state.set_state(AdminFSM.main)
    await state.update_data({"chat_id": msg.chat.id, "msg_id": sent.message_id})

@router.callback_query(F.data == "admin_main")
async def back_main(call: CallbackQuery, state: FSMContext, bot: Bot):
    await state.set_state(AdminFSM.main)
    data = await state.get_data()
    await safe_edit(bot, call.from_user.id, data["msg_id"], "админ-панель", admin_main_kb())
    await call.answer()

# 📸 Фото
@router.callback_query(F.data == "admin_upd_photo")
async def upd_photo(call: CallbackQuery, state: FSMContext, bot: Bot):
    await state.update_data({"action": "upd_photo", "chat_id": call.from_user.id, "msg_id": call.message.message_id})
    await safe_edit(bot, call.from_user.id, call.message.message_id, "📸 Отправьте фото для /start:", back_kb("admin_menu"))
    await call.answer()
@router.message(F.photo, AdminFSM.main)
async def handle_photo(msg: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    if data.get("action") == "upd_photo":
        await db.set_setting("menu_photo", msg.photo[-1].file_id)
        await safe_edit(bot, data["chat_id"], data["msg_id"], "✅ Фото обновлено!", admin_menu_kb())
        try: await msg.delete()
        except: pass

# 🥤 Добавление напитка (Name -> Volumes -> Prices)
@router.callback_query(F.data == "admin_add_drink")
async def add_drink_name(call: CallbackQuery, state: FSMContext, bot: Bot):
    await state.set_state(AdminFSM.add_drink_name)
    await state.update_data({"chat_id": call.from_user.id, "msg_id": call.message.message_id, "add_back": "admin_menu"})
    await safe_edit(bot, call.from_user.id, call.message.message_id, "📝 Введите название напитка:", back_kb("admin_menu"))
    await call.answer()

@router.message(AdminFSM.add_drink_name)
async def proc_drink_name(msg: Message, state: FSMContext, bot: Bot):
    await state.update_data({"drink_name": msg.text.strip()})
    await state.set_state(AdminFSM.add_drink_vols)
    data = await state.get_data()
    vols = await db.get_volumes()
    if not vols: await msg.answer("⚠️ Сначала создайте объемы в разделе 'объемы >'"); return
    await safe_edit(bot, data["chat_id"], data["msg_id"], "📏 Выберите объемы:", admin_toggle_volumes_kb(vols, []))
    await state.update_data({"selected_vols": [], "vol_idx": 0, "vol_prices": {}})
    try: await msg.delete()
    except: pass

@router.callback_query(F.data.startswith("vol_toggle_"))
async def toggle_vol(call: CallbackQuery, state: FSMContext, bot: Bot):
    vid = int(call.data.split("_")[-1])
    data = await state.get_data()
    sel = data.get("selected_vols", [])
    if vid in sel: sel.remove(vid)
    else: sel.append(vid)
    await state.update_data({"selected_vols": sel})
    vols = await db.get_volumes()
    await call.message.edit_reply_markup(reply_markup=admin_toggle_volumes_kb(vols, sel))
    await call.answer()

@router.callback_query(F.data == "vol_confirm")
async def confirm_vols(call: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    if not data.get("selected_vols"): return await call.answer("⚠️ Выберите хотя бы один объем", show_alert=True)
    await state.set_state(AdminFSM.add_drink_prices)
    vols = await db.get_volumes_by_ids(data["selected_vols"])
    await state.update_data({"vol_list": vols})
    await safe_edit(bot, call.from_user.id, call.message.message_id, f"💰 Введите цену для: {vols[0]['name']}", back_kb("admin_add_drink"))
    await call.answer()

@router.message(AdminFSM.add_drink_prices)
async def proc_price(msg: Message, state: FSMContext, bot: Bot):
    if not re.match(r"^\d+(\.\d+)?$", msg.text.strip()): return await msg.answer("❌ Введите число")
    data = await state.get_data()
    vol = data["vol_list"][data.get("vol_idx", 0)]
    data["vol_prices"][vol["id"]] = float(msg.text.strip())
    data["vol_idx"] = data.get("vol_idx", 0) + 1
    
    if data["vol_idx"] >= len(data["vol_list"]):
        await db.add_item(1, data["drink_name"], "drink", json.dumps(data["vol_prices"]))
        await state.set_state(AdminFSM.main)
        await safe_edit(bot, msg.chat.id, data["msg_id"], "✅ Напиток сохранён!", admin_main_kb())
    else:
        next_vol = data["vol_list"][data["vol_idx"]]
        await safe_edit(bot, msg.chat.id, data["msg_id"], f"💰 Введите цену для: {next_vol['name']}", back_kb("admin_add_drink"))
    try: await msg.delete()
    except: pass

# 📏 Управление объемами
@router.callback_query(F.data == "admin_volumes")
async def open_vols(call: CallbackQuery, bot: Bot):
    vols = await db.get_volumes()
    await call.message.edit_text("админ-панель\nраздел: объемы", reply_markup=admin_volumes_kb(vols))
    await call.answer()

@router.callback_query(F.data == "admin_create_vol")
async def create_vol(call: CallbackQuery, state: FSMContext, bot: Bot):
    await state.set_state(AdminFSM.add_vol_name)
    await state.update_data({"chat_id": call.from_user.id, "msg_id": call.message.message_id})
    await safe_edit(bot, call.from_user.id, call.message.message_id, "📏 Введите название объема (напр. 300мл):", back_kb("admin_volumes"))
    await call.answer()

@router.message(AdminFSM.add_vol_name)
async def save_vol(msg: Message, state: FSMContext, bot: Bot):
    await db.add_volume(msg.text.strip())
    data = await state.get_data()
    await state.set_state(AdminFSM.main)
    await safe_edit(bot, msg.chat.id, data["msg_id"], "✅ Объем создан!", admin_main_kb())
    try: await msg.delete()
    except: pass

@router.callback_query(F.data == "admin_cancel")
async def cancel(call: CallbackQuery, state: FSMContext, bot: Bot):
    await state.set_state(AdminFSM.main)
    await safe_edit(bot, call.from_user.id, call.message.message_id, "❌ Отменено", admin_main_kb())
    await call.answer()
