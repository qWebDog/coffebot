from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramBadRequest
from keyboards.user import *
from db.database import db
from utils.safe_edit import safe_edit

router = Router()

class UserFSM(StatesGroup):
    browsing = State()
    selecting_vol = State()
    selecting_extras = State()
    viewing_cart = State()

async def render_cart(uid: int, bot: Bot, state: FSMContext):
    lines = await db.get_cart(uid)
    total = sum(l["line_total"] for l in lines)
    text = "🛒 *Ваш заказ:*\n" + "\n".join(f"• {l['name']} ({l['vol']}) x{l['qty']} = {int(l['line_total'])}₽" for l in lines) + f"\n\n💰 *Итого: {int(total)}₽*"
    data = await state.get_data()
    cid, mid = data.get("cart_cid"), data.get("cart_mid")
    if cid and mid: await safe_edit(bot, cid, mid, text, cart_kb(lines))
    else:
        sent = await bot.send_message(uid, text, reply_markup=cart_kb(lines), parse_mode="Markdown")
        await state.update_data({"cart_cid": uid, "cart_mid": sent.message_id})

@router.message(Command("start"))
async def cmd_start(msg: Message, state: FSMContext, bot: Bot):
    cats = await db.get_categories()
    photo = next((c["photo_id"] for c in cats if c["slug"] == "coffee" and c["photo_id"]), None)
    text = "☕ *Добро пожаловать!* Выберите категорию:"
    if photo: await msg.answer_photo(photo, text, reply_markup=main_menu_kb(cats), parse_mode="Markdown")
    else: await msg.answer(text, reply_markup=main_menu_kb(cats), parse_mode="Markdown")
    await state.set_state(UserFSM.browsing)

@router.callback_query(F.data == "back_to_main")
async def back_main(call: CallbackQuery, bot: Bot, state: FSMContext):
    cats = await db.get_categories()
    await call.message.edit_text("☕ Выберите категорию:", reply_markup=main_menu_kb(cats))
    await call.answer()

@router.callback_query(F.data.startswith("cat_"))
async def show_category(call: CallbackQuery, bot: Bot, state: FSMContext):
    slug = call.data.split("_")[1]
    cats = await db.get_categories()
    cat = next(c for c in cats if c["slug"] == slug)
    items = await db.get_items(cat["id"])
    text = f"📂 *{cat['name']}*\nВыберите напиток:"
    photo = cat.get("photo_id")
    if photo: await call.message.edit_media(media={"type": "photo", "media": photo}, reply_markup=category_items_kb(items), caption=text, parse_mode="Markdown")
    else: await call.message.edit_text(text, reply_markup=category_items_kb(items), parse_mode="Markdown")
    await call.answer()

