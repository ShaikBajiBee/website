"""
ChronosMatch Comprehensive Unit Test Suite
==========================================
Tests the core OrderBook, Zero-Copy Ring Buffer, Price-Time priority matching,
partial fills, cancellations, and market depth calculations.
"""

import unittest
from backend.order_book import OrderBook
from backend.zero_copy import (
    ZeroCopyOrderRingBuffer,
    ZeroCopyBenchmark,
    ORDER_STRUCT,
    ORDER_SIZE
)


class TestOrderBook(unittest.TestCase):
    def setUp(self):
        self.book = OrderBook()

    def test_matching_orders(self):
        self.book.submit_order("BUY", 100, 10)
        result = self.book.submit_order("SELL", 100, 6)

        self.assertEqual(result["filled_quantity"], 6)
        self.assertEqual(len(self.book.get_trades()), 1)
        self.assertEqual(self.book.get_trades()[0]["quantity"], 6)
        self.assertEqual(self.book.get_orders()["buys"][0]["quantity"], 4)

    def test_prices_do_not_match(self):
        self.book.submit_order("BUY", 100, 5)
        self.book.submit_order("SELL", 105, 5)

        self.assertEqual(len(self.book.get_trades()), 0)
        self.assertEqual(len(self.book.get_orders()["buys"]), 1)
        self.assertEqual(len(self.book.get_orders()["sells"]), 1)

    def test_invalid_side(self):
        with self.assertRaises(ValueError):
            self.book.submit_order("HOLD", 100, 5)

    def test_invalid_quantity(self):
        with self.assertRaises(ValueError):
            self.book.submit_order("BUY", 100, 0)
        with self.assertRaises(ValueError):
            self.book.submit_order("BUY", 100, -5)
        with self.assertRaises(ValueError):
            self.book.submit_order("BUY", 100, "ten")

    def test_invalid_price(self):
        with self.assertRaises(ValueError):
            self.book.submit_order("BUY", 0, 10)
        with self.assertRaises(ValueError):
            self.book.submit_order("BUY", -50.0, 10)
        with self.assertRaises(ValueError):
            self.book.submit_order("BUY", float("nan"), 10)

    def test_full_fill(self):
        self.book.submit_order("BUY", 100, 5)
        result = self.book.submit_order("SELL", 100, 5)

        self.assertEqual(result["remaining_quantity"], 0)
        self.assertEqual(result["filled_quantity"], 5)
        self.assertEqual(len(self.book.get_orders()["buys"]), 0)
        self.assertEqual(len(self.book.get_orders()["sells"]), 0)

    def test_price_time_priority(self):
        # Submit two BUY orders at the same price
        self.book.submit_order("BUY", 100.0, 10)  # Order 1 (earlier)
        self.book.submit_order("BUY", 100.0, 15)  # Order 2 (later)

        # Incoming SELL for 10 shares at 100.0
        result = self.book.submit_order("SELL", 100.0, 10)

        # Order 1 must be filled first due to time priority (FIFO)
        trades = self.book.get_trades()
        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0]["buy_order_id"], 1)
        self.assertEqual(trades[0]["quantity"], 10)

        # Order 2 must remain untouched
        buys = self.book.get_orders()["buys"]
        self.assertEqual(len(buys), 1)
        self.assertEqual(buys[0]["order_id"], 2)
        self.assertEqual(buys[0]["quantity"], 15)

    def test_best_price_priority(self):
        # Buyer A bids 99, Buyer B bids 101
        self.book.submit_order("BUY", 99.0, 10)
        self.book.submit_order("BUY", 101.0, 10)

        # Seller offers 10 at 95.0
        # Matching engine must match with Buyer B (101.0, higher price)
        result = self.book.submit_order("SELL", 95.0, 10)
        trades = self.book.get_trades()

        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0]["buy_order_id"], 2)
        self.assertEqual(trades[0]["price"], 101.0)  # Executed at resting price

    def test_order_cancellation(self):
        res = self.book.submit_order("BUY", 150.0, 20)
        order_id = res["order_id"]

        self.assertEqual(len(self.book.get_orders()["buys"]), 1)
        cancelled = self.book.cancel_order(order_id)
        self.assertIsNotNone(cancelled)
        self.assertEqual(cancelled["order_id"], order_id)
        self.assertEqual(len(self.book.get_orders()["buys"]), 0)

        # Cancel non-existent
        self.assertIsNone(self.book.cancel_order(9999))

    def test_market_depth(self):
        self.book.submit_order("BUY", 100.0, 10)
        self.book.submit_order("BUY", 100.0, 15)
        self.book.submit_order("BUY", 99.0, 20)
        self.book.submit_order("SELL", 105.0, 50)
        self.book.submit_order("SELL", 106.0, 30)

        depth = self.book.get_market_depth(levels=5)
        self.assertEqual(len(depth["bids"]), 2)
        self.assertEqual(depth["bids"][0]["price"], 100.0)
        self.assertEqual(depth["bids"][0]["quantity"], 25)  # 10 + 15 aggregated
        self.assertEqual(depth["best_bid"], 100.0)
        self.assertEqual(depth["best_ask"], 105.0)
        self.assertEqual(depth["spread"], 5.0)


class TestZeroCopyEngine(unittest.TestCase):
    def test_binary_pack_and_unpack(self):
        ring = ZeroCopyOrderRingBuffer(capacity=100)
        offset = ring.push("BUY", "LIMIT", 42, 123.45, 1000)

        self.assertEqual(offset, 0)
        order = ring.get_order_at(0)
        self.assertEqual(order["order_id"], 42)
        self.assertEqual(order["side"], "BUY")
        self.assertEqual(order["order_type"], "LIMIT")
        self.assertEqual(order["price"], 123.45)
        self.assertEqual(order["quantity"], 1000)
        self.assertGreater(order["timestamp_ns"], 0)

    def test_ring_buffer_wrap_around(self):
        ring = ZeroCopyOrderRingBuffer(capacity=4)
        for i in range(10):
            ring.push("SELL", "LIMIT", i + 1, 10.0 + i, 5)

        self.assertEqual(ring.total_orders, 10)
        # Check last order written at slot 9 (9 % 4 = 1)
        latest = ring.get_order_at(1)
        self.assertEqual(latest["order_id"], 10)

    def test_zero_copy_benchmark_execution(self):
        res = ZeroCopyBenchmark.run_benchmark(num_orders=1000)
        self.assertIn("standard_dict", res)
        self.assertIn("zero_copy", res)
        self.assertGreater(res["zero_copy"]["throughput_orders_per_sec"], 0)
        self.assertGreater(res["speedup_factor"], 0)


if __name__ == "__main__":
    unittest.main()
