from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest

async def safe_edit(bot: Bot, chat_id: int, msg_id: int, text: str, kb=None, parse_mode=None):
    try:
        return await bot.edit_message_text(text=text, chat_id=chat_id, message_id=msg_id, reply_markup=kb, parse_mode=parse_mode)
    except TelegramBadRequest as e:
        if "message is not modified" in str(e).lower(): return None
        sent = await bot.send_message(chat_id=chat_id, text=text, reply_markup=kb, parse_mode=parse_mode)
        return sent.message_id
    except Exception: return None
