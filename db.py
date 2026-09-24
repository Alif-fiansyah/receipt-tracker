import sqlite3
from datetime import datetime

DB_NAME = "expenses.db"


def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Tabel utama transaksi struk
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS receipts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            merchant TEXT,
            transaction_date TEXT,
            total_amount REAL,
            category TEXT,
            created_at TEXT
        )
    """)

    # Tabel rincian barang belanjaan
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS receipt_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            receipt_id INTEGER,
            item_name TEXT,
            quantity REAL,
            total_price REAL,
            FOREIGN KEY (receipt_id) REFERENCES receipts (id)
        )
    """)

    conn.commit()
    conn.close()


def save_receipt_data(data: dict) -> int:
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute(
        """
        INSERT INTO receipts (merchant, transaction_date, total_amount, category, created_at)
        VALUES (?, ?, ?, ?, ?)
    """,
        (
            data["merchant"],
            data["transaction_date"],
            data["total_amount"],
            data["category"],
            now,
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
                item["item_name"],
                item.get("quantity", 1.0),
                item.get("total_price", 0.0),
            ),
        )

    conn.commit()
    conn.close()
    return receipt_id


def get_all_receipts():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, merchant, transaction_date, total_amount, category, created_at 
        FROM receipts 
        ORDER BY id DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return rows
