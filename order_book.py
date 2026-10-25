from .order import Order


class OrderBook:
    def __init__(self):
        self.buy_orders = []
        self.sell_orders = []
        self.order_ids = set()

    def add_order(self, order):
        if not isinstance(order, Order):
            raise TypeError("Only Order objects can be added")

        if order.order_id in self.order_ids:
            raise ValueError(f"Duplicate order ID: {order.order_id}")

        if order.side == "BUY":
            self.buy_orders.append(order)
            self.buy_orders.sort(key=lambda order: -order.price)

        elif order.side == "SELL":
            self.sell_orders.append(order)
            self.sell_orders.sort(key=lambda order: order.price)

        else:
            raise ValueError("Order side must be BUY or SELL")

        self.order_ids.add(order.order_id)

    def show_orders(self):
        print("\nBUY ORDERS:")
        for order in self.buy_orders:
            print(order)

        print("\nSELL ORDERS:")
        for order in self.sell_orders:
            print(order)