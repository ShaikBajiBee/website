"""
ChronosMatch Zero-Copy High-Frequency Trading Core
==================================================
This module implements a zero-copy, binary-packed order processing pipeline
designed for microsecond-latency trade matching.

Key Principles:
1. Contiguous Binary Memory: Orders are written directly into a pre-allocated
   circular ring buffer using structured binary layouts (32 bytes per order).
2. Zero Object Allocation: Slicing and inspections use Python's `memoryview`
   and `struct.unpack_from`, avoiding dictionary and string allocations in the hot path.
3. Cache-friendly Layout: Fixed 32-byte alignment allows high L1/L2 CPU cache hit rates.
4. Microsecond/Nanosecond Precision: Hardware timestamps captured via `time.perf_counter_ns()`.
"""

import struct
import time
from typing import List, Dict, Tuple, Optional

# Binary Format Specification (32 bytes total):
# < : Little-endian
# c : side (1 byte, 'B'=Buy, 'S'=Sell)
# c : order_type (1 byte, 'L'=Limit, 'M'=Market)
# 2s: padding/alignment (2 bytes)
# Q : order_id (8 bytes uint64)
# d : price (8 bytes double float)
# I : quantity (4 bytes uint32)
# Q : timestamp_ns (8 bytes uint64 nanoseconds)
ORDER_FORMAT = "<cc2sQdIQ"
ORDER_STRUCT = struct.Struct(ORDER_FORMAT)
ORDER_SIZE = ORDER_STRUCT.size  # 32 bytes

assert ORDER_SIZE == 32, f"Expected 32 bytes, got {ORDER_SIZE}"

# Trade Binary Format (32 bytes):
# Q : trade_id (8 bytes)
# Q : buy_order_id (8 bytes)
# Q : sell_order_id (8 bytes)
# d : price (8 bytes double)
# I : quantity (4 bytes uint32)
# 4s: padding (4 bytes)
# (Optionally structured for zero-copy trade persistence)
TRADE_FORMAT = "<QQQdI4s"
TRADE_STRUCT = struct.Struct(TRADE_FORMAT)


class ZeroCopyOrderRingBuffer:
    """
    Pre-allocated contiguous memory circular ring buffer for incoming orders.
    Eliminates Python garbage collection pauses during high-frequency order bursts.
    """

    def __init__(self, capacity: int = 100_000):
        self.capacity = capacity
        self.buffer = bytearray(capacity * ORDER_SIZE)
        self.view = memoryview(self.buffer)
        self.write_index = 0
        self.read_index = 0
        self.total_orders = 0

    def push(self, side: str, order_type: str, order_id: int, price: float, quantity: int) -> int:
        """
        Packs and writes order directly into contiguous memory without heap allocations.
        Returns the offset in bytes where the order was stored.
        """
        offset = (self.write_index % self.capacity) * ORDER_SIZE
        side_byte = b'B' if side.upper() == 'BUY' else b'S'
        type_byte = b'M' if order_type.upper() == 'MARKET' else b'L'
        ts_ns = time.perf_counter_ns()

        ORDER_STRUCT.pack_into(
            self.buffer,
            offset,
            side_byte,
            type_byte,
            b'\x00\x00',
            order_id,
            float(price),
            int(quantity),
            ts_ns
        )

        self.write_index += 1
        self.total_orders += 1
        return offset

    def get_order_at(self, slot_index: int) -> Dict:
        """
        Decodes order from binary memory slot for inspection or API serialization.
        """
        offset = (slot_index % self.capacity) * ORDER_SIZE
        side_b, type_b, _, order_id, price, quantity, ts_ns = ORDER_STRUCT.unpack_from(self.buffer, offset)
        return {
            "order_id": order_id,
            "side": "BUY" if side_b == b'B' else "SELL",
            "order_type": "MARKET" if type_b == b'M' else "LIMIT",
            "price": round(price, 4),
            "quantity": quantity,
            "timestamp_ns": ts_ns
        }

    def clear(self):
        """Resets the ring buffer pointers."""
        self.write_index = 0
        self.read_index = 0
        self.total_orders = 0


