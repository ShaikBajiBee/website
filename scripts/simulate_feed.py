"""
ChronosMatch Real-Time Market Feed Simulator
============================================
Generates live streaming order flow to demonstrate the matching engine,
Level 2 order depth, and trade execution tape in real-time.

Usage:
    python scripts/simulate_feed.py [--orders 50] [--interval 0.5] [--api http://127.0.0.1:8000]
"""

import argparse
import random
import time
import urllib.request
import json


def send_order(api_base: str, side: str, price: float, quantity: int):
    url = f"{api_base}/orders"
    payload = json.dumps({
        "side": side,
        "price": round(price, 2),
        "quantity": int(quantity),
        "order_type": "LIMIT"
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            order = data.get("order", {})
            status = order.get("status", "OPEN")
            filled = order.get("filled_quantity", 0)
            trades = len(data.get("new_trades", []))
            print(f"[{side}] ID #{order.get('order_id')} @ ₹{price:.2f} (Qty: {quantity}) -> {status} (Filled: {filled}, Trades: {trades})")
    except Exception as e:
        print(f"Error submitting order: {e}")


def run_simulation(api_base: str, count: int, interval: float):
    print("=" * 65)
    print("  ChronosMatch Live Market Feed Simulator")
    print(f"  Target API: {api_base}")
    print(f"  Orders: {count} | Interval: {interval}s")
    print("=" * 65)

    base_price = 150.00

    for i in range(count):
        # 50% Buy, 50% Sell
        side = "BUY" if random.random() < 0.5 else "SELL"
        
        # Price jitter around base price
        jitter = random.choice([-2.0, -1.5, -1.0, -0.5, 0.0, 0.5, 1.0, 1.5, 2.0])
        price = max(1.0, base_price + jitter)
        qty = random.choice([5, 10, 15, 20, 25, 50, 100])

        send_order(api_base, side, price, qty)
        time.sleep(interval)

    print("\nSimulation completed successfully!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ChronosMatch Market Simulator")
    parser.add_argument("--orders", type=int, default=30, help="Number of orders to simulate")
    parser.add_argument("--interval", type=float, default=0.3, help="Delay between orders (seconds)")
    parser.add_argument("--api", type=str, default="http://127.0.0.1:8000", help="ChronosMatch API Base URL")
    args = parser.parse_args()

    run_simulation(args.api, args.orders, args.interval)
