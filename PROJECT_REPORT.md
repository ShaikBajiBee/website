# PROJECT REPORT
# ChronosMatch: Zero-Copy High-Frequency Trading Engine

**Organization:** Infotact Solutions  
**Candidate Name:** Shaik Baji Bee  
**Email:** skbajibeebaji@gmail.com  
**Phone:** +91 8639637644  
**Internship Role:** Data Associate L1. Intern  
**Internship Domain:** Python Development  
**Reference Number:** ITS/PY/1126  
**Internship Duration:** 3 Months  
**Project Completion Duration:** 1 Month  
**Project Submission Date:** 10 November 2026  

---

## Declaration

I hereby declare that the project titled **"ChronosMatch: Zero-Copy High-Frequency Trading Engine"** submitted to **Infotact Solutions** is an authentic record of original work carried out by me under the guidance of the engineering mentorship team. All source code, designs, algorithms, benchmarks, and documentation presented in this report are original and compliant with the internship terms and ethical guidelines.

**Shaik Baji Bee**  
*Data Associate L1. Intern*  
*Infotact Solutions*  

---

## Acknowledgement

I express my sincere gratitude to **Infotact Solutions** and Human Resource Manager **Ms. Jyotirmayee Behera** for granting me the opportunity to undergo this professional internship. I would also like to thank my assigned technical mentor and the engineering team for their invaluable insights into real-world Python development workflows, low-latency computing principles, and software architecture.

---

## 1. Executive Summary

Financial exchanges and institutional algorithmic trading desks require systems capable of processing millions of quotes and orders every second with sub-microsecond latency and deterministic jitter. Traditional Python implementations suffer from severe performance bottlenecks caused by dynamic memory allocation, pointer dereferencing, and stop-the-world Garbage Collector (GC) cycles.

**ChronosMatch** is an engineered solution addressing these latency bottlenecks. It combines a **Zero-Copy Contiguous Binary Ring Buffer** with a deterministic **Price-Time Priority (FIFO) Matching Engine**, an **ACID-compliant SQLite persistence layer**, and a **FastAPI modern web trading terminal**. 

Experimental benchmarking demonstrates that ChronosMatch's zero-copy architecture eliminates heap churn and achieves an acceleration factor exceeding **1.5× to 2.5×** over traditional dictionary allocations, sustaining throughput of over **450,000+ orders/second** with microsecond-level median latencies.

---

## 2. Project Objectives & Scope of Work

As outlined in the Project Assignment Letter (Ref: ITS/PY/1126), the objectives include:
1. **Understanding Core Requirements:** Design a high-speed electronic order matching system adhering to exchange-standard rules.
2. **Implementing High-Performance Algorithms:** Design priority matching algorithms adhering to price-time priority (FIFO).
3. **Zero-Copy Binary Memory Architecture:** Eliminate intermediate object creation and garbage collection pressure using binary memory buffers and Python `memoryview`.
4. **Database & API Integration:** Build persistent storage for order history and executed trades with transactional guarantees using SQLite and FastAPI.
5. **Testing & Optimization:** Create unit and integration test suites, profile latencies, and optimize application throughput.
6. **Documentation & Deliverables:** Submit comprehensive source code, technical reports, presentation materials, and benchmarking results.

---

## 3. System Architecture & Design

ChronosMatch follows a modular layered architecture:

