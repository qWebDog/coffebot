# handlers/admin.py
import re
import logging  # ← Обязательно!
from datetime import datetime
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramBadRequest
from keyboards.admin import (
    admin_main_kb, admin_menu_kb, admin_categories_kb, admin_drinks_kb,
    admin_edit_drink_kb, admin_confirm_kb, admin_sales_kb, back_kb
)
from db.database import db
from config import settings

router = Router()

class AdminFSM(StatesGroup):
    main = State()
    menu = State()
    add_cat_name = State()
    add_drink_cat = State()
    add_drink_name = State()
    add_drink_volume = State()
    add_drink_price = State()
    add_drink_confirm = State()
    upd_order_photo = State()
    edit_drink_wait = State()
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
    await state.set_state(AdminFSM.main)
    await state.update_data({"chat_id": msg.chat.id, "msg_id": msg.message_id})
    await safe_edit(bot, msg.chat.id, msg.message_id, "админ-панель", admin_main_kb())

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

@router.callback_query(F.data == "admin_upd_order_photo")
async def upd_photo_start(call: CallbackQuery, state: FSMContext, bot: Bot):
    await state.set_state(AdminFSM.upd_order_photo)
    await safe_edit(bot, call.from_user.id, call.message.message_id, "📸 Отправьте новое фото для сообщений с заказом:", back_kb("admin_menu"))
    await call.answer()

@router.message(AdminFSM.upd_order_photo, F.photo)
async def upd_photo_save(msg: Message, state: FSMContext, bot: Bot):
    photo_id = msg.photo[-1].file_id
    await db.set_setting("order_preview_photo", photo_id)
    data = await state.get_data()
    await safe_edit(bot, msg.chat.id, data["msg_id"], "✅ Фото заказа обновлено!\nраздел: меню", admin_menu_kb())
    try: await msg.delete()
    except: pass

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
    except Exception:
        await msg.answer("❌ Категория с таким именем уже существует")
    try: await msg.delete()
    except: pass

@router.callback_query(F.data == "admin_add_drink")
async def add_drink_start(call: CallbackQuery, state: FSMContext, bot: Bot):
    cats = await db.get_categories()
    if not cats:
        await call.answer("⚠️ Сначала добавьте категорию!", show_alert=True)
        return
    await state.set_state(AdminFSM.add_drink_cat)
    await safe_edit(bot, call.from_user.id, call.message.message_id, "🥤 Выберите категорию для напитка:", admin_categories_kb(cats))
    await call.answer()

@router.callback_query(F.data.startswith("admin_sel_cat_"))
async def add_drink_name(call: CallbackQuery, state: FSMContext, bot: Bot):
    cat_id = int(call.data.split("_")[-1])
    await state.update_data({"drink_cat_id": cat_id, "chat_id": call.from_user.id, "msg_id": call.message.message_id})
    await state.set_state(AdminFSM.add_drink_name)
    await safe_edit(bot, call.from_user.id, call.message.message_id, "📝 Введите название напитка:", back_kb("admin_add_drink"))
    await call.answer()

@router.message(AdminFSM.add_drink_name)
async def proc_drink_name(msg: Message, state: FSMContext, bot: Bot):
    await state.update_data({"drink_name": msg.text.strip()})
    await state.set_state(AdminFSM.add_drink_volume)
    data = await state.get_data()
    await safe_edit(bot, data["chat_id"], data["msg_id"], "📏 Введите объем (напр. 300мл):", back_kb("admin_add_drink"))
    try: await msg.delete()
    except: pass

@router.message(AdminFSM.add_drink_volume)
async def proc_drink_volume(msg: Message, state: FSMContext, bot: Bot):
    await state.update_data({"drink_volume": msg.text.strip()})
    await state.set_state(AdminFSM.add_drink_price)
    data = await state.get_data()
    await safe_edit(bot, data["chat_id"], data["msg_id"], "💰 Введите цену (число):", back_kb("admin_add_drink"))
    try: await msg.delete()
    except: pass

