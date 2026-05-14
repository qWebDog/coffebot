import re
from datetime import datetime, timedelta
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from keyboards.admin import admin_main_kb, admin_items_kb, admin_edit_item_kb
from db.database import db
from utils.safe_edit import safe_edit_message
from config import settings

router = Router()


class AdminFSM(StatesGroup):
    menu = State()
    add_name = State()
    add_price = State()
    add_volume = State()
    add_photo = State()
    edit_select = State()
    edit_wait_value = State()


def is_admin(uid: int) -> bool:
    return str(uid) in settings.admin_ids.split(",")


@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return await message.answer("🚫 Доступ запрещён")
    await state.set_state(AdminFSM.menu)
    await state.update_data({"msg_id": message.message_id, "chat_id": message.chat.id})
    await safe_edit_message(message.bot, message.chat.id, message.message_id, "👨‍💼 Админ-панель", admin_main_kb())


@router.callback_query(F.data == "admin_main")
async def back_to_main(call: CallbackQuery, state: FSMContext, bot: Bot):
    await state.set_state(AdminFSM.menu)
    await safe_edit_message(bot, call.from_user.id, call.message.message_id, "👨‍💼 Админ-панель", admin_main_kb())
    await call.answer()


# ➕ ДОБАВЛЕНИЕ
@router.callback_query(F.data == "admin_add")
async def start_add(call: CallbackQuery, state: FSMContext, bot: Bot):
    await state.set_state(AdminFSM.add_name)
    await state.update_data({"msg_id": call.message.message_id, "chat_id": call.from_user.id})
    await safe_edit_message(bot, call.from_user.id, call.message.message_id, "📝 Введите название напитка:",
                            admin_main_kb())
    await call.answer()


@router.message(AdminFSM.add_name)
async def proc_add_name(msg: Message, state: FSMContext, bot: Bot):
    await state.update_data({"new_name": msg.text})
    await state.set_state(AdminFSM.add_price)
    data = await state.get_data()
    await safe_edit_message(bot, data["chat_id"], data["msg_id"], "💰 Введите цену (число):", admin_main_kb())
    await msg.delete()


@router.message(AdminFSM.add_price)
async def proc_add_price(msg: Message, state: FSMContext, bot: Bot):
    if not re.match(r"^\d+(\.\d+)?$", msg.text):
        return await msg.answer("❌ Введите корректное число")
    await state.update_data({"new_price": float(msg.text)})
    await state.set_state(AdminFSM.add_volume)
    data = await state.get_data()
    await safe_edit_message(bot, data["chat_id"], data["msg_id"], "📏 Введите объем (напр. 300мл):", admin_main_kb())
    await msg.delete()


@router.message(AdminFSM.add_volume)
async def proc_add_volume(msg: Message, state: FSMContext, bot: Bot):
    await state.update_data({"new_volume": msg.text})
    await state.set_state(AdminFSM.add_photo)
    data = await state.get_data()
    await safe_edit_message(bot, data["chat_id"], data["msg_id"], "🖼 Отправьте фото напитка:", admin_main_kb())
    await msg.delete()


@router.message(AdminFSM.add_photo, F.photo)
async def proc_add_photo(msg: Message, state: FSMContext, bot: Bot):
    photo_id = msg.photo[-1].file_id
    data = await state.get_data()
    await db.add_menu_item(data["new_name"], data["new_price"], data["new_volume"], photo_id)
    await state.set_state(AdminFSM.menu)
    await safe_edit_message(bot, msg.chat.id, data["msg_id"], "✅ Напиток добавлен!\n👨‍💼 Админ-панель",
                            admin_main_kb())
    await msg.delete()


# ✏️ РЕДАКТИРОВАНИЕ
@router.callback_query(F.data == "admin_edit_list")
async def edit_list(call: CallbackQuery, state: FSMContext, bot: Bot):
    items = await db.get_menu_items()
    await state.set_state(AdminFSM.edit_select)
    await safe_edit_message(bot, call.from_user.id, call.message.message_id, "✏️ Выберите напиток:",
                            admin_items_kb(items))
    await call.answer()


