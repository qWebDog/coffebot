import asyncio
import logging
from aiogram import Bot, Dispatcher
from config import settings
from db.database import db
from handlers import commands, menu, cart, payment, admin

logging.basicConfig(level=logging.INFO)

async def main():
    bot = Bot(token=settings.bot_token)
    dp = Dispatcher()

    # Инициализация БД
    await db.connect()
    await db.init_tables()

    # Подключаем роутеры
    dp.include_routers(commands.router, menu.router, cart.router, payment.router, admin.router)

    try:
        await dp.start_polling(bot)
    finally:
        await db.close()
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())