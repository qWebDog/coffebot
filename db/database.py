import aiosqlite
import json
from config import settings

class Database:
    def __init__(self):
        self.conn: aiosqlite.Connection | None = None

    async def connect(self):
        self.conn = await aiosqlite.connect(settings.db_path)
        await self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS categories (id INTEGER PRIMARY KEY AUTOINCREMENT, slug TEXT UNIQUE, name TEXT, photo_id TEXT);
            CREATE TABLE IF NOT EXISTS volumes (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE);
            CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY AUTOINCREMENT, category_id INTEGER, name TEXT, photo_id TEXT, volumes_json TEXT, FOREIGN KEY(category_id) REFERENCES categories(id));
            CREATE TABLE IF NOT EXISTS extras (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, price REAL, photo_id TEXT);
            CREATE TABLE IF NOT EXISTS cart (user_id INTEGER PRIMARY KEY, data_json TEXT);
            CREATE TABLE IF NOT EXISTS orders (id TEXT PRIMARY KEY, user_id INTEGER, data_json TEXT, total REAL, status TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP);
        """)
        # Дефолтные категории
        for slug, name in [("coffee", "Кофе"), ("non_coffee", "Не кофе"), ("tea", "Чай"), ("cold", "Холодные"), ("lemonade", "Лимонады")]:
            await self.conn.execute("INSERT OR IGNORE INTO categories (slug, name) VALUES (?, ?)", (slug, name))
        await self.conn.commit()

    # 📂 Категории
    async def get_categories(self): return [{"id": r[0], "slug": r[1], "name": r[2], "photo_id": r[3]} for r in await (await self.conn.execute("SELECT * FROM categories ORDER BY id")).fetchall()]
    async def update_cat_photo(self, slug: str, photo_id: str): await self.conn.execute("UPDATE categories SET photo_id=? WHERE slug=?", (photo_id, slug)); await self.conn.commit()

    # 📏 Объемы
    async def get_volumes(self): return [{"id": r[0], "name": r[1]} for r in await (await self.conn.execute("SELECT * FROM volumes ORDER BY id")).fetchall()]
    async def add_volume(self, name: str): await self.conn.execute("INSERT INTO volumes (name) VALUES (?)", (name,)); await self.conn.commit()

    # ☕ Позиции
    async def get_items(self, cat_id: int): return [{"id": r[0], "name": r[2], "volumes": json.loads(r[4]) if r[4] else {}} for r in await (await self.conn.execute("SELECT id, category_id, name, photo_id, volumes_json FROM items WHERE category_id=?", (cat_id,))).fetchall()]
    async def add_item(self, cat_id: int, name: str, volumes_json: str): await self.conn.execute("INSERT INTO items (category_id, name, volumes_json) VALUES (?,?,?)", (cat_id, name, volumes_json)); await self.conn.commit()

    # 🥐 Допы
    async def get_extras(self): return [{"id": r[0], "name": r[1], "price": r[2], "photo_id": r[3]} for r in await (await self.conn.execute("SELECT * FROM extras ORDER BY id")).fetchall()]
    async def get_extra(self, eid: int): return next(({"id": r[0], "name": r[1], "price": r[2], "photo_id": r[3]} for r in await (await self.conn.execute("SELECT * FROM extras WHERE id=?", (eid,))).fetchall()), None)

    # 🛒 Корзина
    async def get_cart(self, uid: int):
        row = await (await self.conn.execute("SELECT data_json FROM cart WHERE user_id=?", (uid,))).fetchone()
        return json.loads(row[0]) if row and row[0] else []
    async def save_cart(self, uid: int, data: list):
        await self.conn.execute("INSERT OR REPLACE INTO cart VALUES (?, ?)", (uid, json.dumps(data)))
        await self.conn.commit()
    async def clear_cart(self, uid: int):
        await self.conn.execute("DELETE FROM cart WHERE user_id=?", (uid,))
        await self.conn.commit()

    # 📦 Заказы
    async def create_order(self, order_id: str, uid: int, data: list, total: float):
        await self.conn.execute("INSERT INTO orders (id, user_id, data_json, total, status) VALUES (?,?,?,?, 'pending')", (order_id, uid, json.dumps(data), total))
        await self.conn.commit()

db = Database()
