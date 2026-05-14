import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import settings
from db.database import db
from handlers import commands, menu, cart, payment, admin

# Настраиваем логирование, чтобы видеть ВСЁ
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s | %(levelname)s | %(message)s")

async def main():
    bot = Bot(token=settings.bot_token)
    # ✅ Обязательно: хранилище для FSM
    dp = Dispatcher(storage=MemoryStorage())

    await db.connect()

    # ✅ Порядок важен! Специфичные роутеры идут первыми
    dp.include_routers(
        admin.router,    # ← Админка ПЕРВОЙ (чтобы не съелась другими)
        commands.router,
        menu.router,
        cart.router,
        payment.router
    )

    logging.info(f"🤖 Бот @{(await bot.me).username} запущен (ID: {bot.id})")
    
    try:
        await dp.start_polling(bot)
    finally:
        await db.close()
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
