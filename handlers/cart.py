import logging
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from keyboards.cart import cart_keyboard
from db.database import db
from services.yookassa import create_payment
from utils.safe_edit import safe_edit_message

router = Router()

async def render_cart(user_id: int, bot: Bot, is_checkout: bool = False):
    """Универсальная отрисовка/обновление сообщения корзины"""
    cart = await db.get_cart(user_id)
    if not cart or not cart["items"]:
        return

    menu = await db.get_menu_items()
    items, total, chat_id, msg_id = cart["items"], cart["total"], cart["chat_id"], cart["message_id"]

    text = "🛒 *Ваш заказ:*\n\n"
    for item_id_str, qty in items.items():
        try:
            item_id = int(item_id_str)
            item = next((m for m in menu if m["id"] == item_id), None)
            if item:
                text += f"• {item['name']} ({item['volume']}) × {qty} = {int(item['price'])*qty}₽\n"
        except: continue
    text += f"\n💰 *Итого: {int(total)}₽*"

    kb = cart_keyboard(items, menu, is_checkout=is_checkout)
    await safe_edit_message(bot, chat_id, msg_id, text, kb)

@router.callback_query(F.data.startswith("cart_plus_") | F.data.startswith("cart_minus_"))
async def change_qty(call: CallbackQuery, bot: Bot, state: FSMContext):
    user_id = call.from_user.id
    action, item_id_str = call.data.split("_")[1], call.data.split("_")[2]
    item_id = int(item_id_str)

    cart = await db.get_cart(user_id)
    if not cart: return await call.answer("⚠️ Корзина не найдена", show_alert=True)

    menu = await db.get_menu_items()
    item = next((m for m in menu if m["id"] == item_id), None)
    if not item: return await call.answer("⚠️ Товар удалён", show_alert=True)

    items = cart["items"]
    if action == "plus":
        items[item_id_str] = items.get(item_id_str, 0) + 1
    elif action == "minus":
        if items[item_id_str] > 1:
            items[item_id_str] -= 1
        else:
            del items[item_id_str]

    total = sum(next(m["price"] for m in menu if m["id"] == int(i)) * q for i, q in items.items())
    await db.save_cart(user_id, items, total, cart["chat_id"], cart["message_id"])
    await call.answer()
    await render_cart(user_id, bot, is_checkout=False)

@router.callback_query(F.data == "cart_clear")
async def clear_cart(call: CallbackQuery, bot: Bot, state: FSMContext):
    await db.clear_cart(call.from_user.id)
    await call.answer("🗑 Корзина очищена")
    try: await call.message.delete()
    except: pass

@router.callback_query(F.data == "cart_checkout")
async def checkout(call: CallbackQuery, bot: Bot, state: FSMContext):
    cart = await db.get_cart(call.from_user.id)
    if not cart or not cart["items"]:
        return await call.answer("Корзина пуста", show_alert=True)
    await render_cart(call.from_user.id, bot, is_checkout=True)
    await call.answer()

@router.callback_query(F.data == "cart_back")
async def back_to_cart(call: CallbackQuery, bot: Bot, state: FSMContext):
    await render_cart(call.from_user.id, bot, is_checkout=False)
    await call.answer()

@router.callback_query(F.data == "cart_pay")
async def pay_order(call: CallbackQuery, bot: Bot, state: FSMContext):
    user_id = call.from_user.id
    cart = await db.get_cart(user_id)
    if not cart: return await call.answer("Ошибка: корзина пуста", show_alert=True)

    menu = await db.get_menu_items()
    order_id, url = create_payment(cart["total"], cart["items"], menu, user_id)
    username = call.from_user.username or f"user_{user_id}"
    
    await db.create_order(order_id, user_id, cart["items"], cart["total"], username)
    await db.clear_cart(user_id)  # ✅ Очищаем корзину только после создания заказа

    # Обновляем сообщение корзины на статус
    await safe_edit_message(bot, cart["chat_id"], cart["message_id"], 
                            "✅ Заказ создан! Перейдите по ссылке ниже для оплаты.",
                            InlineKeyboardMarkup(inline_keyboard=[[
                                InlineKeyboardButton(text="💳 Оплатить", url=url)
                            ]]))
    await call.answer()
