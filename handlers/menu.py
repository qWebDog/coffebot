from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from keyboards.menu import menu_keyboard
from keyboards.cart import cart_keyboard
from utils.safe_edit import safe_edit_message
from db.database import db

router = Router()

@router.callback_query(F.data.startswith("add_"))
async def add_item(call: CallbackQuery, bot: Bot, state: FSMContext):
    raw_id = call.data.split("_", 1)[-1]
    try:
        item_id = int(raw_id)
    except ValueError:
        return await call.answer("⚠️ Ошибка формата товара", show_alert=True)

    menu = await db.get_menu_items()
    item = next((m for m in menu if m["id"] == item_id), None)
    
    if not item:
        return await call.answer("⚠️ Товар удалён или не найден", show_alert=True)


    cart = await db.get_cart(call.from_user.id)
    items = cart["items"] if cart else {}
    items[str(item_id)] = items.get(str(item_id), 0) + 1
    

    total = sum(
        next(m["price"] for m in menu if m["id"] == int(i)) * q
        for i, q in items.items()
    )

    if not cart:
        sent = await call.message.answer("🛒 Корзина", reply_markup=cart_keyboard())
        chat_id, msg_id = call.from_user.id, sent.message_id
    else:
        chat_id, msg_id = cart["chat_id"], cart["message_id"]

    await db.save_cart(call.from_user.id, items, total, chat_id, msg_id)
    await call.answer(f"➕ {item['name']} добавлен")
    
    text = "🛒 *Ваш заказ:*\n" + "\n".join(
        f"• {next(m['name'] for m in menu if m['id'] == int(i))} × {q} = "
        f"{int(next(m['price'] for m in menu if m['id'] == int(i)) * q)}₽"
        for i, q in items.items()
    ) + f"\n\n💰 *Итого: {int(total)}₽*"
    
    await safe_edit_message(bot, chat_id, msg_id, text, cart_keyboard())