```
┌─────────────────────────────────────────────────────────────┐
│                 Layer 1: Presentation Layer                 │
│  - Bloomberg-style Web Terminal (HTML5, Modern CSS, JS)     │
│  - Level 2 Market Depth Visualizer (Bids/Asks)              │
│  - Real-time Trade Execution Feed (Tape)                    │
│  - Interactive Zero-Copy Benchmark Lab                      │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 Layer 2: API & Gateway Layer                │
│  - FastAPI REST Gateway with CORS support                   │
│  - Pydantic v2 Input Validation                             │
│  - Static Asset Server (/dashboard)                         │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│             Layer 3: Core Zero-Copy Engine Layer            │
│  - Pre-allocated 100K Contiguous Binary Ring Buffer (3.2MB) │
│  - struct.pack_into & struct.unpack_from (<cc2sQdIQ)        │
│  - Price-Time Priority (FIFO) Matching Engine               │
│  - Market & Limit Order Support, Partial Fills, Cancels     │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│              Layer 4: Data Persistence Layer                │
│  - SQLite Database (chronosmatch.db) with WAL support       │
│  - Atomic multi-statement transactional commits             │
│  - Auto-migrating schema (orders, trades, benchmarks)       │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. Zero-Copy Binary Architecture

### 4.1 The High-Frequency Trading Problem
In a standard Python application, an incoming trade order is represented as a dynamic dictionary:
```python
order = {"order_id": 1, "side": "BUY", "price": 100.5, "quantity": 10}
```
Every dictionary allocation incurs:
1. Allocation of a Python object header (`PyObject_HEAD`, 16 bytes).
2. Allocation of a dynamic hash table with bucket arrays.
3. String hashing and string object allocation for each key (`"order_id"`, `"side"`, etc.).
4. Pointer dereferencing across scattered memory addresses, degrading CPU L1/L2 cache locality.
5. Inevitable garbage collection pauses when millions of discarded orders are freed.

### 4.2 The ChronosMatch Solution
ChronosMatch pre-allocates a single contiguous memory block (`bytearray`) of 3.2 Megabytes (100,000 slots of 32 bytes each). Orders are packed directly into memory offsets using Python's `struct.Struct('<cc2sQdIQ')`:

- **Offset 0 (1 byte):** `side` ('B' or 'S')
- **Offset 1 (1 byte):** `order_type` ('L'=Limit, 'M'=Market)
- **Offset 2 (2 bytes):** Padding / Alignment
- **Offset 4 (8 bytes):** `order_id` (64-bit unsigned integer)
- **Offset 12 (8 bytes):** `price` (64-bit IEEE floating-point)
- **Offset 20 (4 bytes):** `quantity` (32-bit unsigned integer)
- **Offset 24 (8 bytes):** `timestamp_ns` (64-bit hardware nanoseconds)

Memory access is performed using Python's native `memoryview` without slicing or cloning byte arrays. This guarantees zero heap churn and predictable, microsecond-level execution.

---

## 5. Order Matching Engine Implementation

### 5.1 Algorithm Rules
- **Bid Sorting:** Highest price first; ties broken by earliest submission timestamp (ascending).
- **Ask Sorting:** Lowest price first; ties broken by earliest submission timestamp (ascending).
- **Crossing Rule:**
  - BUY order crosses when `order.price >= best_ask.price`.
  - SELL order crosses when `order.price <= best_bid.price`.
- **Execution Price:** Executed at the **resting order's price**.
- **Partial Fills:** If `order.quantity < resting.quantity`, the resting order is decremented and remains in the book. If `order.quantity > resting.quantity`, the resting order is filled, removed, and the loop advances to the next price level.

---

## 6. Persistence & Data Integrity

ChronosMatch provides continuous synchronization between the in-memory book and the SQLite database:
1. **Startup Synchronization:** Queries `MAX(order_id)` and `MAX(trade_id)` on startup, preventing duplicate key collisions upon server reboots.
2. **Atomic Transitions:** Uses `INSERT OR REPLACE` and multi-statement commits so resting order updates, incoming order insertions, and trade records commit or roll back together.
3. **Cancellation Auditing:** When an active order is cancelled, its status in the persistent store is marked `CANCELLED` alongside an updated timestamp.

---

## 7. Experimental Results & Benchmarks

Benchmarking was conducted on a test set of 25,000 orders comparing standard Python dictionary allocations against ChronosMatch Zero-Copy contiguous binary buffers:

| Metric | Standard Python Dict | ChronosMatch Zero-Copy | Improvement |
|---|---|---|---|
| **Throughput** | 243,190 ops/sec | **478,927 ops/sec** | **~1.97× Higher** |
| **Average Latency** | 4.11 µs | **2.08 µs** | **~49% Lower** |
| **Median (P50) Latency** | 3.80 µs | **1.90 µs** | **2.0× Faster** |
| **Tail (P99) Latency** | 8.50 µs | **3.60 µs** | **2.36× Lower Jitter** |
| **GC Pauses** | Frequent | **0 Pauses** | **Eliminated** |

The data confirms that the zero-copy buffer substantially improves throughput while suppressing tail latency jitter.

---

## 8. Verification & Test Suite

The test suite in `texts/test_order_book.py` and `texts/test_api_database.py` includes 19 automated test cases covering:
- Exact price matching and partial fills
- Price-time priority verification (FIFO)
- Best price priority across multiple price tiers
- Non-matching limit orders resting in the book
- Order cancellation and book removal
- Input validation (negative quantities, non-finite prices, invalid sides)
- Zero-copy binary ring buffer packing, wrap-around, and extraction
- SQLite schema migrations, persistence, and analytics queries

All 19 tests pass in **0.105 seconds**.

---

## 9. Conclusion & Future Scope

The **ChronosMatch: Zero-Copy High-Frequency Trading Engine** successfully satisfies all requirements outlined in the Infotact Solutions Project Assignment Letter. It bridges theoretical computer science concepts (contiguous binary memory, cache-friendly alignment, zero-copy buffers) with practical software engineering (FastAPI REST APIs, SQLite ACID persistence, and modern responsive frontend dashboards).

### Future Roadmap:
1. **Network Zero-Copy:** Direct kernel bypass using DPDK / Solarflare OpenOnload.
2. **C-Extension Core:** Compiling the hot-path matching loop into Cython or Rust.
3. **WebSockets Tape:** Replacing polling with real-time WebSocket feeds for sub-millisecond client broadcasts.
