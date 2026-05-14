from aiogram import Router, Bot, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from keyboards.menu import MENU
from db.database import db
from services.yookassa import create_payment

router = Router()

@router.callback_query(F.data == "pay")
async def process_payment(call: CallbackQuery, bot: Bot):
    cart = await db.get_cart(call.from_user.id)
    if not cart: return await call.answer("Нечего оплачивать", show_alert=True)

    order_id, url = create_payment(cart["total"], cart["items"], MENU, call.from_user.id)
    username = call.from_user.username or f"user_{call.from_user.id}"
    await db.create_order(order_id, call.from_user.id, cart["items"], cart["total"], username)

    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="💳 Оплатить", url=url)]])
    await call.message.answer(f"🔗 Перейдите для оплаты {int(cart['total'])}₽:", reply_markup=kb)
    await call.answer()