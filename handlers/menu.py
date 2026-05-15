from aiogram import Router, F, Bot
from aiogram.filters import Command  # ✅ Добавлено
from aiogram.types import CallbackQuery, Message  # ✅ Добавлено
from aiogram.fsm.context import FSMContext
from keyboards.menu import menu_keyboard, volume_keyboard
from keyboards.cart import cart_keyboard, extras_keyboard
from handlers.cart import render_cart
from db.database import db

router = Router()

@router.message(Command("start"))
async def cmd_start(msg: Message, bot: Bot):
    drinks = await db.get_drinks()
    if not drinks: return await msg.answer("📭 Меню пока пусто.")
    photo = await db.get_setting("menu_photo")
    cap = "☕ Выберите напиток:"
    if photo: await msg.answer_photo(photo, cap, reply_markup=menu_keyboard(drinks))
    else: await msg.answer(cap, reply_markup=menu_keyboard(drinks))

@router.callback_query(F.data.startswith("show_vols_"))
async def show_vols(call: CallbackQuery, bot: Bot):
    did = int(call.data.split("_")[-1])
    drinks = await db.get_drinks()
    d = next((x for x in drinks if x["id"] == did), None)
    if d: 
        await call.message.edit_text(f"🥤 {d['name']} - выберите объем:", reply_markup=volume_keyboard(d["id"], d["volumes"]))
    await call.answer()

@router.callback_query(F.data == "back_to_menu")
async def back_menu(call: CallbackQuery, bot: Bot):
    drinks = await db.get_drinks()
    await call.message.edit_text("☕ Выберите напиток:", reply_markup=menu_keyboard(drinks))
    await call.answer()

@router.callback_query(F.data.startswith("add_to_cart_"))
async def add_to_cart(call: CallbackQuery, bot: Bot, state: FSMContext):
    _, did, vid = call.data.split("_")
    did, vid = int(did), int(vid)
    drinks = await db.get_drinks()
    d = next((x for x in drinks if x["id"] == did), None)
    if not d or vid not in d["volumes"]: return await call.answer("⚠️ Ошибка", show_alert=True)
    
    key = f"{d['name']} ({d['volumes'][vid]['name']})"
    
    cart = await db.get_cart(call.from_user.id)
    items = cart["items"] if cart else {}
    items[key] = items.get(key, 0) + 1
    
    # Временный расчет суммы для демонстрации, в проде лучше хранить в БД
    total = sum(100 * q for q in items.values()) 
    
    if not cart:
        sent = await call.message.answer("🛒 Ваш заказ:", reply_markup=cart_keyboard(items, [], 0))
        await db.save_cart(call.from_user.id, items, total, call.from_user.id, sent.message_id)
    else:
        await db.save_cart(call.from_user.id, items, total, cart["chat_id"], cart["message_id"])
    
    await call.answer(f"➕ {key} добавлен")
    await render_cart(call.from_user.id, bot)

@router.callback_query(F.data == "add_extra")
async def show_extras(call: CallbackQuery, bot: Bot):
    extras = await db.get_extras()
    await call.message.edit_text("🥐 Выберите дополнение:", reply_markup=extras_keyboard(extras))
    await call.answer()

@router.callback_query(F.data.startswith("add_extra_"))
async def add_extra(call: CallbackQuery, bot: Bot, state: FSMContext):
    eid = int(call.data.split("_")[-1])
    extras = await db.get_extras()
    e = next((x for x in extras if x["id"] == eid), None)
    if not e: return
    
    key = f"{e['name']} (доп.)"
    
    cart = await db.get_cart(call.from_user.id)
    items = cart["items"] if cart else {}
    items[key] = items.get(key, 0) + 1
    
    total = 100 # Заглушка суммы
    
    if not cart:
        sent = await call.message.answer("🛒 Ваш заказ:", reply_markup=cart_keyboard(items, [], 0))
        await db.save_cart(call.from_user.id, items, total, call.from_user.id, sent.message_id)
    else:
        await db.save_cart(call.from_user.id, items, total, cart["chat_id"], cart["message_id"])
    await call.answer(f"➕ {key} добавлен")
    await render_cart(call.from_user.id, bot)

@router.callback_query(F.data == "back_to_cart")
async def back_cart(call: CallbackQuery, bot: Bot):
    await render_cart(call.from_user.id, bot)
    await call.answer()
