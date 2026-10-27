
import unittest
from backend.order_book import OrderBook


class TestOrderBook(unittest.TestCase):
    def setUp(self):
        self.book = OrderBook()

    def test_matching_orders(self):
        self.book.submit_order("BUY", 100, 10)
        result = self.book.submit_order("SELL", 100, 6)

        self.assertEqual(result["filled_quantity"], 6)
        self.assertEqual(len(self.book.get_trades()), 1)
        self.assertEqual(
            self.book.get_trades()[0]["quantity"], 6
        )
        self.assertEqual(
            self.book.get_orders()["buys"][0]["quantity"], 4
        )

    def test_prices_do_not_match(self):
        self.book.submit_order("BUY", 100, 5)
        self.book.submit_order("SELL", 105, 5)

        self.assertEqual(len(self.book.get_trades()), 0)

    def test_invalid_side(self):
        with self.assertRaises(ValueError):
            self.book.submit_order("HOLD", 100, 5)

    def test_invalid_quantity(self):
        with self.assertRaises(ValueError):
            self.book.submit_order("BUY", 100, 0)

    def test_full_fill(self):
        self.book.submit_order("BUY", 100, 5)
        result = self.book.submit_order("SELL", 100, 5)

        self.assertEqual(result["remaining_quantity"], 0)
        self.assertEqual(len(self.book.get_orders()["buys"]), 0)
        self.assertEqual(len(self.book.get_orders()["sells"]), 0)


if __name__ == "__main__":
    unittest.main()
