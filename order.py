from decimal import Decimal, InvalidOperation


class Order:
    def __init__(self, order_id, side, price, quantity):
        if not isinstance(order_id, str) or not order_id.strip():
            raise ValueError("Order ID must be a non-empty string")

        if not isinstance(side, str):
            raise ValueError("Order side must be BUY or SELL")

        side = side.strip().upper()

        if side not in ("BUY", "SELL"):
            raise ValueError("Order side must be BUY or SELL")

        if isinstance(price, bool):
            raise ValueError("Price must be a positive number")

        try:
            price = Decimal(str(price))
        except (InvalidOperation, ValueError, TypeError):
            raise ValueError("Price must be a positive number") from None

        if not price.is_finite() or price <= 0:
            raise ValueError("Price must be positive and finite")

        if isinstance(quantity, bool) or not isinstance(quantity, int):
            raise ValueError("Quantity must be a positive integer")

        if quantity <= 0:
            raise ValueError("Quantity must be a positive integer")

        self.order_id = order_id.strip()
        self.side = side
        self.price = price
        self.quantity = quantity

    def __str__(self):
        return (
            f"Order(id={self.order_id}, "
            f"side={self.side}, "
            f"price={self.price}, "
            f"quantity={self.quantity})"
        )