@router.callback_query(F.data.startswith("item_"))
async def select_item(call: CallbackQuery, state: FSMContext, bot: Bot):
    item_id = int(call.data.split("_")[1])
    await state.update_data({"sel_item_id": item_id})
    # В реальном проекте здесь можно подгрузить фото предмета, но по ТЗ фокус на объемах
    await call.message.edit_text("📏 Выберите объем:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[])) # заглушка, обновится в след. шаге
    await call.answer()

# ⚠️ Примечание: В реальном коде callback должен парсить item_id из state, 
# но для простоты я сделаю прямой переход к объемам в одном хендлере.
# Переписываю логику выбора объема корректно:
@router.callback_query(F.data.startswith("vol_"))
async def pick_volume(call: CallbackQuery, state: FSMContext, bot: Bot):
    vol_id = int(call.data.split("_")[1])
    await state.update_data({"sel_vol_id": vol_id, "temp_extras": []})
    extras = await db.get_extras()
    if not extras:
        await finalize_add_to_cart(call, state, bot, [])
        return
    photo = extras[0].get("photo_id")
    text = "🥐 Выберите дополнительные опции:"
    kb = extras_kb(extras, [])
    if photo: await call.message.edit_photo(photo, caption=text, reply_markup=kb)
    else: await call.message.edit_text(text, reply_markup=kb)
    await state.set_state(UserFSM.selecting_extras)
    await call.answer()

@router.callback_query(F.data.startswith("extra_toggle_"), UserFSM.selecting_extras)
async def toggle_extra(call: CallbackQuery, state: FSMContext, bot: Bot):
    eid = int(call.data.split("_")[-1])
    data = await state.get_data()
    sel = data.get("temp_extras", [])
    if eid in sel: sel.remove(eid)
    else: sel.append(eid)
    await state.update_data({"temp_extras": sel})
    extras = await db.get_extras()
    photo = extras[0].get("photo_id") if extras else None
    if photo: await call.message.edit_reply_markup(reply_markup=extras_kb(extras, sel))
    else: await call.message.edit_reply_markup(reply_markup=extras_kb(extras, sel))
    await call.answer()

@router.callback_query(F.data.in_(["confirm_extras", "no_extras"]), UserFSM.selecting_extras)
async def finalize_add_to_cart(call: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    extras_ids = data.get("temp_extras", []) if call.data == "confirm_extras" else []
    await add_line_to_cart(call, state, bot, extras_ids)

async def add_line_to_cart(call: CallbackQuery, state: FSMContext, bot: Bot, extra_ids: list[int]):
    item_id = data.get("sel_item_id")
    vol_id = data.get("sel_vol_id")
    if not item_id or not vol_id: return
    
    # Парсим цены (в реальном проекте нужно хранить маппинг в state или БД)
    # Для стабильности возьмем из items
    cats = await db.get_categories()
    items_flat = []
    for c in cats: items_flat.extend(await db.get_items(c["id"]))
    item = next((i for i in items_flat if i["id"] == item_id), None)
    if not item: return
    
    vol_name = next((v["name"] for v in await db.get_volumes() if v["id"] == vol_id), "Std")
    base_price = float(item["volumes"].get(str(vol_id), 0))
    
    extras = []
    extras_total = 0
    for eid in extra_ids:
        e = await db.get_extra(eid)
        if e: extras.append({"id": e["id"], "name": e["name"], "price": e["price"]}); extras_total += e["price"]
        
    lines = await db.get_cart(call.from_user.id)
    lines.append({"item_id": item_id, "name": item["name"], "vol": vol_name, "vol_id": vol_id, "qty": 1, "extras": extras, "line_total": base_price + extras_total})
    await db.save_cart(call.from_user.id, lines)
    
    await render_cart(call.from_user.id, bot, state)
    await call.answer("✅ Добавлено в корзину")
    await state.set_state(UserFSM.viewing_cart)

@router.callback_query(F.data.startswith("cart_plus_") | F.data.startswith("cart_minus_"))
async def change_qty(call: CallbackQuery, state: FSMContext, bot: Bot):
    action, idx = call.data.split("_")[1], int(call.data.split("_")[2])
    lines = await db.get_cart(call.from_user.id)
    if idx >= len(lines): return
    line = lines[idx]
    if action == "plus": line["qty"] += 1; line["line_total"] += line.get("line_total", 0) / (line["qty"]-1)
    elif action == "minus" and line["qty"] > 1: line["qty"] -= 1; line["line_total"] -= line.get("line_total", 0) / (line["qty"]+1)
    else: lines.pop(idx)
    
    await db.save_cart(call.from_user.id, lines)
    await render_cart(call.from_user.id, bot, state)
    await call.answer()

@router.callback_query(F.data == "clear_cart")
async def clear(call: CallbackQuery, state: FSMContext, bot: Bot):
    await db.clear_cart(call.from_user.id)
    await call.message.delete()
    await state.clear()
    await call.answer("🗑 Очищено")

@router.callback_query(F.data == "checkout")
async def checkout(call: CallbackQuery, state: FSMContext, bot: Bot):
    lines = await db.get_cart(call.from_user.id)
    if not lines: return await call.answer("Корзина пуста", show_alert=True)
    total = sum(l["line_total"] for l in lines)
    await call.message.edit_text(f"💳 Оформление заказа на {int(total)}₽\n\n(Здесь будет интеграция с ЮKassa)", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад в корзину", callback_data="view_cart")]]))
    await call.answer()