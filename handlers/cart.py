from aiogram import Router, Bot, F
from aiogram.types import CallbackQuery
from keyboards.cart import cart_keyboard
from utils.safe_edit import safe_edit_message
from db.database import db

router = Router()

@router.callback_query(F.data == "view_cart")
async def view_cart(call: CallbackQuery, bot: Bot):
    cart = await db.get_cart(call.from_user.id)
    if not cart: return await call.answer("Корзина пуста", show_alert=True)
    await safe_edit_message(bot, cart["chat_id"], cart["message_id"], "", cart_keyboard()) # триггер обновления
    await call.answer()

@router.callback_query(F.data == "clear_cart")
async def clear_cart(call: CallbackQuery, bot: Bot):
    await db.clear_cart(call.from_user.id)
    await safe_edit_message(bot, call.from_user.id, call.message.message_id, "🛒 Корзина очищена", cart_keyboard())
    await call.answer()