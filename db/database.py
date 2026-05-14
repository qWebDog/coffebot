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
        # 1️⃣ Создаём таблицы (если их нет)
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
            CREATE TABLE IF NOT EXISTS menu_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, price REAL, volume TEXT,
                photo_file_id TEXT, is_active INTEGER DEFAULT 1
            );
        """)

        # 2️⃣ Миграция: добавляем колонку, если её нет в старой БД
        try:
            cur = await self.conn.execute("PRAGMA table_info(orders)")
            columns = [row[1] for row in await cur.fetchall()]
            if "customer_username" not in columns:
                await self.conn.execute("ALTER TABLE orders ADD COLUMN customer_username TEXT DEFAULT NULL")
                await self.conn.commit()
                print("✅ Миграция БД: добавлена колонка customer_username")
        except Exception as e:
            print(f"⚠️ Ошибка миграции БД: {e}")

        await self.conn.commit()

    async def get_menu_items(self) -> list[dict]:
        cur = await self.conn.execute("SELECT id, name, price, volume, photo_file_id FROM menu_items WHERE is_active=1")
        rows = await cur.fetchall()
        return [{"id": r[0], "name": r[1], "price": r[2], "volume": r[3], "photo_id": r[4]} for r in rows]

    async def add_menu_item(self, name: str, price: float, volume: str, photo_id: str) -> int:
        await self.conn.execute("INSERT INTO menu_items (name, price, volume, photo_file_id) VALUES (?,?,?,?)",
                                (name, price, volume, photo_id))
        await self.conn.commit()
        cur = await self.conn.execute("SELECT last_insert_rowid()")
        return (await cur.fetchone())[0]

    async def update_menu_item(self, item_id: int, field: str, value):
        await self.conn.execute(f"UPDATE menu_items SET {field}=? WHERE id=?", (value, item_id))
        await self.conn.commit()

    async def delete_menu_item(self, item_id: int):
        await self.conn.execute("UPDATE menu_items SET is_active=0 WHERE id=?", (item_id,))
        await self.conn.commit()

    async def get_cart(self, user_id: int) -> dict | None:
        cur = await self.conn.execute("SELECT items, total, chat_id, message_id FROM carts WHERE user_id=?", (user_id,))
        row = await cur.fetchone()
        if not row:
            return None
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
            (order_id, user_id, json.dumps(items), total, username)
        )
        await self.conn.commit()

    async def get_order(self, order_id: str) -> dict | None:
        cur = await self.conn.execute("SELECT * FROM orders WHERE id=?", (order_id,))
        row = await cur.fetchone()
        if not row:
            return None
        return {
            "id": row[0], "user_id": row[1], "items": json.loads(row[2]),
            "total": row[3], "status": row[4], "created_at": row[5], "username": row[6]
        }

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
