# ChronosMatch: Zero-Copy High-Frequency Trading Engine
## Technical Specification & System Architecture Documentation

**Candidate:** Shaik Baji Bee  
**Role:** Data Associate L1. Intern (Python Development)  
**Organization:** Infotact Solutions  
**Project Ref:** ITS/PY/1126  
**Date of Submission:** 10 November 2026  

---

## 1. Executive Overview

**ChronosMatch** is a microsecond-latency order matching engine and real-time electronic trading dashboard designed for high-throughput algorithmic execution. Modern electronic exchanges (such as NASDAQ, CME, and leading cryptocurrency exchanges) operate in ultra-low latency regimes where garbage collection pauses, pointer chasing, and heap allocations introduce fatal tail latency jitter.

ChronosMatch solves this challenge through a **Zero-Copy Contiguous Binary Architecture** combined with a deterministic **Price-Time Priority (FIFO)** order book and an **ACID-compliant SQLite persistence pipeline**.

---

## 2. System Architecture

The following diagram illustrates the flow of an order from transmission down to hardware memory layout and database persistence:

```
[ Web Trading UI / Algorithmic Feed ]
                │
                ▼ (HTTP POST /orders)
┌─────────────────────────────────────────────────────────────┐
│                       FastAPI Gateway                       │
│    - Pydantic v2 Request Validation                         │
│    - Non-blocking Asynchronous Routing                      │
└───────────────┬─────────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────────────────┐
│               ChronosMatch Zero-Copy Engine                 │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │     Zero-Copy Binary Ring Buffer (100K Slots)         │  │
│  │   [ 32B Slot 0 ][ 32B Slot 1 ][ 32B Slot 2 ] ...     │  │
│  │   Struct: <cc2sQdIQ  (memoryview + pack_into)         │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │             Price-Time Priority Order Book            │  │
│  │   - Bids: Sorted Descending Price + Ascending TS      │  │
│  │   - Asks: Sorted Ascending Price + Ascending TS       │  │
│  │   - FIFO Matching Loop                                │  │
│  │   - L2 Market Depth Aggregator                        │  │
│  └───────────────────────────────────────────────────────┘  │
└───────────────┬─────────────────────────────────────────────┘
                │
                ▼ (Atomic Transaction: Commit / Rollback)
┌─────────────────────────────────────────────────────────────┐
│                 SQLite Persistence Layer                    │
│   - Orders Table (Order Lifecycle & Auditing)               │
│   - Trades Table (Execution Fill History)                   │
│   - Benchmarks Table (Latency Profiling Metrics)            │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Zero-Copy Binary Ring Buffer Specification

### 3.1 Memory Layout
To eliminate heap fragmentation and Python Garbage Collector (GC) latency spikes, ChronosMatch pre-allocates a contiguous binary buffer in memory:

- **Buffer Size:** `100,000 slots × 32 bytes = 3.2 MB`
- **Memory Structure:** Contiguous `bytearray` sliced via `memoryview`
- **CPU Alignment:** 32-byte cache-line friendly alignment

```
Binary Layout: <cc2sQdIQ (32 bytes Little-Endian)
┌───────┬───────┬──────────┬──────────────┬──────────────┬──────────┬──────────────┐
│ Side  │ Type  │ Padding  │   Order ID   │    Price     │ Quantity │ Timestamp NS │
│ (1 B) │ (1 B) │  (2 B)   │   (8 B, u64) │ (8 B, float) │(4 B, u32)│  (8 B, u64)  │
└───────┴───────┴──────────┴──────────────┴──────────────┴──────────┴──────────────┘
 0       1       2          4              12             20         24           32
