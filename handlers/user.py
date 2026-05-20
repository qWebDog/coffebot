import logging
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message, InputMediaPhoto, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramBadRequest
from keyboards.user import *
from db.database import db
from utils.safe_edit import safe_edit
from zoneinfo import ZoneInfo
from datetime import datetime, timedelta

router = Router()
MSK = ZoneInfo("Europe/Moscow")

class UserFSM(StatesGroup):
    browsing = State()
    picking_volume = State()
    picking_extras = State()
    viewing_cart = State()
    selecting_time = State()
    after_time = State()
    editing_item_extras = State()

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
    menu_photo = await db.get_setting("menu_photo")
    text = "☕ *Добро пожаловать!* Выберите категорию:"
    kb = main_menu_kb(cats)
    if menu_photo: await msg.answer_photo(photo=menu_photo, caption=text, reply_markup=kb, parse_mode="Markdown")
    else: await msg.answer(text=text, reply_markup=kb, parse_mode="Markdown")
    await state.set_state(UserFSM.browsing)
    await state.update_data({"cart_cid": None, "cart_mid": None})

@router.callback_query(F.data == "back_to_main")
async def back_main(call: CallbackQuery, bot: Bot, state: FSMContext):
    cats = await db.get_categories()
    menu_photo = await db.get_setting("menu_photo")
    if menu_photo: await call.message.edit_media(media=InputMediaPhoto(media=menu_photo), caption="☕ Выберите категорию:", reply_markup=main_menu_kb(cats))
    else: await call.message.edit_text("☕ Выберите категорию:", reply_markup=main_menu_kb(cats))
    await call.answer()

@router.callback_query(F.data.startswith("cat_"))
async def show_category(call: CallbackQuery, bot: Bot, state: FSMContext):
    slug = "_".join(call.data.split("_")[1:])
    cats = await db.get_categories()
    cat = next((c for c in cats if c["slug"] == slug), None)
    if not cat: return await call.answer("❌ Категория не найдена", show_alert=True)
    items = await db.get_items(cat["id"])
    text = f"📂 *{cat['name']}*\nВыберите напиток:"
    kb = category_items_kb(items)
    if cat.get("photo_id"): await call.message.edit_media(media=InputMediaPhoto(media=cat["photo_id"]), caption=text, reply_markup=kb, parse_mode="Markdown")
    else: await call.message.edit_text(text=text, reply_markup=kb, parse_mode="Markdown")
    await state.update_data({"sel_cat_id": cat["id"]})
    await call.answer()

@router.callback_query(F.data.startswith("item_"))
async def select_item(call: CallbackQuery, state: FSMContext, bot: Bot):
    item_id = int(call.data.split("_")[1])
    cats = await db.get_categories()
    item = None
    for c in cats:
        for i in await db.get_items(c["id"]):
            if i["id"] == item_id: item = i; break
    if not item: return await call.answer("❌ Товар не найден", show_alert=True)
    await state.update_data({"sel_item_id": item_id, "sel_item_name": item["name"], "temp_extras": []})
    vols = item.get("volumes", {})
    if not vols: return await call.answer("⚠️ Нет доступных объемов", show_alert=True)
    try: await call.message.edit_caption(caption="📏 Выберите объем:", reply_markup=item_volumes_kb(vols))
    except TelegramBadRequest: await call.message.delete(); await call.message.answer("📏 Выберите объем:", reply_markup=item_volumes_kb(vols))
    await state.set_state(UserFSM.picking_volume)
    await call.answer()

@router.callback_query(F.data.startswith("vol_"), UserFSM.picking_volume)
async def pick_volume(call: CallbackQuery, state: FSMContext, bot: Bot):
    vol_id = int(call.data.split("_")[1])
    await state.update_data({"sel_vol_id": vol_id, "temp_extras": []})
    cats = await db.get_categories()
    # Находим цены и имя для финализации
    item_id = call.data.split("_") # заглушка, берем из state
    await state.set_state(UserFSM.picking_extras) # Упрощаем: сразу в допы или в корзину
    await finalize_add_to_cart(call, state, bot, [])
    return

