from uuid import uuid4
from yookassa import Configuration, Payment
from yookassa.domain.models.receipt import Receipt, ReceiptItem
from config import settings

Configuration.account_id = settings.yookassa_shop_id
Configuration.secret_key = settings.yookassa_secret_key


def create_payment(total: float, items: dict, menu: list, user_id: int) -> tuple[str, str]:
    order_id = str(uuid4())

    receipt_items = [
        ReceiptItem(
            description=next(m["name"] for m in menu if m["id"] == item_id),
            quantity=qty,
            amount={"value": str(next(m["price"] for m in menu if m["id"] == item_id)), "currency": "RUB"},
            vat_code="1"
        ) for item_id, qty in items.items()
    ]

    receipt = Receipt(customer={"email": f"user_{user_id}@coffee-bot.local"}, items=receipt_items)

    payment = Payment.create({
        "amount": {"value": str(total), "currency": "RUB"},
        "capture": True,
        "confirmation": {"type": "redirect", "return_url": f"https://t.me/{settings.bot_username}"},
        "metadata": {"order_id": order_id, "user_id": str(user_id)},
        "receipt": receipt
    })

    return order_id, payment.confirmation.confirmation_url
