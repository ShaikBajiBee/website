"""
ChronosMatch Order Book & Matching Engine
=========================================
Implements a high-performance price-time priority (FIFO) matching engine.
Maintains limit order queues for Bids and Asks, supports Market and Limit orders,
partial fills, cancellations, and Level 2 market depth aggregation.
"""

from typing import Dict, List, Optional, Tuple, Any
from backend.zero_copy import ZeroCopyOrderRingBuffer


class OrderBook:
    def __init__(self, start_id: int = 1):
        self.buys: List[Dict[str, Any]] = []
        self.sells: List[Dict[str, Any]] = []
        self.trades: List[Dict[str, Any]] = []
        self.next_id: int = start_id
        self.sequence: int = 0
        self.trade_counter: int = 1

        # Integrated Zero-Copy Binary Ring Buffer
        self.ring_buffer = ZeroCopyOrderRingBuffer(capacity=100_000)

    def set_next_id(self, next_id: int) -> None:
        """Synchronizes order ID counter with the persistent database."""
        if next_id > self.next_id:
            self.next_id = next_id

    def set_next_trade_id(self, next_trade_id: int) -> None:
        """Synchronizes trade ID counter with the persistent database."""
        if next_trade_id > self.trade_counter:
            self.trade_counter = next_trade_id

    def submit_order(
        self,
        side: str,
        price: float,
        quantity: int,
        order_type: str = "LIMIT"
    ) -> Dict[str, Any]:
        """
        Submits and matches an order against the order book.
        Maintains strict price-time priority.
        """
        # 1. Input Validation
        if not isinstance(side, str):
            raise ValueError("Side must be BUY or SELL")

        side = side.strip().upper()
        if side not in ("BUY", "SELL"):
            raise ValueError("Side must be BUY or SELL")

        order_type = str(order_type).strip().upper()
        if order_type not in ("LIMIT", "MARKET"):
            order_type = "LIMIT"

        if isinstance(price, bool) or not isinstance(price, (int, float)):
            raise ValueError("Price must be a number")

        price = float(price)
        if price <= 0 or not price < float("inf"):
            raise ValueError("Price must be finite and positive")

        if isinstance(quantity, bool) or not isinstance(quantity, int):
            raise ValueError("Quantity must be a whole number")

        if quantity <= 0:
            raise ValueError("Quantity must be positive")

        # 2. Assign ID and push to Zero-Copy contiguous binary ring buffer
        order_id = self.next_id
        self.next_id += 1
        seq = self.sequence
        self.sequence += 1

        # Zero-copy memory buffer write
        self.ring_buffer.push(
            side=side,
            order_type=order_type,
            order_id=order_id,
            price=price,
            quantity=quantity
        )

        original_quantity = quantity
        remaining_quantity = quantity

        order = {
            "order_id": order_id,
            "side": side,
            "order_type": order_type,
            "price": price,
            "original_quantity": original_quantity,
            "quantity": remaining_quantity,
            "timestamp": seq,
        }

        # 3. Matching Loop
        opposite = self.sells if side == "BUY" else self.buys
        new_trades: List[Dict[str, Any]] = []
        resting_updates: List[Dict[str, Any]] = []

        while order["quantity"] > 0 and opposite:
            # Sort opposite book by Price-Time priority:
            # For BUY order looking at SELLS: lowest price first, earliest timestamp first.
            # For SELL order looking at BUYS: highest price first, earliest timestamp first.
            opposite.sort(
                key=lambda item: (
                    item["price"] if side == "BUY" else -item["price"],
                    item["timestamp"]
                )
            )

            best = opposite[0]

            # Price crossing check for Limit orders
            if order_type == "LIMIT":
                if side == "BUY" and order["price"] < best["price"]:
                    break  # Buyer unwilling to pay seller's asking price
                if side == "SELL" and order["price"] > best["price"]:
                    break  # Seller unwilling to sell at buyer's bid price

            # Match executed at the resting order's price
            matched_qty = min(order["quantity"], best["quantity"])
            trade_price = best["price"]

            buy_id = order["order_id"] if side == "BUY" else best["order_id"]
            sell_id = best["order_id"] if side == "BUY" else order["order_id"]

            trade_record = {
                "trade_id": self.trade_counter,
                "buy_order_id": buy_id,
                "sell_order_id": sell_id,
                "price": trade_price,
                "quantity": matched_qty,
            }
            self.trade_counter += 1

            self.trades.append(trade_record)
            new_trades.append(trade_record)

            order["quantity"] -= matched_qty
            best["quantity"] -= matched_qty

            resting_updates.append({
                "order_id": best["order_id"],
                "remaining_quantity": best["quantity"],
                "status": "FILLED" if best["quantity"] == 0 else "PARTIALLY_FILLED"
            })

            if best["quantity"] == 0:
                opposite.pop(0)

        # 4. If any unfilled quantity remains and it is a LIMIT order, rest in the book
        if order["quantity"] > 0 and order_type == "LIMIT":
            own_side = self.buys if side == "BUY" else self.sells
            own_side.append(order.copy())

        filled_quantity = original_quantity - order["quantity"]
        final_status = (
            "FILLED" if order["quantity"] == 0
            else "PARTIALLY_FILLED" if filled_quantity > 0
            else "OPEN"
        )

        return {
            "message": "Order processed successfully",
            "order_id": order["order_id"],
            "side": side,
            "order_type": order_type,
            "price": price,
            "original_quantity": original_quantity,
            "remaining_quantity": order["quantity"],
            "filled_quantity": filled_quantity,
            "status": final_status,
            "trades": new_trades,
            "resting_updates": resting_updates
        }

    def cancel_order(self, order_id: int) -> Optional[Dict[str, Any]]:
        """Cancels a pending resting order by ID."""
        for side_list in (self.buys, self.sells):
            for i, order in enumerate(side_list):
                if order["order_id"] == order_id:
                    cancelled = side_list.pop(i)
                    return cancelled
        return None

    def get_orders(self) -> Dict[str, List[Dict[str, Any]]]:
        """Returns sorted snapshot of active pending orders."""
        return {
            "buys": [
                order.copy()
                for order in sorted(
                    self.buys,
                    key=lambda o: (-o["price"], o["timestamp"])
                )
            ],
            "sells": [
                order.copy()
                for order in sorted(
                    self.sells,
                    key=lambda o: (o["price"], o["timestamp"])
                )
            ]
        }

    def get_trades(self) -> List[Dict[str, Any]]:
        """Returns snapshot of completed trades."""
        return [trade.copy() for trade in self.trades]

    def get_market_depth(self, levels: int = 10) -> Dict[str, Any]:
        """
        Aggregates pending orders into Level 2 Market Depth (bids and asks by price level).
        """
        # Aggregate bids (grouped by price, descending)
        bid_map: Dict[float, int] = {}
        for o in self.buys:
            p = o["price"]
            bid_map[p] = bid_map.get(p, 0) + o["quantity"]

        bids = [
            {"price": price, "quantity": qty}
            for price, qty in sorted(bid_map.items(), key=lambda x: -x[0])
        ][:levels]

        # Aggregate asks (grouped by price, ascending)
        ask_map: Dict[float, int] = {}
        for o in self.sells:
            p = o["price"]
            ask_map[p] = ask_map.get(p, 0) + o["quantity"]

        asks = [
            {"price": price, "quantity": qty}
            for price, qty in sorted(ask_map.items(), key=lambda x: x[0])
        ][:levels]

        best_bid = bids[0]["price"] if bids else None
        best_ask = asks[0]["price"] if asks else None
        spread = round(best_ask - best_bid, 4) if (best_bid is not None and best_ask is not None) else None

        return {
            "bids": bids,
            "asks": asks,
            "best_bid": best_bid,
            "best_ask": best_ask,
            "spread": spread
        }

    def reset(self, start_id: int = 1):
        """Clears all orders and trades (used in testing and benchmarks)."""
        self.buys.clear()
        self.sells.clear()
        self.trades.clear()
        self.next_id = start_id
        self.sequence = 0
        self.trade_counter = 1
        self.ring_buffer.clear()