# ⚠️ Упрощенный поток: объем -> сразу в корзину с вопросом про допы
# Но по ТЗ нужно: к каждой позиции можно добавить доп. Реализуем через кнопку в корзине.
async def finalize_add_to_cart(call: CallbackQuery, state: FSMContext, bot: Bot, extra_ids: list[int]):
    data = await state.get_data()
    item_id, vol_id = data.get("sel_item_id"), data.get("sel_vol_id")
    if not item_id or not vol_id: return
    cats = await db.get_categories()
    item_vols, item_name = {}, "Напиток"
    for c in cats:
        for i in await db.get_items(c["id"]):
            if i["id"] == item_id: item_vols = i.get("volumes", {}); item_name = i.get("name", "Напиток"); break
    vol_data = item_vols.get(vol_id, {})
    base_price = float(vol_data.get("price", 0))
    vol_name = vol_data.get("name", "Стандарт")
    
    lines = await db.get_cart(call.from_user.id)
    lines.append({"item_id": item_id, "name": item_name, "vol": vol_name, "vol_id": vol_id, "qty": 1, "extras": [], "line_total": base_price})
    await db.save_cart(call.from_user.id, lines)
    await render_cart(call.from_user.id, bot, state)
    await call.answer("✅ Добавлено в корзину")
    await state.set_state(UserFSM.viewing_cart)

@router.callback_query(F.data == "view_cart")
async def open_cart(call: CallbackQuery, state: FSMContext, bot: Bot):
    await render_cart(call.from_user.id, bot, state)
    await call.answer()

@router.callback_query(F.data.startswith("cart_plus_") | F.data.startswith("cart_minus_"))
async def change_qty(call: CallbackQuery, state: FSMContext, bot: Bot):
    action = call.data.split("_")[1]
    idx = int(call.data.split("_")[2])
    lines = await db.get_cart(call.from_user.id)
    if idx >= len(lines): return
    line = lines[idx]
    unit_price = line["line_total"] / line["qty"] if line["qty"] > 0 else 0
    if action == "plus": line["qty"] += 1
    elif action == "minus":
        if line["qty"] > 1: line["qty"] -= 1
        else: lines.pop(idx)
    line["line_total"] = unit_price * line["qty"]
    await db.save_cart(call.from_user.id, lines)
    await render_cart(call.from_user.id, bot, state)
    await call.answer()

@router.callback_query(F.data.startswith("cart_add_extras_"))
async def start_adding_extras(call: CallbackQuery, state: FSMContext, bot: Bot):
    idx = int(call.data.split("_")[-1])
    await state.update_data({"cart_edit_idx": idx})
    cats = await db.get_extra_categories()
    if not cats: return await call.answer("⚠️ Допы пока не добавлены", show_alert=True)
    await call.message.edit_text("📦 Выберите категорию допов:", reply_markup=extra_cats_kb(cats))
    await state.set_state(UserFSM.editing_item_extras)
    await call.answer()

@router.callback_query(F.data.startswith("excat_"), UserFSM.editing_item_extras)
async def show_extras_for_cat(call: CallbackQuery, state: FSMContext, bot: Bot):
    cat_id = int(call.data.split("_")[1])
    cats = await db.get_extra_categories()
    cat = next((c for c in cats if c["id"] == cat_id), None)
    if not cat: return
    extras = await db.get_extras_by_category(cat_id)
    if not extras: return await call.answer("В этой категории пока пусто", show_alert=True)
    
    kb = extras_kb(extras)
    if cat.get("photo_id"):
        await call.message.edit_media(media=InputMediaPhoto(media=cat["photo_id"]), caption="🥐 Выберите доп:", reply_markup=kb)
    else:
        await call.message.edit_text("🥐 Выберите доп:", reply_markup=kb)
    await state.update_data({"sel_extra_cat_id": cat_id})
    await call.answer()

