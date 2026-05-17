# handlers/user.py
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message, InputMediaPhoto, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from keyboards.user import *
from db.database import db
from utils.safe_edit import safe_edit

router = Router()

class UserFSM(StatesGroup):
    browsing = State()
    picking_volume = State()
    picking_extras = State()
    viewing_cart = State()

async def render_cart(uid: int, bot: Bot, state: FSMContext):
    lines = await db.get_cart(uid)
    total = sum(l["line_total"] * l["qty"] for l in lines)
    
    text = "🛒 *Ваш заказ:*\n" + "\n".join(
        f"• {l['name']} ({l['vol']}) x{l['qty']} = {int(l['line_total']*l['qty'])}₽" for l in lines
    ) + f"\n\n💰 *Итого: {int(total)}₽*"
    
    data = await state.get_data()
    cid, mid = data.get("cart_cid"), data.get("cart_mid")
    kb = cart_kb(lines)
    
    if cid and mid:
        await safe_edit(bot, cid, mid, text, kb)
    else:
        sent = await bot.send_message(uid, text, reply_markup=kb, parse_mode="Markdown")
        await state.update_data({"cart_cid": uid, "cart_mid": sent.message_id})

@router.message(Command("start"))
async def cmd_start(msg: Message, state: FSMContext, bot: Bot):
    cats = await db.get_categories()
    # ✅ Берём фото из отдельной настройки "menu_photo", а не из категории "coffee"
    menu_photo = await db.get_setting("menu_photo")
    
    text = "☕ *Добро пожаловать!* Выберите категорию:"
    kb = main_menu_kb(cats)
    
    if menu_photo:
        await msg.answer_photo(
            photo=menu_photo,
            caption=text,
            reply_markup=kb,
            parse_mode="Markdown"
        )
    else:
        await msg.answer(
            text=text,
            reply_markup=kb,
            parse_mode="Markdown"
        )
    
    await state.set_state(UserFSM.browsing)
    await state.update_data({"cart_cid": None, "cart_mid": None})

@router.callback_query(F.data == "back_to_main")
async def back_main(call: CallbackQuery, bot: Bot, state: FSMContext):
    cats = await db.get_categories()
    menu_photo = await db.get_setting("menu_photo")
    
    if menu_photo:
        await call.message.edit_media(
            media=InputMediaPhoto(media=menu_photo),
            caption="☕ Выберите категорию:",
            reply_markup=main_menu_kb(cats)
        )
    else:
        await call.message.edit_text(
            "☕ Выберите категорию:",
            reply_markup=main_menu_kb(cats)
        )
    await call.answer()

@router.callback_query(F.data.startswith("cat_"))
async def show_category(call: CallbackQuery, bot: Bot, state: FSMContext):
    # ✅ Исправлен парсинг slug: cat_non_coffee → "non_coffee"
    slug = "_".join(call.data.split("_")[1:])
    cats = await db.get_categories()
    cat = next((c for c in cats if c["slug"] == slug), None)
    
    if not cat:
        return await call.answer(f"❌ Категория '{slug}' не найдена", show_alert=True)
    
    items = await db.get_items(cat["id"])
    text = f"📂 *{cat['name']}*\nВыберите напиток:"
    kb = category_items_kb(items)
    
    if cat.get("photo_id"):
        await call.message.edit_media(
            media=InputMediaPhoto(media=cat["photo_id"]),
            caption=text,
            reply_markup=kb,
            parse_mode="Markdown"
        )
    else:
        await call.message.edit_text(
            text=text,
            reply_markup=kb,
            parse_mode="Markdown"
        )
    await state.update_data({"sel_cat_id": cat["id"]})
    await call.answer()

@router.callback_query(F.data.startswith("item_"))
async def select_item(call: CallbackQuery, state: FSMContext, bot: Bot):
    item_id = int(call.data.split("_")[1])
    cats = await db.get_categories()
    
    item = None
    for c in cats:
        for i in await db.get_items(c["id"]):
            if i["id"] == item_id:
                item = i
                break
    if not item:
        return await call.answer("❌ Товар не найден", show_alert=True)
    
    await state.update_data({"sel_item_id": item_id, "sel_item_name": item["name"], "temp_extras": []})
    vols = item.get("volumes", {})
    if not vols:
        return await call.answer("⚠️ Нет доступных объемов", show_alert=True)
    
    # ✅ Теперь передаём только volumes
    await call.message.edit_text("📏 Выберите объем:", reply_markup=item_volumes_kb(vols))
    await state.set_state(UserFSM.picking_volume)
    await call.answer()

