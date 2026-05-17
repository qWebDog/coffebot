import asyncio, logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import settings
from db.database import db
from handlers import user, admin

logging.basicConfig(level=logging.INFO)

async def main():
    bot = Bot(token=settings.bot_token)
    dp = Dispatcher(storage=MemoryStorage())
    await db.connect()
    
    dp.include_routers(user.router, admin.router)
    logging.info(f"🤖 Бот @{(await bot.get_me()).username} запущен")
    
    try: await dp.start_polling(bot)
    finally: await db.close(); await bot.session.close()

if __name__ == "__main__": asyncio.run(main())