@router.callback_query(F.data.startswith("add_ex_"), UserFSM.editing_item_extras)
async def add_extra_to_item(call: CallbackQuery, state: FSMContext, bot: Bot):
    eid = int(call.data.split("_")[2])
    data = await state.get_data()
    idx = data.get("cart_edit_idx")
    if idx is None: return
    lines = await db.get_cart(call.from_user.id)
    if idx >= len(lines): return
    
    extras_list = await db.get_extras_by_category(data["sel_extra_cat_id"])
    extra = next((e for e in extras_list if e["id"] == eid), None)
    if not extra: return
    
    lines[idx]["extras"].append({"id": extra["id"], "name": extra["name"], "price": extra["price"]})
    lines[idx]["line_total"] += extra["price"]
    await db.save_cart(call.from_user.id, lines)
    await render_cart(call.from_user.id, bot, state)
    await call.answer(f"✅ {extra['name']} добавлен")
    await state.set_state(UserFSM.viewing_cart)

@router.callback_query(F.data.in_(["back_to_cart_from_extras", "back_to_excats"]), UserFSM.editing_item_extras)
async def cancel_extras(call: CallbackQuery, state: FSMContext, bot: Bot):
    await state.set_state(UserFSM.viewing_cart)
    await render_cart(call.from_user.id, bot, state)
    await call.answer()

@router.callback_query(F.data == "clear_cart")
async def clear_cart(call: CallbackQuery, state: FSMContext, bot: Bot):
    await db.clear_cart(call.from_user.id)
    await call.message.delete()
    await state.clear()
    await call.answer("🗑 Очищено")

# ⏱ ВЫБОР ВРЕМЕНИ (МСК)
@router.callback_query(F.data == "checkout")
async def checkout(call: CallbackQuery, state: FSMContext, bot: Bot):
    lines = await db.get_cart(call.from_user.id)
    if not lines: return await call.answer("Корзина пуста", show_alert=True)
    await state.update_data({"time_offset": 5})
    await call.message.edit_text("🕒 Выберите удобное время для получения:", reply_markup=time_kb(5))
    await state.set_state(UserFSM.selecting_time)
    await call.answer()

@router.callback_query(F.data == "time_plus")
async def time_plus(call: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    await state.update_data({"time_offset": data.get("time_offset", 5) + 5})
    await call.message.edit_reply_markup(reply_markup=time_kb(data.get("time_offset", 5) + 5))
    await call.answer()

@router.callback_query(F.data == "time_minus")
async def time_minus(call: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    new_offset = data.get("time_offset", 5) - 5
    if new_offset < 5: return await call.answer("⏳ Минимум 5 минут", show_alert=True)
    await state.update_data({"time_offset": new_offset})
    await call.message.edit_reply_markup(reply_markup=time_kb(new_offset))
    await call.answer()

@router.callback_query(F.data == "time_confirm")
async def time_confirm(call: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    offset = data.get("time_offset", 5)
    target = datetime.now(tz=MSK) + timedelta(minutes=offset)
    time_str = target.strftime("%H:%M")
    await state.update_data({"pickup_time": time_str})
    await call.message.edit_text(
        f"⏰ Заказ готов к: *{time_str}*\n\n🤔 Хотите выбрать что-то ещё?",
        reply_markup=post_time_question_kb(),
        parse_mode="Markdown"
    )
    await state.set_state(UserFSM.after_time)
    await call.answer()

@router.callback_query(F.data == "after_time_menu")
async def after_time_menu(call: CallbackQuery, state: FSMContext, bot: Bot):
    cats = await db.get_categories()
    menu_photo = await db.get_setting("menu_photo")
    if menu_photo: await call.message.edit_media(media=InputMediaPhoto(media=menu_photo), caption="☕ Выберите категорию:", reply_markup=main_menu_kb(cats))
    else: await call.message.edit_text("☕ Выберите категорию:", reply_markup=main_menu_kb(cats))
    await state.set_state(UserFSM.browsing)
    await call.answer()

@router.callback_query(F.data == "after_time_pay")
async def after_time_pay(call: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    await call.message.edit_text(f"💳 Переход к оплате...\n🕒 Время: {data.get('pickup_time')}\n(ЮKassa подключается здесь)")
    await call.answer("✅ Готово к оплате")
    # Здесь будет создание заказа и генерация ссылки
    # await db.create_order(...)

@router.callback_query(F.data == "back_to_cart")
async def back_to_cart(call: CallbackQuery, state: FSMContext, bot: Bot):
    await render_cart(call.from_user.id, bot, state)
    await state.set_state(UserFSM.viewing_cart)
    await call.answer()
