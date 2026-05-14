# webhook_server.py
import os
import json
import hmac
import hashlib
from fastapi import FastAPI, Request, HTTPException
from aiosqlite import connect
import httpx
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Yookassa Webhook Handler")

TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
YOOKASSA_SECRET_KEY = os.getenv("YOOKASSA_SECRET_KEY")
DB_PATH = os.getenv("DB_PATH", "coffee_bot.db")


# 🔐 Верификация подписи ЮKassa (обязательно для продакшена)
def verify_yookassa_signature(payload: bytes, signature: str) -> bool:
    if not signature or not YOOKASSA_SECRET_KEY:
        return True  # Для тестов можно отключить
    expected = hmac.new(
        YOOKASSA_SECRET_KEY.encode(), payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


@app.post("/yookassa/webhook")
async def handle_webhook(request: Request):
    # ... (верификация и парсинг data) ...
    if data.get("event") != "payment.succeeded":
        return {"status": "ignored"}

    order_id = data["object"]["metadata"]["order_id"]
    admin_chat_id = int(os.getenv("ADMIN_CHAT_ID", 0))

    if not admin_chat_id:
        return {"status": "ok", "note": "ADMIN_CHAT_ID not set"}

    # Получаем заказ из общей БД
    order = await db.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Формируем текст
    items_text = "\n".join([f"• {name} x{qty}" for name, qty in order["items"].items()])
    text = (
        f"🆕 <b>НОВЫЙ ОПЛАЧЕННЫЙ ЗАКАЗ!</b>\n\n"
        f"🆔 <code>{order['id']}</code>\n"
        f"👤 {order['username'] or 'Аноним'} (ID: {order['user_id']})\n"
        f"📦 Заказ:\n{items_text}\n"
        f"💰 Сумма: <b>{order['total']}₽</b>"
    )

    # Кнопка для админа
    reply_markup = {"inline_keyboard": [[{"text": "✅ Готов к выдаче", "callback_data": f"adm_ready_{order['id']}"}]]}

    # Отправляем через Telegram API
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage",
            json={"chat_id": admin_chat_id, "text": text, "reply_markup": reply_markup, "parse_mode": "HTML"}
        )

    return {"status": "ok"}