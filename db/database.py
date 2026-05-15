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
        if self.conn:
            await self.conn.close()

    async def init_tables(self):
        await self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS carts (user_id INTEGER PRIMARY KEY, items TEXT, total REAL, chat_id INTEGER, message_id INTEGER);
            CREATE TABLE IF NOT EXISTS orders (id TEXT PRIMARY KEY, user_id INTEGER, items TEXT, total REAL, status TEXT DEFAULT 'pending', created_at DATETIME DEFAULT CURRENT_TIMESTAMP, customer_username TEXT);
            CREATE TABLE IF NOT EXISTS categories (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE);
            CREATE TABLE IF NOT EXISTS volumes (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE);
            CREATE TABLE IF NOT EXISTS menu_items (id INTEGER PRIMARY KEY AUTOINCREMENT, category_id INTEGER, name TEXT, item_type TEXT DEFAULT 'drink', volumes_json TEXT, photo_file_id TEXT, is_active INTEGER DEFAULT 1);
            CREATE TABLE IF NOT EXISTS bot_settings (key TEXT PRIMARY KEY, value TEXT);
        """)
        # Миграция старых таблиц (если есть)
        for col in ["customer_username"]:
            try:
                cur = await self.conn.execute(f"PRAGMA table_info(orders)")
                if col not in [r[1] for r in await cur.fetchall()]:
                    await self.conn.execute(f"ALTER TABLE orders ADD COLUMN {col} TEXT DEFAULT NULL")
            except: pass
        await self.conn.commit()

    # 📦 Меню и товары
    async def get_drinks(self) -> list[dict]:
        cur = await self.conn.execute("SELECT m.id, c.name as cat, m.name, m.volumes_json FROM menu_items m LEFT JOIN categories c ON m.category_id = c.id WHERE m.is_active=1 AND m.item_type='drink' ORDER BY m.id")
        res = []
        async for row in cur:
            vols = json.loads(row[3]) if row[3] else {}
            vol_list = await self.get_volumes_by_ids(list(vols.keys()))
            res.append({"id": row[0], "category": row[1], "name": row[2], "volumes": {v["id"]: {"name": v["name"], "price": float(vols.get(str(v["id"])), 0)} for v in vol_list}})
        return res

    async def get_extras(self) -> list[dict]:
        cur = await self.conn.execute("SELECT id, name, price FROM menu_items WHERE is_active=1 AND item_type='extra' ORDER BY id")
        return [{"id": r[0], "name": r[1], "price": r[2]} for r in await cur.fetchall()]

    async def add_item(self, category_id: int, name: str, item_type: str, volumes_json: str, price: float = 0):
        await self.conn.execute("INSERT INTO menu_items (category_id, name, item_type, volumes_json, price) VALUES (?,?,?,?,?)", (category_id, name, item_type, volumes_json, price))
        await self.conn.commit()

    async def update_item(self, item_id: int, field: str, value):
        await self.conn.execute(f"UPDATE menu_items SET {field}=? WHERE id=?", (value, item_id))
        await self.conn.commit()

    async def delete_item(self, item_id: int):
        await self.conn.execute("UPDATE menu_items SET is_active=0 WHERE id=?", (item_id,))
        await self.conn.commit()

    # 📏 Объёмы
    async def get_volumes(self) -> list[dict]:
        cur = await self.conn.execute("SELECT id, name FROM volumes ORDER BY id")
        return [{"id": r[0], "name": r[1]} for r in await cur.fetchall()]

    async def get_volumes_by_ids(self, ids: list[int]) -> list[dict]:
        if not ids: return []
        ids_str = ",".join(map(str, ids))
        cur = await self.conn.execute(f"SELECT id, name FROM volumes WHERE id IN ({ids_str})")
        return [{"id": r[0], "name": r[1]} for r in await cur.fetchall()]

    async def add_volume(self, name: str) -> int:
        await self.conn.execute("INSERT INTO volumes (name) VALUES (?)", (name,))
        await self.conn.commit()
        cur = await self.conn.execute("SELECT last_insert_rowid()")
        return (await cur.fetchone())[0]

    async def update_volume(self, vol_id: int, name: str):
        await self.conn.execute("UPDATE volumes SET name=? WHERE id=?", (name, vol_id))
        await self.conn.commit()

    async def delete_volume(self, vol_id: int):
        await self.conn.execute("DELETE FROM volumes WHERE id=?", (vol_id,))
        await self.conn.commit()

    # 🗂 Категории и настройки
    async def get_categories(self) -> list[dict]:
        cur = await self.conn.execute("SELECT id, name FROM categories ORDER BY id")
        return [{"id": r[0], "name": r[1]} for r in await cur.fetchall()]

    async def set_setting(self, key: str, value: str):
        await self.conn.execute("INSERT OR REPLACE INTO bot_settings VALUES (?, ?)", (key, value))
        await self.conn.commit()

    async def get_setting(self, key: str) -> str | None:
        cur = await self.conn.execute("SELECT value FROM bot_settings WHERE key=?", (key,))
        res = await cur.fetchone()
        return res[0] if res else None

    # 🛒 Корзина и заказы
    async def get_cart(self, user_id: int) -> dict | None:
        cur = await self.conn.execute("SELECT items, total, chat_id, message_id FROM carts WHERE user_id=?", (user_id,))
        row = await cur.fetchone()
        return {"items": json.loads(row[0]), "total": row[1], "chat_id": row[2], "message_id": row[3]} if row else None

    async def save_cart(self, user_id: int, items: dict, total: float, chat_id: int, message_id: int):
        await self.conn.execute("INSERT OR REPLACE INTO carts VALUES (?, ?, ?, ?, ?)", (user_id, json.dumps(items), total, chat_id, message_id))
        await self.conn.commit()

    async def clear_cart(self, user_id: int):
        await self.conn.execute("DELETE FROM carts WHERE user_id=?", (user_id,))
        await self.conn.commit()

    async def create_order(self, order_id: str, user_id: int, items: dict, total: float, username: str):
        await self.conn.execute("INSERT INTO orders (id, user_id, items, total, customer_username) VALUES (?, ?, ?, ?, ?)", (order_id, user_id, json.dumps(items), total, username))
        await self.conn.commit()

    async def get_sales_stats(self, start: str, end: str) -> list[tuple]:
        cur = await self.conn.execute("SELECT date(created_at) as day, COUNT(*) as orders, SUM(total) as revenue FROM orders WHERE status='paid' AND created_at BETWEEN ? AND ? GROUP BY day ORDER BY day DESC", (start, end))
        return await cur.fetchall()

db = Database()
