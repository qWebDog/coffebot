from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    bot_token: str
    yookassa_shop_id: str
    yookassa_secret_key: str
    webhook_url: str
    bot_username: str
    db_path: str = "coffee_bot.db"
    admin_ids: str = "123456789"  # ID админов через запятую
    admin_chat_id: int | None = None

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

settings = Settings()