class ZeroCopyBenchmark:
    """
    Benchmark suite comparing standard Python dictionary allocations
    against ChronosMatch Zero-Copy contiguous binary ring buffers.
    """

    @staticmethod
    def run_benchmark(num_orders: int = 25_000) -> Dict:
        """
        Executes a comparative latency and throughput benchmark.
        """
        # 1. Benchmark Standard Python Dict Allocation
        dict_latencies = []
        start_time_dict = time.perf_counter()
        simulated_store = []

        for i in range(num_orders):
            t0 = time.perf_counter_ns()
            order = {
                "order_id": i + 1,
                "side": "BUY" if i % 2 == 0 else "SELL",
                "order_type": "LIMIT",
                "price": 100.0 + (i % 50) * 0.5,
                "quantity": 10 + (i % 100),
                "timestamp_ns": time.perf_counter_ns()
            }
            simulated_store.append(order)
            t1 = time.perf_counter_ns()
            dict_latencies.append(t1 - t0)

        total_dict_time = time.perf_counter() - start_time_dict
        del simulated_store

        # 2. Benchmark Zero-Copy Ring Buffer
        ring_buffer = ZeroCopyOrderRingBuffer(capacity=num_orders + 1000)
        zero_copy_latencies = []
        start_time_zc = time.perf_counter()

        for i in range(num_orders):
            t0 = time.perf_counter_ns()
            ring_buffer.push(
                side="BUY" if i % 2 == 0 else "SELL",
                order_type="LIMIT",
                order_id=i + 1,
                price=100.0 + (i % 50) * 0.5,
                quantity=10 + (i % 100)
            )
            t1 = time.perf_counter_ns()
            zero_copy_latencies.append(t1 - t0)

        total_zc_time = time.perf_counter() - start_time_zc

        # Latency statistics calculations
        dict_latencies.sort()
        zero_copy_latencies.sort()

        def percentile(arr, pct):
            idx = int(len(arr) * pct)
            return arr[min(idx, len(arr) - 1)]

        dict_throughput = int(num_orders / total_dict_time)
        zc_throughput = int(num_orders / total_zc_time)
        speedup = round(total_dict_time / max(total_zc_time, 1e-9), 2)

        return {
            "num_orders": num_orders,
            "standard_dict": {
                "total_time_seconds": round(total_dict_time, 4),
                "throughput_orders_per_sec": dict_throughput,
                "avg_latency_ns": round(sum(dict_latencies) / len(dict_latencies), 1),
                "p50_latency_ns": percentile(dict_latencies, 0.50),
                "p95_latency_ns": percentile(dict_latencies, 0.95),
                "p99_latency_ns": percentile(dict_latencies, 0.99),
                "p50_latency_us": round(percentile(dict_latencies, 0.50) / 1000.0, 3),
                "p99_latency_us": round(percentile(dict_latencies, 0.99) / 1000.0, 3),
            },
            "zero_copy": {
                "total_time_seconds": round(total_zc_time, 4),
                "throughput_orders_per_sec": zc_throughput,
                "avg_latency_ns": round(sum(zero_copy_latencies) / len(zero_copy_latencies), 1),
                "p50_latency_ns": percentile(zero_copy_latencies, 0.50),
                "p95_latency_ns": percentile(zero_copy_latencies, 0.95),
                "p99_latency_ns": percentile(zero_copy_latencies, 0.99),
                "p50_latency_us": round(percentile(zero_copy_latencies, 0.50) / 1000.0, 3),
                "p99_latency_us": round(percentile(zero_copy_latencies, 0.99) / 1000.0, 3),
            },
            "speedup_factor": speedup,
            "memory_efficiency": "Contiguous pre-allocated 32-byte binary slots with zero GC churn"
        }
