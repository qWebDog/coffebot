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
            CREATE TABLE IF NOT EXISTS carts (
                user_id INTEGER PRIMARY KEY, items TEXT, total REAL,
                chat_id INTEGER, message_id INTEGER
            );
            CREATE TABLE IF NOT EXISTS orders (
                id TEXT PRIMARY KEY, user_id INTEGER, items TEXT, total REAL,
                status TEXT DEFAULT 'pending', created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                customer_username TEXT
            );
            CREATE TABLE IF NOT EXISTS categories (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE);
            CREATE TABLE IF NOT EXISTS menu_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT, category_id INTEGER, name TEXT, price REAL,
                volume TEXT, photo_file_id TEXT, is_active INTEGER DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS bot_settings (key TEXT PRIMARY KEY, value TEXT);
        """)

        # Миграция 1: customer_username
        try:
            cur = await self.conn.execute("PRAGMA table_info(orders)")
            cols = [r[1] for r in await cur.fetchall()]
            if "customer_username" not in cols:
                await self.conn.execute("ALTER TABLE orders ADD COLUMN customer_username TEXT DEFAULT NULL")
                await self.conn.commit()
        except: pass

        # Миграция 2: item_type (drink/extra)
        try:
            await self.conn.execute("ALTER TABLE menu_items ADD COLUMN item_type TEXT DEFAULT 'drink'")
            await self.conn.commit()
        except: pass

        await self.conn.commit()

    async def get_menu_items(self, item_type: str = 'drink') -> list[dict]:
        cur = await self.conn.execute("""
            SELECT m.id, c.name as category, m.name, m.price, m.volume, m.photo_file_id
            FROM menu_items m LEFT JOIN categories c ON m.category_id = c.id
            WHERE m.is_active = 1 AND m.item_type = ? ORDER BY c.id, m.id
        """, (item_type,))
        rows = await cur.fetchall()
        return [{"id": r[0], "category": r[1] or "Без категории", "name": r[2],
                 "price": r[3], "volume": r[4], "photo_id": r[5]} for r in rows]

    async def add_menu_item(self, category_id: int, name: str, price: float, volume: str, photo_id: str = None, item_type: str = 'drink'):
        await self.conn.execute(
            "INSERT INTO menu_items (category_id, name, price, volume, photo_file_id, item_type) VALUES (?,?,?,?,?,?)",
            (category_id, name, price, volume, photo_id, item_type)
        )
        await self.conn.commit()

    async def update_menu_item(self, item_id: int, field: str, value):
        await self.conn.execute(f"UPDATE menu_items SET {field}=? WHERE id=?", (value, item_id))
        await self.conn.commit()

    async def delete_menu_item(self, item_id: int):
        await self.conn.execute("UPDATE menu_items SET is_active=0 WHERE id=?", (item_id,))
        await self.conn.commit()

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

    async def get_cart(self, user_id: int) -> dict | None:
        cur = await self.conn.execute("SELECT items, total, chat_id, message_id FROM carts WHERE user_id=?", (user_id,))
        row = await cur.fetchone()
        if not row: return None
        return {"items": json.loads(row[0]), "total": row[1], "chat_id": row[2], "message_id": row[3]}

    async def save_cart(self, user_id: int, items: dict, total: float, chat_id: int, message_id: int):
        await self.conn.execute("INSERT OR REPLACE INTO carts VALUES (?, ?, ?, ?, ?)",
                                (user_id, json.dumps(items), total, chat_id, message_id))
        await self.conn.commit()

    async def clear_cart(self, user_id: int):
        await self.conn.execute("DELETE FROM carts WHERE user_id=?", (user_id,))
        await self.conn.commit()

    async def create_order(self, order_id: str, user_id: int, items: dict, total: float, username: str):
        await self.conn.execute(
            "INSERT INTO orders (id, user_id, items, total, customer_username) VALUES (?, ?, ?, ?, ?)",
            (order_id, user_id, json.dumps(items), total, username))
        await self.conn.commit()

    async def get_order(self, order_id: str) -> dict | None:
        cur = await self.conn.execute("SELECT * FROM orders WHERE id=?", (order_id,))
        row = await cur.fetchone()
        if not row: return None
        return {"id": row[0], "user_id": row[1], "items": json.loads(row[2]),
                "total": row[3], "status": row[4], "created_at": row[5], "username": row[6]}

    async def update_order_status(self, order_id: str, status: str):
        await self.conn.execute("UPDATE orders SET status=? WHERE id=?", (status, order_id))
        await self.conn.commit()

    async def get_sales_stats(self, start: str, end: str) -> list[tuple]:
        query = """
            SELECT date(created_at) as day, COUNT(*) as orders, SUM(total) as revenue
            FROM orders WHERE status='paid' AND created_at BETWEEN ? AND ?
            GROUP BY day ORDER BY day DESC
        """
        cur = await self.conn.execute(query, (start, end))
        return await cur.fetchall()

db = Database()