```

### 3.2 Elimination of Object Copies
1. **Network Ingestion:** Incoming parameters are packed directly into the contiguous buffer slot using `struct.pack_into()` without intermediate string encoding.
2. **Hardware Timestamps:** Clock cycles are recorded in nanoseconds via `time.perf_counter_ns()`.
3. **No Garbage Collection:** The circular buffer reuses slots cyclically via modulo arithmetic `(index % capacity)`, resulting in zero allocations in the critical hot path.

---

## 4. Matching Engine Logic & Algorithms

### 4.1 Price-Time Priority (FIFO)
ChronosMatch guarantees strict price and time priority:
1. **Price Priority:**
   - Buyers offering a higher price take priority over buyers offering a lower price.
   - Sellers asking for a lower price take priority over sellers asking for a higher price.
2. **Time Priority:**
   - For orders resting at the identical price level, orders submitted earlier take priority over later orders.

### 4.2 Trade Price Determination
Trades are executed at the **resting order's price** (the passive maker order already in the book). The aggressive taker order pays or receives the maker's stated limit price.

### 4.3 Pseudocode for Order Matching
```python
def match(order, opposite_book):
    while order.quantity > 0 and len(opposite_book) > 0:
        best_opposite = opposite_book[0]
        
        # Check price crossing condition
        if order.side == "BUY" and order.price < best_opposite.price:
            break
        if order.side == "SELL" and order.price > best_opposite.price:
            break
            
        trade_qty = min(order.quantity, best_opposite.quantity)
        trade_price = best_opposite.price
        
        execute_trade(buyer, seller, trade_price, trade_qty)
        
        order.quantity -= trade_qty
        best_opposite.quantity -= trade_qty
        
        if best_opposite.quantity == 0:
            opposite_book.pop(0)
            
    if order.quantity > 0 and order.order_type == "LIMIT":
        own_book.append(order)
```

---

## 5. Database Schema & Persistence

### 5.1 Tables
```sql
CREATE TABLE orders (
    order_id INTEGER PRIMARY KEY,
    side TEXT NOT NULL,
    order_type TEXT NOT NULL DEFAULT 'LIMIT',
    price REAL NOT NULL,
    original_quantity INTEGER NOT NULL,
    filled_quantity INTEGER NOT NULL DEFAULT 0,
    remaining_quantity INTEGER NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE trades (
    trade_id INTEGER PRIMARY KEY AUTOINCREMENT,
    buy_order_id INTEGER NOT NULL,
    sell_order_id INTEGER NOT NULL,
    price REAL NOT NULL,
    quantity INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE benchmarks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    num_orders INTEGER NOT NULL,
    dict_ops INTEGER NOT NULL,
    zc_ops INTEGER NOT NULL,
    speedup REAL NOT NULL,
    zc_p50_us REAL NOT NULL,
    zc_p99_us REAL NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

### 5.2 Atomic State Transitions
When an incoming order partially or fully fills resting orders, the engine executes an atomic transaction updating the resting orders' quantities and statuses, inserting the incoming order, and logging trade records in one ACID transaction.

---

## 6. REST API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | API status and directory of available endpoints |
| `GET` | `/dashboard/` | Interactive web trading terminal UI |
| `POST` | `/orders` | Submit a new BUY or SELL order |
| `GET` | `/orders` | Retrieve active pending orders and recent order history |
| `DELETE` | `/orders/{order_id}` | Cancel an active pending order |
| `GET` | `/trades` | Retrieve list of completed trades |
| `GET` | `/book/depth` | Level 2 aggregated market depth (bids and asks) |
| `GET` | `/stats/daily` | Real-time daily analytics (orders, trades, volume, turnover) |
| `POST` | `/benchmark/run` | Execute zero-copy vs dynamic allocation benchmark |
| `GET` | `/benchmark/latest` | Retrieve latest benchmark metrics |
| `GET` | `/docs` | Interactive Swagger UI API documentation |

---

## 7. Verification & Testing

The project includes an automated test suite comprising 19 unit and integration tests across order matching, zero-copy buffer operations, boundary conditions, and database persistence.

Run tests:
```powershell
python -m unittest discover -s texts -v
```
All tests execute and pass in approximately 0.10 seconds.