@router.message(AdminFSM.add_drink_price)
async def proc_drink_price(msg: Message, state: FSMContext, bot: Bot):
    if not re.match(r"^\d+(\.\d+)?$", msg.text.strip()):
        return await msg.answer("❌ Введите корректное число")
    await state.update_data({"drink_price": float(msg.text.strip())})
    await state.set_state(AdminFSM.add_drink_confirm)
    data = await state.get_data()
    preview = (f"🥤 Проверка данных:\n"
               f"• Категория ID: {data['drink_cat_id']}\n"
               f"• Название: {data['drink_name']}\n"
               f"• Объем: {data['drink_volume']}\n"
               f"• Цена: {data['drink_price']}₽")
    await safe_edit(bot, msg.chat.id, data["msg_id"], preview, admin_confirm_kb())
    try: await msg.delete()
    except: pass

@router.callback_query(F.data == "admin_save_drink")
async def save_drink(call: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    await db.add_menu_item(data["drink_cat_id"], data["drink_name"], data["drink_price"], data["drink_volume"])
    await state.set_state(AdminFSM.menu)
    await safe_edit(bot, call.from_user.id, call.message.message_id, "✅ Напиток сохранён!\nраздел: меню", admin_menu_kb())
    await call.answer()

@router.callback_query(F.data == "admin_cancel_drink")
async def cancel_drink(call: CallbackQuery, state: FSMContext, bot: Bot):
    await state.set_state(AdminFSM.menu)
    await safe_edit(bot, call.from_user.id, call.message.message_id, "❌ Отменено.\nраздел: меню", admin_menu_kb())
    await call.answer()

@router.callback_query(F.data == "admin_edit_drinks")
async def open_edit_drinks(call: CallbackQuery, state: FSMContext, bot: Bot):
    drinks = await db.get_menu_items()
    if not drinks:
        await call.answer("⚠️ Меню пусто", show_alert=True)
        return
    await safe_edit(bot, call.from_user.id, call.message.message_id, "✏️ Выберите напиток для редактирования:", admin_drinks_kb(drinks))
    await call.answer()

@router.callback_query(F.data.startswith("admin_edit_drink_"))
async def select_drink_to_edit(call: CallbackQuery, state: FSMContext, bot: Bot):
    item_id = int(call.data.split("_")[-1])
    await state.update_data({"edit_id": item_id, "chat_id": call.from_user.id, "msg_id": call.message.message_id})
    await safe_edit(bot, call.from_user.id, call.message.message_id, "🛠 Выберите поле для изменения:", admin_edit_drink_kb(item_id))
    await call.answer()

@router.callback_query(F.data.startswith("admin_upd_"))
async def prompt_edit_field(call: CallbackQuery, state: FSMContext, bot: Bot):
    field = call.data.split("_")[2]
    await state.update_data({"edit_field": field})
    await state.set_state(AdminFSM.edit_drink_wait)
    prompts = {
        "name": "📝 Введите новое название:",
        "price": "💰 Введите новую цену (число):",
        "volume": "📏 Введите новый объем:"
    }
    await safe_edit(bot, call.from_user.id, call.message.message_id, prompts.get(field, "Введите значение:"), back_kb("admin_edit_drinks"))
    await call.answer()

@router.message(AdminFSM.edit_drink_wait)
async def apply_edit(msg: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    field, item_id = data["edit_field"], data["edit_id"]
    
    if field == "price":
        if not re.match(r"^\d+(\.\d+)?$", msg.text.strip()):
            return await msg.answer("❌ Введите корректное число")
        val = float(msg.text.strip())
    else:
        val = msg.text.strip()

    await db.update_menu_item(item_id, field, val)
    drinks = await db.get_menu_items()
    await safe_edit(bot, msg.chat.id, data["msg_id"], "✅ Поле обновлено!\n✏️ Выберите напиток:", admin_drinks_kb(drinks))
    try: await msg.delete()
    except: pass

@router.callback_query(F.data.startswith("admin_del_drink_"))
async def delete_drink(call: CallbackQuery, state: FSMContext, bot: Bot):
    item_id = int(call.data.split("_")[-1])
    await db.delete_menu_item(item_id)
    drinks = await db.get_menu_items()
    await safe_edit(bot, call.from_user.id, call.message.message_id, "🗑 Удалено!\n✏️ Выберите напиток:", admin_drinks_kb(drinks) if drinks else back_kb("admin_menu"))
    await call.answer()

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
