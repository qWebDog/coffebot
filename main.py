import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import settings
from db.database import db
from handlers import commands, menu, cart, payment, admin

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

async def main():
    bot = Bot(token=settings.bot_token)
    dp = Dispatcher(storage=MemoryStorage())  

    await db.connect()

    dp.include_routers(
        commands.router,
        menu.router,
        cart.router,
        payment.router,
        admin.router
    )

    try:
        logging.info("Бот запущен")
        await dp.start_polling(bot)
    finally:
        await db.close()
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
