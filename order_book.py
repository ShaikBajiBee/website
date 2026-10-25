
class OrderBook:
    def __init__(self):
        self.buys = []
        self.sells = []
        self.trades = []
        self.next_id = 1
        self.sequence = 0

    def submit_order(self, side, price, quantity):
        side = side.strip().upper()

        if side not in ("BUY", "SELL"):
            raise ValueError("Side must be BUY or SELL")

        if isinstance(price, bool) or not isinstance(price, (int, float)):
            raise ValueError("Price must be a number")

        if price <= 0 or not float(price) < float("inf"):
            raise ValueError("Price must be finite and positive")

        if isinstance(quantity, bool) or not isinstance(quantity, int):
            raise ValueError("Quantity must be a whole number")

        if quantity <= 0:
            raise ValueError("Quantity must be positive")

        order = {
            "order_id": self.next_id,
            "side": side,
            "price": float(price),
            "quantity": quantity,
            "timestamp": self.sequence
        }

        self.next_id += 1
        self.sequence += 1

        original_quantity = quantity
        opposite = self.sells if side == "BUY" else self.buys

        while order["quantity"] > 0 and opposite:
            opposite.sort(
                key=lambda item: (
                    item["price"] if side == "BUY"
                    else -item["price"],
                    item["timestamp"]
                )
            )

            best = opposite[0]

            if side == "BUY" and order["price"] < best["price"]:
                break

            if side == "SELL" and order["price"] > best["price"]:
                break

            traded_quantity = min(
                order["quantity"], best["quantity"]
            )

            buy_id = (
                order["order_id"] if side == "BUY"
                else best["order_id"]
            )
            sell_id = (
                best["order_id"] if side == "BUY"
                else order["order_id"]
            )

            self.trades.append({
                "buy_order_id": buy_id,
                "sell_order_id": sell_id,
                "price": best["price"],
                "quantity": traded_quantity
            })

            order["quantity"] -= traded_quantity
            best["quantity"] -= traded_quantity

            if best["quantity"] == 0:
                opposite.pop(0)

        if order["quantity"] > 0:
            own_side = self.buys if side == "BUY" else self.sells
            own_side.append(order.copy())

        return {
            "message": "Order processed successfully",
            "order_id": order["order_id"],
            "side": side,
            "price": float(price),
            "original_quantity": original_quantity,
            "remaining_quantity": order["quantity"],
            "filled_quantity": original_quantity - order["quantity"]
        }

    def get_orders(self):
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

    def get_trades(self):
        return [trade.copy() for trade in self.trades]
