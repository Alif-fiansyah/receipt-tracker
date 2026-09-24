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

        # Buat client sinkron ke Turso Cloud
        return libsql_client.create_client_sync(
            url=TURSO_URL,
            auth_token=TURSO_TOKEN,
        )
    return None


def init_db():
    client = get_client()
    if client:
        # Skema Turso Cloud
        client.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
    else:
        # Fallback ke SQLite lokal
        conn = sqlite3.connect(LOCAL_DB)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS receipts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                merchant TEXT,
                transaction_date TEXT,
                total_amount REAL,
                category TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        conn.commit()
        conn.close()

def save_receipt_data(data: dict) -> int:
    client = get_client()
    if client:
        res = client.execute(
            """
            INSERT INTO receipts (merchant, transaction_date, total_amount, category)
            VALUES (?, ?, ?, ?)
        """,
            [
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
            INSERT INTO receipts (merchant, transaction_date, total_amount, category)
            VALUES (?, ?, ?, ?)
        """,
            (
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


def get_all_receipts():
    client = get_client()
    if client:
        res = client.execute(
            """
            SELECT id, merchant, transaction_date, total_amount, category, created_at 
            FROM receipts 
            ORDER BY id DESC
        """
        )
        client.close()
        # Ubah ResultSet Turso menjadi daftar tuple agar cocok dengan Pandas
        return [tuple(row) for row in res.rows]
    else:
        conn = sqlite3.connect(LOCAL_DB)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, merchant, transaction_date, total_amount, category, created_at 
            FROM receipts 
            ORDER BY id DESC
        """
        )
        rows = cursor.fetchall()
        conn.close()
        return rows