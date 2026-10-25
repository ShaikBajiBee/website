
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ConfigDict

from backend.order_book import OrderBook
from backend.database import (
    initialize_database,
    save_order,
    save_new_trades,
    get_saved_orders,
    get_saved_trades,
)

app = FastAPI(title="ChronosMatch Trading Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

book = OrderBook()


@app.on_event("startup")
def startup():
    initialize_database()


class OrderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    side: str
    price: float = Field(gt=0, allow_inf_nan=False)
    quantity: int = Field(gt=0, strict=True)


@app.get("/")
def home():
    return {
        "message": "ChronosMatch API is running",
        "status": "success",
    }


@app.post("/orders")
def create_order(order: OrderRequest):
    side = order.side.strip().upper()

    if side not in ("BUY", "SELL"):
        raise HTTPException(
            status_code=400,
            detail="Side must be BUY or SELL",
        )

    try:
        previous_trade_count = len(book.trades)

        result = book.submit_order(
            side,
            order.price,
            order.quantity,
        )

        save_order(result)

        new_trades = book.trades[previous_trade_count:]
        save_new_trades(new_trades)

        return result

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )


@app.get("/orders")
def get_orders():
    return {
        "order_book": book.get_orders(),
        "history": get_saved_orders(),
    }


@app.get("/trades")
def get_trades():
    return get_saved_trades()
