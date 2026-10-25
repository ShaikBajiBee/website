
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "chronosmatch.db"


def connect():
    connection = sqlite3.connect(DB_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    with connect() as connection:
        connection.executescript("""
            CREATE TABLE IF NOT EXISTS orders (
                order_id INTEGER PRIMARY KEY,
                side TEXT NOT NULL,
                price REAL NOT NULL,
                original_quantity INTEGER NOT NULL,
                filled_quantity INTEGER NOT NULL DEFAULT 0,
                remaining_quantity INTEGER NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS trades (
                trade_id INTEGER PRIMARY KEY AUTOINCREMENT,
                buy_order_id INTEGER NOT NULL,
                sell_order_id INTEGER NOT NULL,
                price REAL NOT NULL,
                quantity INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
        """)


def save_order(result):
    with connect() as connection:
        connection.execute("""
            INSERT INTO orders (
                order_id, side, price, original_quantity,
                filled_quantity, remaining_quantity, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            result["order_id"],
            result["side"],
            result["price"],
            result["original_quantity"],
            result["filled_quantity"],
            result["remaining_quantity"],
            "FILLED" if result["remaining_quantity"] == 0
            else "PARTIALLY_FILLED" if result["filled_quantity"] > 0
            else "OPEN"
        ))


def save_new_trades(trades):
    with connect() as connection:
        connection.executemany("""
            INSERT INTO trades (
                buy_order_id, sell_order_id, price, quantity
            ) VALUES (?, ?, ?, ?)
        """, [
            (
                trade["buy_order_id"],
                trade["sell_order_id"],
                trade["price"],
                trade["quantity"]
            )
            for trade in trades
        ])


def get_saved_orders():
    with connect() as connection:
        rows = connection.execute("""
            SELECT * FROM orders ORDER BY order_id DESC
        """).fetchall()
        return [dict(row) for row in rows]


def get_saved_trades():
    with connect() as connection:
        rows = connection.execute("""
            SELECT trade_id, buy_order_id, sell_order_id,
                   price, quantity, created_at
            FROM trades ORDER BY trade_id DESC
        """).fetchall()
        return [dict(row) for row in rows]