@router.callback_query(F.data.startswith("admin_edit_"))
async def select_item(call: CallbackQuery, state: FSMContext, bot: Bot):
    item_id = int(call.data.split("_")[-1])
    await state.update_data({"edit_id": item_id, "msg_id": call.message.message_id, "chat_id": call.from_user.id})
    await safe_edit_message(bot, call.from_user.id, call.message.message_id, f"🛠 ID {item_id} | Выберите поле:",
                            admin_edit_item_kb(item_id))
    await call.answer()


@router.callback_query(F.data.startswith("admin_upd_"))
async def select_field(call: CallbackQuery, state: FSMContext, bot: Bot):
    field = call.data.split("_")[2]
    await state.update_data({"edit_field": field})
    await state.set_state(AdminFSM.edit_wait_value)
    prompts = {"name": "📝 Новое название:", "price": "💰 Новая цена:", "volume": "📏 Новый объем:",
               "photo": "🖼 Новое фото:"}
    await safe_edit_message(bot, call.from_user.id, call.message.message_id, prompts.get(field, "Введите значение:"),
                            admin_main_kb())
    await call.answer()


@router.message(AdminFSM.edit_wait_value)
async def proc_edit_value(msg: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    field, item_id = data["edit_field"], data["edit_id"]

    if field == "price":
        if not re.match(r"^\d+(\.\d+)?$", msg.text): return await msg.answer("❌ Число!")
        val = float(msg.text)
    elif field == "photo":
        if not msg.photo: return await msg.answer("❌ Отправьте фото!")
        val = msg.photo[-1].file_id
    else:
        val = msg.text

    await db.update_menu_item(item_id, field, val)
    await state.set_state(AdminFSM.edit_select)
    await safe_edit_message(bot, msg.chat.id, data["msg_id"], "✅ Обновлено! Выберите напиток:",
                            admin_items_kb(await db.get_menu_items()))
    await msg.delete()


@router.callback_query(F.data.startswith("admin_del_"))
async def delete_item(call: CallbackQuery, state: FSMContext, bot: Bot):
    item_id = int(call.data.split("_")[-1])
    await db.delete_menu_item(item_id)
    await safe_edit_message(bot, call.from_user.id, call.message.message_id, "🗑 Удалено! Выберите напиток:",
                            admin_items_kb(await db.get_menu_items()))
    await call.answer()


# 📊 СТАТИСТИКА
@router.callback_query(F.data.startswith("admin_stats_"))
async def show_stats(call: CallbackQuery, state: FSMContext, bot: Bot):
    period = call.data.split("_")[-1]
    now = datetime.now()
    if period == "today":
        start, end = now.replace(hour=0, minute=0, second=0), now
    elif period == "month":
        start = now.replace(day=1, hour=0, minute=0, second=0);
        end = now
    else:
        start, end = now - timedelta(days=7), now

    stats = await db.get_sales_stats(start.strftime("%Y-%m-%d %H:%M:%S"), end.strftime("%Y-%m-%d %H:%M:%S"))
    text = f"📊 Статистика ({period}):\n\n"
    total_rev = total_ord = 0
    if not stats: text += "Нет продаж."
    for day, orders, rev in stats:
        text += f"📅 {day}: {orders} зак. | {rev}₽\n"
        total_rev += rev;
        total_ord += orders
    if stats: text += f"\n💰 Итого: {total_rev}₽\n📦 Заказов: {total_ord}"

    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="admin_main")]])
    await safe_edit_message(bot, call.from_user.id, call.message.message_id, text, kb)
    await call.answer()

@router.callback_query(F.data.startswith("adm_ready_"))
async def mark_order_ready(call: CallbackQuery, bot: Bot):
    order_id = call.data.split("_")[-1]

    # Обновляем статус
    await db.update_order_status(order_id, "ready")

    # Редактируем сообщение уведомления
    new_text = f"{call.message.text}\n\n✅ <b>Статус: Готов к выдаче</b>"
    await bot.edit_message_text(
        text=new_text,
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=None,
        parse_mode="HTML"
    )

    # Опционально: уведомить клиента
    order = await db.get_order(order_id)
    try:
        await bot.send_message(
            order["user_id"],
            f"🎉 Ваш заказ {order_id} готов! Можете забирать."
        )
    except Exception:
        pass  # Бот заблокирован или пользователь удалил чат

    await call.answer("✅ Заказ отмечен как готовый")