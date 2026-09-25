import hashlib
import os
import sqlite3
from dotenv import load_dotenv

load_dotenv()

TURSO_URL = os.getenv("TURSO_DATABASE_URL")
TURSO_TOKEN = os.getenv("TURSO_AUTH_TOKEN")
LOCAL_DB = "expenses.db"


def get_client():
    if TURSO_URL and TURSO_TOKEN:
        import libsql_client
        return libsql_client.create_client_sync(
            url=TURSO_URL,
            auth_token=TURSO_TOKEN,
        )
    return None


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def register_user(username: str, password: str) -> bool:
    pwd_hash = hash_password(password)
    client = get_client()
    if client:
        try:
            client.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                [username, pwd_hash],
            )
            client.close()
            return True
        except Exception:
            client.close()
            return False
    else:
        conn = sqlite3.connect(LOCAL_DB)
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (username, pwd_hash),
            )
            conn.commit()
            conn.close()
            return True
        except Exception:
            conn.close()
            return False


def authenticate_user(username: str, password: str):
    pwd_hash = hash_password(password)
    client = get_client()
    if client:
        res = client.execute(
            "SELECT id, username FROM users WHERE username = ? AND password_hash = ?",
            [username, pwd_hash],
        )
        client.close()
        if res.rows:
            return {"id": res.rows[0][0], "username": res.rows[0][1]}
        return None
    else:
        conn = sqlite3.connect(LOCAL_DB)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, username FROM users WHERE username = ? AND password_hash = ?",
            (username, pwd_hash),
        )
        row = cursor.fetchone()
        conn.close()
        if row:
            return {"id": row[0], "username": row[1]}
        return None


def init_db():
    client = get_client()
    if client:
        # Skema Turso Cloud
        client.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                password_hash TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        client.execute("""
            CREATE TABLE IF NOT EXISTS receipts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                merchant TEXT,
                transaction_date TEXT,
                total_amount REAL,
                category TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        client.execute("""
            CREATE TABLE IF NOT EXISTS receipt_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                receipt_id INTEGER,
                item_name TEXT,
                quantity INTEGER,
                total_price REAL,
                FOREIGN KEY (receipt_id) REFERENCES receipts(id)
            )
        """)
        client.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                user_id INTEGER,
                setting_key TEXT,
                setting_value TEXT,
                PRIMARY KEY (user_id, setting_key)
            )
        """)
        client.close()
    else:
        # Fallback ke SQLite lokal
        conn = sqlite3.connect(LOCAL_DB)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                password_hash TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS receipts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                merchant TEXT,
                transaction_date TEXT,
                total_amount REAL,
                category TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS receipt_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                receipt_id INTEGER,
                item_name TEXT,
                quantity INTEGER,
                total_price REAL,
                FOREIGN KEY (receipt_id) REFERENCES receipts(id)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                user_id INTEGER,
                setting_key TEXT,
                setting_value TEXT,
                PRIMARY KEY (user_id, setting_key)
            )
        """)
        conn.commit()
        conn.close()


def save_receipt_data(data: dict, user_id: int) -> int:
    client = get_client()
    if client:
        res = client.execute(
            """
            INSERT INTO receipts (user_id, merchant, transaction_date, total_amount, category)
            VALUES (?, ?, ?, ?, ?)
        """,
            [
                user_id,
                data.get("merchant"),
                data.get("transaction_date"),
                data.get("total_amount"),
                data.get("category"),
            ],
        )
        receipt_id = res.last_insert_rowid

        for item in data.get("items", []):
            client.execute(
                """
                INSERT INTO receipt_items (receipt_id, item_name, quantity, total_price)
                VALUES (?, ?, ?, ?)
            """,
                [
                    receipt_id,
                    item.get("item_name"),
                    item.get("quantity", 1),
                    item.get("total_price", 0.0),
                ],
            )
        client.close()
        return receipt_id
    else:
        conn = sqlite3.connect(LOCAL_DB)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO receipts (user_id, merchant, transaction_date, total_amount, category)
            VALUES (?, ?, ?, ?, ?)
        """,
            (
                user_id,
                data.get("merchant"),
                data.get("transaction_date"),
                data.get("total_amount"),
                data.get("category"),
            ),
        )
        receipt_id = cursor.lastrowid

        for item in data.get("items", []):
            cursor.execute(
                """
                INSERT INTO receipt_items (receipt_id, item_name, quantity, total_price)
                VALUES (?, ?, ?, ?)
            """,
                (
                    receipt_id,
                    item.get("item_name"),
                    item.get("quantity", 1),
                    item.get("total_price", 0.0),
                ),
            )
        conn.commit()
        conn.close()
        return receipt_id


def get_all_receipts(user_id: int):
    client = get_client()
    if client:
        res = client.execute(
            """
            SELECT id, merchant, transaction_date, total_amount, category, created_at 
            FROM receipts 
            WHERE user_id = ?
            ORDER BY id DESC
        """,
            [user_id],
        )
        client.close()
        return [tuple(row) for row in res.rows]
    else:
        conn = sqlite3.connect(LOCAL_DB)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, merchant, transaction_date, total_amount, category, created_at 
            FROM receipts 
            WHERE user_id = ?
            ORDER BY id DESC
        """,
            (user_id,),
        )
        rows = cursor.fetchall()
        conn.close()
        return rows


def get_budget(user_id: int, default_val: float = 3000000.0) -> float:
    client = get_client()
    if client:
        try:
            res = client.execute(
                "SELECT setting_value FROM settings WHERE user_id = ? AND setting_key = 'monthly_budget'",
                [user_id],
            )
            client.close()
            if res.rows:
                return float(res.rows[0][0])
        except Exception:
            pass
        return default_val
    else:
        conn = sqlite3.connect(LOCAL_DB)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT setting_value FROM settings WHERE user_id = ? AND setting_key = 'monthly_budget'",
            (user_id,),
        )
        row = cursor.fetchone()
        conn.close()
        if row:
            return float(row[0])
        return default_val


def set_budget(user_id: int, amount: float):
    client = get_client()
    if client:
        client.execute(
            """
            INSERT INTO settings (user_id, setting_key, setting_value) VALUES (?, 'monthly_budget', ?)
            ON CONFLICT(user_id, setting_key) DO UPDATE SET setting_value = excluded.setting_value
        """,
            [user_id, str(amount)],
        )
        client.close()
    else:
        conn = sqlite3.connect(LOCAL_DB)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO settings (user_id, setting_key, setting_value) VALUES (?, 'monthly_budget', ?)
            ON CONFLICT(user_id, setting_key) DO UPDATE SET setting_value = excluded.setting_value
        """,
            (user_id, str(amount)),
        )
        conn.commit()
        conn.close()