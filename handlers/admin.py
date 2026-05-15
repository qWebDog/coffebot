import re
import logging
from datetime import datetime
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramBadRequest
from keyboards.admin import (
    admin_main_kb, admin_menu_kb, admin_extras_kb, admin_categories_kb,
    admin_items_list_kb, admin_edit_item_kb, admin_confirm_kb, admin_sales_kb, back_kb
)
from db.database import db
from config import settings

router = Router()

class AdminFSM(StatesGroup):
    main = State()
    menu = State()
    extras = State()
    add_cat_name = State()
    add_item_cat = State()
    add_item_name = State()
    add_item_volume = State()
    add_item_price = State()
    add_item_confirm = State()
    edit_item_wait = State()
    upd_photo = State()
    sales = State()

def is_admin(uid: int) -> bool:
    return str(uid) in [x.strip() for x in settings.admin_ids.split(",") if x.strip()]

async def safe_edit(bot: Bot, chat_id: int, msg_id: int, text: str, kb=None, parse_mode="HTML"):
    try:
        await bot.edit_message_text(text=text, chat_id=chat_id, message_id=msg_id, reply_markup=kb, parse_mode=parse_mode)
    except TelegramBadRequest:
        pass

@router.message(Command("admin"))
async def cmd_admin(msg: Message, state: FSMContext, bot: Bot):
    if not is_admin(msg.from_user.id):
        return await msg.answer("🚫 Доступ запрещён")

    # ✅ 1. Отправляем НОВОЕ сообщение от имени бота
    sent = await msg.answer("админ-панель", reply_markup=admin_main_kb())

    # ✅ 2. Сохраняем в состоянии ID ИМЕННО ЭТОГО сообщения
    await state.set_state(AdminFSM.main)
    await state.update_data({"chat_id": msg.chat.id, "msg_id": sent.message_id})

@router.callback_query(F.data == "admin_main")
async def back_main(call: CallbackQuery, state: FSMContext, bot: Bot):
    await state.set_state(AdminFSM.main)
    await safe_edit(bot, call.from_user.id, call.message.message_id, "админ-панель", admin_main_kb())
    await call.answer()

@router.callback_query(F.data == "admin_menu")
async def open_menu(call: CallbackQuery, state: FSMContext, bot: Bot):
    await state.set_state(AdminFSM.menu)
    await safe_edit(bot, call.from_user.id, call.message.message_id, "админ-панель\nраздел: меню", admin_menu_kb())
    await call.answer()

@router.callback_query(F.data == "admin_extras")
async def open_extras(call: CallbackQuery, state: FSMContext, bot: Bot):
    await state.set_state(AdminFSM.extras)
    await safe_edit(bot, call.from_user.id, call.message.message_id, "админ-панель\nраздел: дополнительно", admin_extras_kb())
    await call.answer()

# 📸 Обновить фото меню
@router.callback_query(F.data == "admin_upd_order_photo")
async def upd_photo_start(call: CallbackQuery, state: FSMContext, bot: Bot):
    await state.set_state(AdminFSM.upd_photo)
    await safe_edit(bot, call.from_user.id, call.message.message_id, "📸 Отправьте фото для /start:", back_kb("admin_menu"))
    await call.answer()

@router.message(AdminFSM.upd_photo, F.photo)
async def upd_photo_save(msg: Message, state: FSMContext, bot: Bot):
    await db.set_setting("menu_photo", msg.photo[-1].file_id)
    data = await state.get_data()
    await safe_edit(bot, msg.chat.id, data["msg_id"], "✅ Фото меню обновлено!\nраздел: меню", admin_menu_kb())
    try: await msg.delete()
    except: pass

# 📂 Добавить категорию
@router.callback_query(F.data == "admin_add_cat")
async def add_cat_start(call: CallbackQuery, state: FSMContext, bot: Bot):
    await state.set_state(AdminFSM.add_cat_name)
    await safe_edit(bot, call.from_user.id, call.message.message_id, "📂 Введите название новой категории:", back_kb("admin_menu"))
    await call.answer()

@router.message(AdminFSM.add_cat_name)
async def add_cat_save(msg: Message, state: FSMContext, bot: Bot):
    try:
        await db.conn.execute("INSERT INTO categories (name) VALUES (?)", (msg.text.strip(),))
        await db.conn.commit()
        data = await state.get_data()
        await safe_edit(bot, msg.chat.id, data["msg_id"], f"✅ Категория '{msg.text.strip()}' добавлена!\nраздел: меню", admin_menu_kb())
    except: await msg.answer("❌ Категория уже существует")
    try: await msg.delete()
    except: pass

