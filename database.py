"""
ChronosMatch SQLite Database Persistence Layer
==============================================
Provides ACID-compliant transactional persistence for orders, trades,
and performance benchmark metrics with automatic schema migrations.
"""

import sqlite3
from pathlib import Path
from typing import Dict, List, Any, Optional
from contextlib import contextmanager

DB_PATH = Path(__file__).resolve().parent / "chronosmatch.db"


@contextmanager
def get_db():
    """Context manager that handles commit/rollback and ensures the connection is closed."""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def initialize_database():
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS orders (
                order_id INTEGER PRIMARY KEY,
                side TEXT NOT NULL,
                order_type TEXT NOT NULL DEFAULT 'LIMIT',
                price REAL NOT NULL,
                original_quantity INTEGER NOT NULL,
                filled_quantity INTEGER NOT NULL DEFAULT 0,
                remaining_quantity INTEGER NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS trades (
                trade_id INTEGER PRIMARY KEY AUTOINCREMENT,
                buy_order_id INTEGER NOT NULL,
                sell_order_id INTEGER NOT NULL,
                price REAL NOT NULL,
                quantity INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS benchmarks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                num_orders INTEGER NOT NULL,
                dict_ops INTEGER NOT NULL,
                zc_ops INTEGER NOT NULL,
                speedup REAL NOT NULL,
                zc_p50_us REAL NOT NULL,
                zc_p99_us REAL NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
            CREATE INDEX IF NOT EXISTS idx_trades_created_at ON trades(created_at);
        """)

        # Migration check: Ensure existing database schema has new columns
        cursor = conn.execute("PRAGMA table_info(orders)")
        existing_cols = {row["name"] for row in cursor.fetchall()}

        if "order_type" not in existing_cols:
            conn.execute("ALTER TABLE orders ADD COLUMN order_type TEXT NOT NULL DEFAULT 'LIMIT'")
        if "updated_at" not in existing_cols:
            conn.execute("ALTER TABLE orders ADD COLUMN updated_at TEXT DEFAULT ''")


def get_max_order_id() -> int:
    """Returns the highest order ID in the database to prevent duplicate key collisions."""
    with get_db() as conn:
        row = conn.execute("SELECT COALESCE(MAX(order_id), 0) AS max_id FROM orders").fetchone()
        return row["max_id"] if row else 0


def get_max_trade_id() -> int:
    """Returns the highest trade ID in the database."""
    with get_db() as conn:
        row = conn.execute("SELECT COALESCE(MAX(trade_id), 0) AS max_id FROM trades").fetchone()
        return row["max_id"] if row else 0


def save_order_and_matches(
    order_result: Dict[str, Any],
    resting_updates: List[Dict[str, Any]],
    new_trades: List[Dict[str, Any]]
):
    """
    Atomically updates matched resting orders, inserts the incoming order,
    and records all newly executed trades in a single SQLite transaction.
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # 1. Update resting orders that were partially or fully filled
        for update in resting_updates:
            cursor.execute("""
                UPDATE orders
                SET remaining_quantity = ?,
                    filled_quantity = original_quantity - ?,
                    status = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE order_id = ?
            """, (
                update["remaining_quantity"],
                update["remaining_quantity"],
                update["status"],
                update["order_id"]
            ))

        # 2. Insert or replace incoming order
        cursor.execute("""
            INSERT OR REPLACE INTO orders (
                order_id, side, order_type, price, original_quantity,
                filled_quantity, remaining_quantity, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            order_result["order_id"],
            order_result["side"],
            order_result.get("order_type", "LIMIT"),
            order_result["price"],
            order_result["original_quantity"],
            order_result["filled_quantity"],
            order_result["remaining_quantity"],
            order_result["status"]
        ))

        # 3. Insert newly executed trades
        if new_trades:
            cursor.executemany("""
                INSERT INTO trades (
                    buy_order_id, sell_order_id, price, quantity
                ) VALUES (?, ?, ?, ?)
            """, [
                (
                    t["buy_order_id"],
                    t["sell_order_id"],
                    t["price"],
                    t["quantity"]
                )
                for t in new_trades
            ])


def save_order(result: Dict[str, Any]):
    """Compatibility helper to save a single order."""
    with get_db() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO orders (
                order_id, side, order_type, price, original_quantity,
                filled_quantity, remaining_quantity, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            result["order_id"],
            result["side"],
            result.get("order_type", "LIMIT"),
            result["price"],
            result["original_quantity"],
            result["filled_quantity"],
            result["remaining_quantity"],
            result.get("status", "OPEN")
        ))


def save_new_trades(trades: List[Dict[str, Any]]):
    """Compatibility helper to save new trade records."""
    if not trades:
        return
    with get_db() as conn:
        conn.executemany("""
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


def mark_order_cancelled(order_id: int) -> bool:
    """Updates order status to CANCELLED in database."""
    with get_db() as conn:
        cursor = conn.execute("""
            UPDATE orders
            SET status = 'CANCELLED', updated_at = CURRENT_TIMESTAMP
            WHERE order_id = ? AND status IN ('OPEN', 'PARTIALLY_FILLED')
        """, (order_id,))
        return cursor.rowcount > 0


def get_saved_orders(limit: int = 100) -> List[Dict[str, Any]]:
    with get_db() as conn:
        rows = conn.execute("""
            SELECT * FROM orders ORDER BY order_id DESC LIMIT ?
        """, (limit,)).fetchall()
        return [dict(row) for row in rows]


def get_saved_trades(limit: int = 100) -> List[Dict[str, Any]]:
    with get_db() as conn:
        rows = conn.execute("""
            SELECT trade_id, buy_order_id, sell_order_id,
                   price, quantity, created_at
            FROM trades ORDER BY trade_id DESC LIMIT ?
        """, (limit,)).fetchall()
        return [dict(row) for row in rows]


def get_daily_analytics() -> Dict[str, Any]:
    """Computes daily aggregated trading performance statistics."""
    with get_db() as conn:
        order_row = conn.execute("""
            SELECT COUNT(*) AS total_orders,
                   COALESCE(SUM(original_quantity), 0) AS total_order_qty
            FROM orders
            WHERE DATE(created_at) = DATE('now', 'localtime')
        """).fetchone()

        trade_row = conn.execute("""
            SELECT COUNT(*) AS total_trades,
                   COALESCE(SUM(quantity), 0) AS total_traded_qty,
                   COALESCE(SUM(price * quantity), 0.0) AS total_turnover
            FROM trades
            WHERE DATE(created_at) = DATE('now', 'localtime')
        """).fetchone()

        return {
            "daily_order_count": order_row["total_orders"] if order_row else 0,
            "daily_trade_count": trade_row["total_trades"] if trade_row else 0,
            "daily_quantity_traded": trade_row["total_traded_qty"] if trade_row else 0,
            "daily_turnover_value": round(trade_row["total_turnover"], 2) if trade_row else 0.0
        }


def record_benchmark(data: Dict[str, Any]):
    """Records zero-copy benchmark metrics."""
    with get_db() as conn:
        conn.execute("""
            INSERT INTO benchmarks (
                num_orders, dict_ops, zc_ops, speedup, zc_p50_us, zc_p99_us
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            data["num_orders"],
            data["standard_dict"]["throughput_orders_per_sec"],
            data["zero_copy"]["throughput_orders_per_sec"],
            data["speedup_factor"],
            data["zero_copy"]["p50_latency_us"],
            data["zero_copy"]["p99_latency_us"]
        ))


def get_latest_benchmark() -> Optional[Dict[str, Any]]:
    """Returns the most recent benchmark run."""
    with get_db() as conn:
        row = conn.execute("""
            SELECT * FROM benchmarks ORDER BY id DESC LIMIT 1
        """).fetchone()
        return dict(row) if row else None
