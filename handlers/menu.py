from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from keyboards.menu import menu_keyboard, extras_keyboard
from keyboards.cart import cart_keyboard
from handlers.cart import render_cart
from db.database import db

router = Router()

@router.callback_query(F.data == "view_extras")
async def show_extras(call: CallbackQuery, bot: Bot):
    extras = await db.get_menu_items(item_type='extra')
    if not extras:
        return await call.answer("⚠️ Дополнительных позиций пока нет", show_alert=True)
    await call.message.edit_text("🥐 Выберите дополнение:", reply_markup=extras_keyboard(extras))
    await call.answer()

@router.callback_query(F.data == "view_extras_back")
async def back_to_menu(call: CallbackQuery, bot: Bot):
    drinks = await db.get_menu_items(item_type='drink')
    await call.message.edit_text("☕ Выберите напиток:", reply_markup=menu_keyboard(drinks))
    await call.answer()

@router.callback_query(F.data.startswith("add_"))
async def add_item(call: CallbackQuery, bot: Bot, state: FSMContext):
    raw_id = call.data.split("_", 1)[-1]
    try:
        item_id = int(raw_id)
    except ValueError:
        return await call.answer("⚠️ Ошибка формата", show_alert=True)

    # Ищем и в напитках, и в дополнениях
    menu_all = await db.get_menu_items('drink') + await db.get_menu_items('extra')
    item = next((m for m in menu_all if m["id"] == item_id), None)
    if not item:
        return await call.answer("⚠️ Товар удалён", show_alert=True)

    user_id = call.from_user.id
    cart = await db.get_cart(user_id)
    items = cart["items"] if cart else {}
    items[str(item_id)] = items.get(str(item_id), 0) + 1

    total = sum(next(m["price"] for m in menu_all if m["id"] == int(i)) * q for i, q in items.items())

    if not cart:
        sent = await call.message.answer("🛒 *Ваш заказ:*", reply_markup=cart_keyboard(items, menu_all), parse_mode="Markdown")
        await db.save_cart(user_id, items, total, call.from_user.id, sent.message_id)
    else:
        await db.save_cart(user_id, items, total, cart["chat_id"], cart["message_id"])

    await call.answer(f"➕ {item['name']} добавлен")
    await render_cart(user_id, bot, is_checkout=False)
