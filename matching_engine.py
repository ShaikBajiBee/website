class MatchingEngine:
    def __init__(self, order_book):
        self.order_book = order_book
        self.trades = []

    def match_orders(self):
        buys = self.order_book.buy_orders
        sells = self.order_book.sell_orders

        while buys and sells:
            best_buy = buys[0]
            best_sell = sells[0]

            if best_buy.price < best_sell.price:
                break

            quantity = min(best_buy.quantity, best_sell.quantity)

            trade = {
                "buy_order": best_buy.order_id,
                "sell_order": best_sell.order_id,
                "price": best_sell.price,
                "quantity": quantity,
            }

            self.trades.append(trade)

            best_buy.quantity -= quantity
            best_sell.quantity -= quantity

            if best_buy.quantity == 0:
                buys.pop(0)

            if best_sell.quantity == 0:
                sells.pop(0)

        return self.trades

    def show_trades(self):
        print("\nEXECUTED TRADES:")

        if not self.trades:
            print("No trades executed.")
            return

        for trade in self.trades:
            print(
                f"BUY {trade['buy_order']} matched with "
                f"SELL {trade['sell_order']} | "
                f"Price: {trade['price']} | "
                f"Quantity: {trade['quantity']}"
            )