"""
ChronosMatch Database and API Integration Test Suite
====================================================
"""

import unittest
from backend.database import (
    initialize_database,
    get_max_order_id,
    save_order_and_matches,
    get_saved_orders,
    get_saved_trades,
    mark_order_cancelled,
    get_daily_analytics,
    record_benchmark,
    get_latest_benchmark,
)
from backend.order_book import OrderBook
from backend.zero_copy import ZeroCopyBenchmark


class TestDatabaseAndIntegration(unittest.TestCase):
    def setUp(self):
        initialize_database()
        self.start_id = get_max_order_id() + 1
        self.book = OrderBook(start_id=self.start_id)

    def test_database_initialization_and_max_id(self):
        max_id = get_max_order_id()
        self.assertIsInstance(max_id, int)
        self.assertGreaterEqual(max_id, 0)

    def test_save_and_retrieve_order(self):
        result = self.book.submit_order("BUY", 150.0, 20)
        save_order_and_matches(result, result["resting_updates"], result["trades"])

        orders = get_saved_orders(limit=10)
        self.assertGreater(len(orders), 0)
        matched = [o for o in orders if o["order_id"] == result["order_id"]]
        self.assertEqual(len(matched), 1)
        self.assertEqual(matched[0]["side"], "BUY")

    def test_trade_persistence_on_match(self):
        res1 = self.book.submit_order("BUY", 200.0, 10)
        save_order_and_matches(res1, res1["resting_updates"], res1["trades"])

        res2 = self.book.submit_order("SELL", 195.0, 10)
        save_order_and_matches(res2, res2["resting_updates"], res2["trades"])

        trades = get_saved_trades(limit=5)
        self.assertGreater(len(trades), 0)
        self.assertEqual(trades[0]["quantity"], 10)
        self.assertEqual(trades[0]["price"], 200.0)

    def test_cancel_order_in_db(self):
        res = self.book.submit_order("SELL", 500.0, 15)
        save_order_and_matches(res, res["resting_updates"], res["trades"])

        success = mark_order_cancelled(res["order_id"])
        self.assertTrue(success)

    def test_daily_analytics(self):
        stats = get_daily_analytics()
        self.assertIn("daily_order_count", stats)
        self.assertIn("daily_trade_count", stats)
        self.assertIn("daily_quantity_traded", stats)
        self.assertIn("daily_turnover_value", stats)

    def test_benchmark_persistence(self):
        bench = ZeroCopyBenchmark.run_benchmark(num_orders=500)
        record_benchmark(bench)
        latest = get_latest_benchmark()
        self.assertIsNotNone(latest)
        self.assertEqual(latest["num_orders"], 500)


if __name__ == "__main__":
    unittest.main()