# 🍹/🥐 Универсальный поток добавления (тип сохраняется в state)
async def _start_add_item(call: CallbackQuery, state: FSMContext, bot: Bot, item_type: str, title: str, back_cb: str):
    cats = await db.get_categories()
    if not cats:
        await call.answer("⚠️ Сначала добавьте категорию!", show_alert=True)
        return
    await state.update_data({"item_type": item_type, "add_back_cb": back_cb})
    await state.set_state(AdminFSM.add_item_cat)
    await safe_edit(bot, call.from_user.id, call.message.message_id, f"🥤 Выберите категорию для {title}:", admin_categories_kb(cats))
    await call.answer()

@router.callback_query(F.data == "admin_add_drink")
async def add_drink_start(call: CallbackQuery, state: FSMContext, bot: Bot):
    await _start_add_item(call, state, bot, 'drink', 'напитка', 'admin_menu')

@router.callback_query(F.data == "admin_add_extra")
async def add_extra_start(call: CallbackQuery, state: FSMContext, bot: Bot):
    await _start_add_item(call, state, bot, 'extra', 'дополнения', 'admin_extras')

@router.callback_query(F.data.startswith("admin_sel_cat_"))
async def add_item_name(call: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    cat_id = int(call.data.split("_")[-1])
    await state.update_data({"cat_id": cat_id, "chat_id": call.from_user.id, "msg_id": call.message.message_id})
    await state.set_state(AdminFSM.add_item_name)
    await safe_edit(bot, call.from_user.id, call.message.message_id, "📝 Введите название:", back_kb(data.get("add_back_cb", "admin_main")))
    await call.answer()

@router.message(AdminFSM.add_item_name)
async def proc_name(msg: Message, state: FSMContext, bot: Bot):
    await state.update_data({"item_name": msg.text.strip()})
    await state.set_state(AdminFSM.add_item_volume)
    data = await state.get_data()
    await safe_edit(bot, data["chat_id"], data["msg_id"], "📏 Введите объем (напр. 300мл):", back_kb(data.get("add_back_cb", "admin_main")))
    try: await msg.delete()
    except: pass

@router.message(AdminFSM.add_item_volume)
async def proc_volume(msg: Message, state: FSMContext, bot: Bot):
    await state.update_data({"item_volume": msg.text.strip()})
    await state.set_state(AdminFSM.add_item_price)
    data = await state.get_data()
    await safe_edit(bot, data["chat_id"], data["msg_id"], "💰 Введите цену (число):", back_kb(data.get("add_back_cb", "admin_main")))
    try: await msg.delete()
    except: pass

@router.message(AdminFSM.add_item_price)
async def proc_price(msg: Message, state: FSMContext, bot: Bot):
    if not re.match(r"^\d+(\.\d+)?$", msg.text.strip()):
        return await msg.answer("❌ Введите корректное число")
    await state.update_data({"item_price": float(msg.text.strip())})
    await state.set_state(AdminFSM.add_item_confirm)
    data = await state.get_data()
    preview = f"📋 Проверка:\n• Название: {data['item_name']}\n• Объем: {data['item_volume']}\n• Цена: {data['item_price']}₽"
    await safe_edit(bot, msg.chat.id, data["msg_id"], preview, admin_confirm_kb())
    try: await msg.delete()
    except: pass

@router.callback_query(F.data == "admin_save_drink")
async def save_item(call: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    await db.add_menu_item(data["cat_id"], data["item_name"], data["item_price"], data["item_volume"], item_type=data["item_type"])
    back_cb = data.get("add_back_cb", "admin_main")
    await state.set_state(AdminFSM.main)
    await safe_edit(bot, call.from_user.id, call.message.message_id, "✅ Сохранено!\nадмин-панель", admin_main_kb())
    await call.answer()

@router.callback_query(F.data == "admin_cancel_drink")
async def cancel_item(call: CallbackQuery, state: FSMContext, bot: Bot):
    await state.set_state(AdminFSM.main)
    await safe_edit(bot, call.from_user.id, call.message.message_id, "❌ Отменено.\nадмин-панель", admin_main_kb())
    await call.answer()

# ✏️ Редактирование напитков и дополнений
async def _open_edit(call: CallbackQuery, state: FSMContext, bot: Bot, item_type: str, title: str, back_cb: str):
    items = await db.get_menu_items(item_type)
    if not items:
        await call.answer("⚠️ Пусто", show_alert=True)
        return
    await state.update_data({"edit_type": item_type, "edit_back_cb": back_cb})
    await safe_edit(bot, call.from_user.id, call.message.message_id, f"✏️ Редактирование: {title}", admin_items_list_kb(items, back_cb))
    await call.answer()

@router.callback_query(F.data == "admin_edit_drinks")
async def edit_drinks(call: CallbackQuery, state: FSMContext, bot: Bot):
    await _open_edit(call, state, bot, 'drink', 'напитки', 'admin_menu')

@router.callback_query(F.data == "admin_edit_extras")
async def edit_extras(call: CallbackQuery, state: FSMContext, bot: Bot):
    await _open_edit(call, state, bot, 'extra', 'дополнения', 'admin_extras')

@router.callback_query(F.data.startswith("admin_edit_item_"))
async def select_item(call: CallbackQuery, state: FSMContext, bot: Bot):
    item_id = int(call.data.split("_")[-1])
    await state.update_data({"edit_id": item_id, "chat_id": call.from_user.id, "msg_id": call.message.message_id})
    data = await state.get_data()
    await safe_edit(bot, call.from_user.id, call.message.message_id, "🛠 Выберите поле:", admin_edit_item_kb(item_id, data.get("edit_back_cb", "admin_main")))
    await call.answer()

@router.callback_query(F.data.startswith("admin_upd_"))
async def prompt_field(call: CallbackQuery, state: FSMContext, bot: Bot):
    field = call.data.split("_")[2]
    await state.update_data({"edit_field": field})
    await state.set_state(AdminFSM.edit_item_wait)
    data = await state.get_data()
    prompts = {"name": "📝 Новое название:", "price": "💰 Новая цена:", "volume": "📏 Новый объем:"}
    await safe_edit(bot, call.from_user.id, call.message.message_id, prompts.get(field, "Введите значение:"), back_kb(data.get("edit_back_cb", "admin_main")))
    await call.answer()

@router.message(AdminFSM.edit_item_wait)
async def apply_edit(msg: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    field, item_id = data["edit_field"], data["edit_id"]
    if field == "price":
        if not re.match(r"^\d+(\.\d+)?$", msg.text.strip()): return await msg.answer("❌ Число!")
        val = float(msg.text.strip())
    else:
        val = msg.text.strip()
    await db.update_menu_item(item_id, field, val)
    items = await db.get_menu_items(data["edit_type"])
    await safe_edit(bot, msg.chat.id, data["msg_id"], "✅ Обновлено!", admin_items_list_kb(items, data["edit_back_cb"]))
    try: await msg.delete()
    except: pass

@router.callback_query(F.data.startswith("admin_del_item_"))
async def delete_item(call: CallbackQuery, state: FSMContext, bot: Bot):
    item_id = int(call.data.split("_")[-1])
    await db.delete_menu_item(item_id)
    data = await state.get_data()
    items = await db.get_menu_items(data["edit_type"])
    kb = admin_items_list_kb(items, data["edit_back_cb"]) if items else back_kb(data["edit_back_cb"])
    await safe_edit(bot, call.from_user.id, call.message.message_id, "🗑 Удалено!", kb)
    await call.answer()

# 📊 Продажи
@router.callback_query(F.data == "admin_sales")
async def open_sales(call: CallbackQuery, state: FSMContext, bot: Bot):
    await state.set_state(AdminFSM.sales)
    await safe_edit(bot, call.from_user.id, call.message.message_id, "админ-панель\nраздел: продажи", admin_sales_kb())
    await call.answer()

@router.callback_query(F.data.startswith("admin_stats_"))
async def show_stats(call: CallbackQuery, bot: Bot):
    period = call.data.split("_")[-1]
    now = datetime.now()
    start = now.replace(hour=0, minute=0, second=0) if period == "today" else now.replace(day=1, hour=0, minute=0, second=0)
    stats = await db.get_sales_stats(start.strftime("%Y-%m-%d %H:%M:%S"), now.strftime("%Y-%m-%d %H:%M:%S"))
    count = sum(r[1] for r in stats)
    total = sum(r[2] for r in stats)
    text = f"📊 Статистика: {period}\n📦 Заказов: {count}\n💰 Сумма: {int(total)}₽"
    await call.message.edit_text(text, reply_markup=back_kb("admin_sales"))
    await call.answer()
