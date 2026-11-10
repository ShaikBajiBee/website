"""
ChronosMatch High-Frequency Trading API
=======================================
FastAPI server exposing REST endpoints for the order matching engine,
Level 2 market depth, daily trading analytics, zero-copy performance benchmarks,
and order cancellation.
"""

import logging
import sqlite3
from pathlib import Path
from typing import Optional, Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, ConfigDict

from backend.order_book import OrderBook
from backend.zero_copy import ZeroCopyBenchmark
from backend.database import (
    initialize_database,
    get_max_order_id,
    get_max_trade_id,
    save_order_and_matches,
    get_saved_orders,
    get_saved_trades,
    mark_order_cancelled,
    get_daily_analytics,
    record_benchmark,
    get_latest_benchmark,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="ChronosMatch: Zero-Copy High-Frequency Trading Engine",
    description="Microsecond-latency order matching engine with zero-copy binary ring buffers.",
    version="2.0.0"
)

# Enable CORS for local web servers (Live Server 5500, Vite 5173, Next 3000, and local 8000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://127.0.0.1:8000",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://localhost:3000",
        "*",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount frontend directory for direct dashboard access
BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

if FRONTEND_DIR.exists():
    app.mount("/dashboard", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="dashboard")

book = OrderBook()


@app.on_event("startup")
def startup():
    initialize_database()
    max_order_id = get_max_order_id()
    max_trade_id = get_max_trade_id()
    book.set_next_id(max_order_id + 1)
    book.set_next_trade_id(max_trade_id + 1)
    logger.info(f"ChronosMatch initialized. Next Order ID: {max_order_id + 1}, Next Trade ID: {max_trade_id + 1}")


class OrderRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    side: str
    price: float = Field(gt=0, allow_inf_nan=False)
    quantity: int = Field(gt=0, strict=True)
    order_type: Optional[str] = "LIMIT"


class BenchmarkRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    num_orders: int = Field(default=25_000, ge=1_000, le=100_000)


@app.get("/")
def home():
    return {
        "message": "ChronosMatch API is running",
        "status": "success",
        "engine": "ChronosMatch Zero-Copy High-Frequency Trading Engine",
        "dashboard_url": "/dashboard/",
        "endpoints": {
            "dashboard": "/dashboard/",
            "orders": "/orders",
            "trades": "/trades",
            "market_depth": "/book/depth",
            "daily_stats": "/stats/daily",
            "benchmark_run": "/benchmark/run (POST)",
            "benchmark_latest": "/benchmark/latest",
            "interactive_docs": "/docs"
        }
    }


@app.post("/orders")
def create_order(order: OrderRequest):
    side = order.side.strip().upper()
    if side not in ("BUY", "SELL"):
        raise HTTPException(
            status_code=400,
            detail="Side must be BUY or SELL",
        )

    order_type = (order.order_type or "LIMIT").strip().upper()
    if order_type not in ("LIMIT", "MARKET"):
        order_type = "LIMIT"

    try:
        # Match order using Zero-Copy enabled OrderBook
        result = book.submit_order(
            side=side,
            price=order.price,
            quantity=order.quantity,
            order_type=order_type,
        )

        # Atomic SQLite persistence
        save_order_and_matches(
            order_result=result,
            resting_updates=result.get("resting_updates", []),
            new_trades=result.get("trades", [])
        )

        return {
            "message": "Order submitted successfully",
            "order_id": result["order_id"],
            "order": result,
            "side": result["side"],
            "price": result["price"],
            "original_quantity": result["original_quantity"],
            "filled_quantity": result["filled_quantity"],
            "remaining_quantity": result["remaining_quantity"],
            "status": result["status"],
            "new_trades": result.get("trades", []),
        }

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    except sqlite3.IntegrityError:
        logger.exception("Database integrity error while saving order")
        raise HTTPException(
            status_code=500,
            detail=(
                "Could not save order because of a database integrity error. "
                "Order ID sequence synchronized."
            ),
        )

    except Exception as exc:
        logger.exception("Unexpected error while submitting order")
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected server error while submitting order: {str(exc)}",
        )


@app.get("/orders")
def get_orders():
    return {
        "order_book": book.get_orders(),
        "history": get_saved_orders(limit=100),
    }


@app.delete("/orders/{order_id}")
def cancel_order(order_id: int):
    cancelled = book.cancel_order(order_id)
    if not cancelled:
        raise HTTPException(
            status_code=404,
            detail=f"Order #{order_id} not found in active order book"
        )
    mark_order_cancelled(order_id)
    return {
        "message": f"Order #{order_id} cancelled successfully",
        "order": cancelled
    }


@app.get("/trades")
def get_trades():
    return get_saved_trades(limit=100)


@app.get("/book/depth")
def get_market_depth(levels: int = 10):
    return book.get_market_depth(levels=levels)


@app.get("/stats/daily")
def get_daily_stats():
    return get_daily_analytics()


@app.post("/benchmark/run")
def run_benchmark(request_data: BenchmarkRequest = BenchmarkRequest()):
    try:
        results = ZeroCopyBenchmark.run_benchmark(num_orders=request_data.num_orders)
        record_benchmark(results)
        return {
            "status": "success",
            "benchmark": results
        }
    except Exception as exc:
        logger.exception("Benchmark execution failed")
        raise HTTPException(
            status_code=500,
            detail=f"Benchmark execution failed: {str(exc)}"
        )


@app.get("/benchmark/latest")
def get_latest_benchmark_metrics():
    latest = get_latest_benchmark()
    if not latest:
        # Generate initial benchmark if none recorded yet
        initial = ZeroCopyBenchmark.run_benchmark(num_orders=10_000)
        record_benchmark(initial)
        return initial
    return latest
