from src.order import Order
from src.order_book import OrderBook
from src.matching_engine import MatchingEngine


def main():
    order_book = OrderBook()

    orders = [
        Order("B1", "BUY", "100.00", 10),
        Order("B2", "BUY", "105.00", 5),
        Order("S1", "SELL", "95.00", 6),
        Order("S2", "SELL", "98.00", 4),
        Order("S3", "SELL", "110.00", 3),
    ]

    for order in orders:
        order_book.add_order(order)

    print("CHRONOSMATCH - ORDER BOOK")
    order_book.show_orders()

    matching_engine = MatchingEngine(order_book)
    matching_engine.match_orders()

    matching_engine.show_trades()

    print("\nREMAINING ORDERS")
    order_book.show_orders()

    total_trades = len(matching_engine.trades)

    total_quantity = sum(
            trade["quantity"] for trade in matching_engine.trades
    )
    

    print(f"\nTotal trades executed: {total_trades}")
    print(f"Total quantity traded: {total_quantity}")


if __name__ == "__main__":
    main()