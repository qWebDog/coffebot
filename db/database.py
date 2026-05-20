# db/database.py
import aiosqlite
import json
from config import settings

class Database:
    def __init__(self):
        self.conn: aiosqlite.Connection | None = None

    async def connect(self):
        self.conn = await aiosqlite.connect(settings.db_path)
        await self.init_tables()

    async def close(self):
        if self.conn: await self.conn.close()

    async def init_tables(self):
        await self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS categories (id INTEGER PRIMARY KEY AUTOINCREMENT, slug TEXT UNIQUE, name TEXT, photo_id TEXT);
            CREATE TABLE IF NOT EXISTS volumes (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE);
            CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY AUTOINCREMENT, category_id INTEGER, name TEXT, photo_id TEXT, volumes_json TEXT, FOREIGN KEY(category_id) REFERENCES categories(id));
            CREATE TABLE IF NOT EXISTS extra_categories (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, photo_id TEXT);
            CREATE TABLE IF NOT EXISTS extras (id INTEGER PRIMARY KEY AUTOINCREMENT, category_id INTEGER, name TEXT, volume TEXT, price REAL, FOREIGN KEY(category_id) REFERENCES extra_categories(id));
            CREATE TABLE IF NOT EXISTS cart (user_id INTEGER PRIMARY KEY, data_json TEXT);
            CREATE TABLE IF NOT EXISTS orders (id TEXT PRIMARY KEY, user_id INTEGER, data_json TEXT, total REAL, status TEXT, pickup_time TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS bot_settings (key TEXT PRIMARY KEY, value TEXT);
        """)
        
        # Миграция для старых БД
        try: await self.conn.execute("ALTER TABLE extras ADD COLUMN volume TEXT DEFAULT 'Стандарт'")
        except: pass

        for slug, name in [("coffee", "Кофе"), ("non_coffee", "Не кофе"), ("tea", "Чай"), ("cold", "Холодные"), ("lemonade", "Лимонады")]:
            try: await self.conn.execute("INSERT OR IGNORE INTO categories (slug, name) VALUES (?, ?)", (slug, name))
            except: pass
        await self.conn.commit()

    # 📂 Категории меню
    async def get_categories(self):
        return [{"id": r[0], "slug": r[1], "name": r[2], "photo_id": r[3]} for r in await (await self.conn.execute("SELECT * FROM categories ORDER BY id")).fetchall()]
    async def update_cat_photo(self, slug: str, photo_id: str):
        await self.conn.execute("UPDATE categories SET photo_id=? WHERE slug=?", (photo_id, slug)); await self.conn.commit()

    # 📏 Объемы
    async def get_volumes(self):
        return [{"id": r[0], "name": r[1]} for r in await (await self.conn.execute("SELECT * FROM volumes ORDER BY id")).fetchall()]
    async def add_volume(self, name: str):
        await self.conn.execute("INSERT INTO volumes (name) VALUES (?)", (name,)); await self.conn.commit()

    # ☕ Позиции
    async def get_items(self, cat_id: int):
        rows = await (await self.conn.execute("SELECT id, name, volumes_json FROM items WHERE category_id=?", (cat_id,))).fetchall()
        res, vols = [], await self.get_volumes()
        for r in rows:
            v_raw = json.loads(r[2]) if r[2] else {}
            v_named = {int(vid): {"name": next((v["name"] for v in vols if v["id"] == int(vid)), "Std"), "price": float(price)} for vid, price in v_raw.items()}
            res.append({"id": r[0], "name": r[1], "volumes": v_named})
        return res
    async def add_item(self, cat_id: int, name: str, volumes_json: str):
        await self.conn.execute("INSERT INTO items (category_id, name, volumes_json) VALUES (?,?,?)", (cat_id, name, volumes_json)); await self.conn.commit()

    # 🥐 Допы и категории допов
    async def get_extra_categories(self):
        return [{"id": r[0], "name": r[1], "photo_id": r[2]} for r in await (await self.conn.execute("SELECT * FROM extra_categories ORDER BY id")).fetchall()]
    async def update_extra_cat_photo(self, cat_id: int, photo_id: str):
        await self.conn.execute("UPDATE extra_categories SET photo_id=? WHERE id=?", (photo_id, cat_id)); await self.conn.commit()
    async def add_extra_category(self, name: str):
        await self.conn.execute("INSERT INTO extra_categories (name) VALUES (?)", (name,)); await self.conn.commit()
    async def get_extras_by_category(self, cat_id: int):
        return [{"id": r[0], "name": r[2], "volume": r[3], "price": r[4]} for r in await (await self.conn.execute("SELECT id, category_id, name, volume, price FROM extras WHERE category_id=?", (cat_id,))).fetchall()]
    async def add_extra(self, cat_id: int, name: str, price: float, volume: str = "Стандарт"):
        await self.conn.execute("INSERT INTO extras (category_id, name, volume, price) VALUES (?,?,?,?)", (cat_id, name, volume, price)); await self.conn.commit()
    async def delete_extra(self, eid: int):
        await self.conn.execute("DELETE FROM extras WHERE id=?", (eid,)); await self.conn.commit()

    # ⚙️ Настройки
    async def set_setting(self, key: str, value: str):
        await self.conn.execute("INSERT OR REPLACE INTO bot_settings VALUES (?, ?)", (key, value)); await self.conn.commit()
    async def get_setting(self, key: str) -> str | None:
        row = await (await self.conn.execute("SELECT value FROM bot_settings WHERE key=?", (key,))).fetchone()
        return row[0] if row else None

    # 🛒 Корзина & Заказы
    async def get_cart(self, uid: int):
        row = await (await self.conn.execute("SELECT data_json FROM cart WHERE user_id=?", (uid,))).fetchone()
        return json.loads(row[0]) if row and row[0] else []
    async def save_cart(self, uid: int, data: list):
        await self.conn.execute("INSERT OR REPLACE INTO cart VALUES (?, ?)", (uid, json.dumps(data))); await self.conn.commit()
    async def clear_cart(self, uid: int):
        await self.conn.execute("DELETE FROM cart WHERE user_id=?", (uid,)); await self.conn.commit()
    async def create_order(self, order_id: str, uid: int, data: list, total: float, pickup_time: str):
        await self.conn.execute("INSERT INTO orders (id, user_id, data_json, total, status, pickup_time) VALUES (?,?,?,?, 'pending', ?)", (order_id, uid, json.dumps(data), total, pickup_time)); await self.conn.commit()

db = Database()
