# main.py
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import settings
from db.database import db
from handlers import commands, menu, cart, payment, admin

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

async def main():
    bot = Bot(token=settings.bot_token)
    dp = Dispatcher(storage=MemoryStorage())

    await db.connect()

    # ✅ Порядок: специфичные роутеры первыми
    dp.include_routers(
        admin.router,
        commands.router,
        menu.router,
        cart.router,
        payment.router
    )

    # ✅ bot.me — свойство, не требует await
    me = await bot.get_me()  # ← явно получаем инфо о боте
    logging.info(f"🤖 Бот @{me.username} запущен (ID: {me.id})")
    
    try:
        await dp.start_polling(bot)
    finally:
        await db.close()
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
