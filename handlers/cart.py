from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from keyboards.cart import cart_keyboard
from db.database import db
from services.yookassa import create_payment
from utils.safe_edit import safe_edit_message

router = Router()

async def render_cart(user_id: int, bot: Bot, is_checkout: bool = False):
    cart = await db.get_cart(user_id)
    if not cart or not cart["items"]: return
    extras = await db.get_extras()
    # Пересчёт суммы (в проде лучше хранить total в БД)
    # Для простоты здесь используем заглушку, в реальном проекте парсите цены из БД по имени
    total = 0.0 
    await safe_edit_message(bot, cart["chat_id"], cart["message_id"], "🛒 Ваш заказ:", cart_keyboard(cart["items"], extras, total, is_checkout))

@router.callback_query(F.data.startswith("cart_plus_") | F.data.startswith("cart_minus_"))
async def change_qty(call: CallbackQuery, bot: Bot):
    action, key = call.data.split("_")[1], call.data.split("_", 3)[-1]
    cart = await db.get_cart(call.from_user.id)
    if not cart: return
    items = cart["items"]
    if action == "plus": items[key] = items.get(key, 0) + 1
    elif action == "minus" and items[key] > 1: items[key] -= 1
    else: del items[key]
    
    await db.save_cart(call.from_user.id, items, 0, cart["chat_id"], cart["message_id"])
    await render_cart(call.from_user.id, bot)
    await call.answer()

@router.callback_query(F.data == "cart_clear")
async def clear_cart(call: CallbackQuery, bot: Bot):
    await db.clear_cart(call.from_user.id)
    await call.message.delete()
    await call.answer("🗑 Очищено")

@router.callback_query(F.data == "cart_checkout")
async def checkout(call: CallbackQuery, bot: Bot):
    await render_cart(call.from_user.id, bot, is_checkout=True)
    await call.answer()

@router.callback_query(F.data == "cart_back")
async def back_to_edit(call: CallbackQuery, bot: Bot):
    await render_cart(call.from_user.id, bot, is_checkout=False)
    await call.answer()

@router.callback_query(F.data == "cart_pay")
async def pay(call: CallbackQuery, bot: Bot):
    cart = await db.get_cart(call.from_user.id)
    if not cart: return
    # Здесь вызываете YooKassa, очищаете корзину, отправляете ссылку
    # await db.clear_cart(call.from_user.id)
    await call.answer("⏳ Генерация ссылки...", show_alert=True)