@router.callback_query(F.data.startswith("vol_"), UserFSM.picking_volume)
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
    
    if photo:
        await call.message.edit_media(
            media=InputMediaPhoto(media=photo),
            caption=text,
            reply_markup=kb
        )
    else:
        await call.message.edit_text(text, reply_markup=kb)
    await state.set_state(UserFSM.picking_extras)
    await call.answer()

@router.callback_query(F.data.startswith("extra_toggle_"), UserFSM.picking_extras)
async def toggle_extra(call: CallbackQuery, state: FSMContext, bot: Bot):
    eid = int(call.data.split("_")[-1])
    data = await state.get_data()
    sel = data.get("temp_extras", [])
    if eid in sel:
        sel.remove(eid)
    else:
        sel.append(eid)
    await state.update_data({"temp_extras": sel})
    
    extras = await db.get_extras()
    photo = extras[0].get("photo_id") if extras else None
    kb = extras_kb(extras, sel)
    if photo:
        await call.message.edit_media(media=InputMediaPhoto(media=photo), reply_markup=kb)
    else:
        await call.message.edit_reply_markup(reply_markup=kb)
    await call.answer()

@router.callback_query(F.data.in_(["confirm_extras", "no_extras"]), UserFSM.picking_extras)
async def confirm_extras(call: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    extra_ids = data.get("temp_extras", []) if call.data == "confirm_extras" else []
    await finalize_add_to_cart(call, state, bot, extra_ids)

async def finalize_add_to_cart(call: CallbackQuery, state: FSMContext, bot: Bot, extra_ids: list[int]):
    data = await state.get_data()
    item_id = data.get("sel_item_id")
    vol_id = data.get("sel_vol_id")
    if not item_id or not vol_id:
        return
    
    cats = await db.get_categories()
    item_vols = {}
    item_name = "Напиток"
    for c in cats:
        for i in await db.get_items(c["id"]):
            if i["id"] == item_id:
                item_vols = i.get("volumes", {})
                item_name = i.get("name", "Напиток")
                break
                
    vol_data = item_vols.get(vol_id, {})
    base_price = float(vol_data.get("price", 0))
    vol_name = vol_data.get("name", "Стандарт")
    
    extras = []
    extras_total = 0.0
    all_extras = await db.get_extras()
    for eid in extra_ids:
        e = next((ex for ex in all_extras if ex["id"] == eid), None)
        if e:
            extras.append({"id": e["id"], "name": e["name"], "price": e["price"]})
            extras_total += e["price"]
            
    lines = await db.get_cart(call.from_user.id)
    lines.append({
        "item_id": item_id,
        "name": item_name,
        "vol": vol_name,
        "vol_id": vol_id,
        "qty": 1,
        "extras": extras,
        "line_total": base_price + extras_total
    })
    await db.save_cart(call.from_user.id, lines)
    
    await render_cart(call.from_user.id, bot, state)
    await call.answer("✅ Добавлено в корзину")
    await state.set_state(UserFSM.viewing_cart)

@router.callback_query(F.data.startswith("cart_plus_") | F.data.startswith("cart_minus_"))
async def change_qty(call: CallbackQuery, state: FSMContext, bot: Bot):
    action = call.data.split("_")[1]
    idx = int(call.data.split("_")[2])
    lines = await db.get_cart(call.from_user.id)
    if idx >= len(lines):
        return
    
    line = lines[idx]
    unit_price = line["line_total"] / line["qty"] if line["qty"] > 0 else 0
    
    if action == "plus":
        line["qty"] += 1
    elif action == "minus":
        if line["qty"] > 1:
            line["qty"] -= 1
        else:
            lines.pop(idx)
        
    line["line_total"] = unit_price * line["qty"]
    await db.save_cart(call.from_user.id, lines)
    await render_cart(call.from_user.id, bot, state)
    await call.answer()

@router.callback_query(F.data == "clear_cart")
async def clear_cart(call: CallbackQuery, state: FSMContext, bot: Bot):
    await db.clear_cart(call.from_user.id)
    await call.message.delete()
    await state.clear()
    await call.answer("🗑 Очищено")

@router.callback_query(F.data == "checkout")
async def checkout(call: CallbackQuery, state: FSMContext, bot: Bot):
    lines = await db.get_cart(call.from_user.id)
    if not lines:
        return await call.answer("Корзина пуста", show_alert=True)
    total = sum(l["line_total"] for l in lines)
    await call.message.edit_text(
        f"💳 Оформление заказа на {int(total)}₽\n(Интеграция ЮKassa будет здесь)",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="view_cart")]])
    )
    await call.answer()
