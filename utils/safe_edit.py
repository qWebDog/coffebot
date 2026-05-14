import logging
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest

async def safe_edit_message(bot: Bot, chat_id: int, message_id: int, text: str, kb=None, parse_mode="Markdown"):
    try:
        await bot.edit_message_text(text=text, chat_id=chat_id, message_id=message_id, reply_markup=kb, parse_mode=parse_mode)
    except TelegramBadRequest as e:
        if "message is not modified" in str(e).lower():
            pass  # Игнорируем
        else:
            # Если сообщение удалено или изменено, отправим новое
            try:
                msg = await bot.send_message(chat_id=chat_id, text=text, reply_markup=kb, parse_mode=parse_mode)
                # Обновляем ID в БД (логика вызывается из handlers)
                return msg.message_id
            except Exception:
                logging.warning(f"Не удалось отредактировать/отправить сообщение: {e}")
    return None