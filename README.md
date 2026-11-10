# ChronosMatch: Zero-Copy High-Frequency Trading Engine

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![Tests](https://img.shields.io/badge/tests-19%20passed-brightgreen.svg)]()
[![Latency](https://img.shields.io/badge/latency-sub--microsecond-brightgreen.svg)]()

**Reference No.:** ITS/PY/1126  
**Internship Role:** Data Associate L1. Intern (Python Development)  
**Organization:** Infotact Solutions  
**Submission Date:** 10 November 2026  

---

## ⚡ Overview

**ChronosMatch** is an exchange-grade, microsecond-latency order matching engine and real-time electronic trading terminal. It combines a **Zero-Copy Contiguous Binary Ring Buffer** (eliminating Python Garbage Collector pauses and heap churn) with a deterministic **Price-Time Priority (FIFO)** matching core, **ACID-compliant SQLite persistence**, and a modern **Bloomberg-style web trading dashboard**.

---

## 🌟 Key Features

- **Zero-Copy Binary Memory Architecture:**
  - 3.2 MB pre-allocated contiguous memory buffer (100,000 slots of 32 bytes each).
  - Uses `memoryview` and Little-Endian struct layout (`<cc2sQdIQ`) without heap object allocations during high-frequency order bursts.
  - Sub-microsecond median order latency (~0.90 µs) and over **900,000+ orders/sec** sustained throughput.
- **Price-Time Priority (FIFO) Matching Engine:**
  - Best price execution (trades execute at passive resting order's price).
  - Price-time priority for bids (descending) and asks (ascending).
  - Supports Limit & Market orders, partial fills, and real-time order cancellations.
  - Aggregated Level 2 Market Depth calculation (Bids and Asks by price tier).
- **Persistent Data Store (SQLite):**
  - Continuous synchronization with database on startup to prevent order ID collisions.
  - Atomic multi-statement transactions updating resting orders, incoming fills, and trade logs simultaneously.
  - Order lifecycle tracking (`OPEN`, `PARTIALLY_FILLED`, `FILLED`, `CANCELLED`).
  - Daily aggregated performance analytics (orders, trades, volume, turnover in ₹).
- **Modern Web Trading Terminal:**
  - Dark fintech terminal theme with glowing real-time status indicator.
  - Interactive BUY / SELL switcher with quick increment price/quantity chips and live estimated order value.
  - Pending orders tables with dynamic **Cancel** buttons.
  - Real-time trade feed tape and daily metrics.
  - Interactive **Zero-Copy Benchmark Lab** allowing users to benchmark engine throughput directly in the browser.
- **Automated Market Feed Simulator:**
  - Python simulator script (`scripts/simulate_feed.py`) generating streaming live orders to demonstrate real-time matching and depth updates.

---

## 🏗️ Project Architecture

```
ChronosMatch project/
├── backend/
│   ├── __init__.py
│   ├── main.py                  # FastAPI REST gateway & static file server
│   ├── order_book.py            # Price-time priority matching engine & Level 2 depth
│   ├── zero_copy.py             # 32-byte binary ring buffer & benchmark suite
│   ├── database.py              # SQLite persistence, atomic transactions & migrations
│   ├── chronosmatch.db          # Persistent SQLite database
│   └── requirements.txt
├── frontend/
│   ├── index.html               # Web trading dashboard & benchmark lab UI
│   ├── style.css                # Modern dark fintech stylesheet (responsive)
│   └── script.js                # Real-time polling, form handling & benchmark runner
├── scripts/
│   └── simulate_feed.py         # Live streaming order generator for live demonstrations
├── texts/
│   ├── test_order_book.py       # Matching engine & zero-copy unit tests
│   └── test_api_database.py     # Database persistence & API integration tests
├── docs/
│   ├── PROJECT_DOCUMENTATION.md # Complete technical specification & architecture
│   ├── PROJECT_REPORT.md        # Formal internship submission report
│   ├── PRESENTATION.md          # Defense slide deck notes
│   ├── presentation.html        # Interactive HTML presentation slide deck
│   ├── BENCHMARK_RESULTS.md     # Quantitative latency & throughput evaluation
│   └── DEMO_GUIDE.md            # Mentor walkthrough and demonstration guide
├── requirements.txt
└── README.md
```

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- Python 3.10 or newer (tested on Python 3.14)
- Any modern web browser (Chrome, Edge, Firefox, Safari)

### 2. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 3. Start the Backend Engine
From the project root directory:
```powershell
python -m uvicorn backend.main:app --reload
```
The engine will boot up, initialize SQLite, synchronize IDs, and start listening on port 8000:
- **Interactive Web Dashboard:** http://127.0.0.1:8000/dashboard/
- **Interactive Swagger API Docs:** http://127.0.0.1:8000/docs
- **API Base:** http://127.0.0.1:8000/

### 4. Open the Web Trading Dashboard
Navigate directly to:
👉 **[http://127.0.0.1:8000/dashboard/](http://127.0.0.1:8000/dashboard/)**

*(Or open `frontend/index.html` with VS Code Live Server on `http://127.0.0.1:5500`)*

---

## 🧪 Automated Testing

Run the full suite of **19 unit and integration tests**:
```powershell
python -m unittest discover -s texts -v
```
All tests pass in approximately **0.10 seconds**.

---

## 📊 Performance Benchmarks

| Metric | Standard Python Dict | ChronosMatch Zero-Copy | Speedup |
|---|---|---|---|
| **Sustained Throughput** | ~475,000 ops/sec | **~932,000 ops/sec** | **~1.96× Faster** |
| **Median (P50) Latency** | 1.90 µs | **0.90 µs** | **2.11× Faster** |
| **Tail (P99) Latency** | 6.10 µs | **2.80 µs** | **2.18× Faster** |
| **Memory Allocation** | Dynamic Heap Allocations | **Contiguous Pre-allocated 32B Slots** | **Zero GC Pauses** |

Run the benchmark manually via command line:
```powershell
python -c "from backend.zero_copy import ZeroCopyBenchmark; import json; print(json.dumps(ZeroCopyBenchmark.run_benchmark(25000), indent=2))"
```
Or click the **"Run 25,000 Order Benchmark"** button directly on the web dashboard.

---

## 📡 REST API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | API status and endpoint directory |
| `GET` | `/dashboard/` | Web trading terminal UI |
| `POST` | `/orders` | Submit a BUY or SELL order |
| `GET` | `/orders` | Current order book & order history |
| `DELETE` | `/orders/{order_id}` | Cancel a resting order |
| `GET` | `/trades` | Completed trade execution history |
| `GET` | `/book/depth` | Aggregated Level 2 Market Depth (bids/asks) |
| `GET` | `/stats/daily` | Real-time daily analytics |
| `POST` | `/benchmark/run` | Execute zero-copy vs dynamic benchmark |
| `GET` | `/benchmark/latest` | Retrieve latest benchmark run |
| `GET` | `/docs` | OpenAPI / Swagger interactive documentation |

---

## 📁 Internship Submission Deliverables (Infotact Solutions)

All deliverables requested in Assignment Letter **Ref: ITS/PY/1126** are completed:

1. **Source Code:** Fully functional zero-copy high-frequency trading engine in Python & FastAPI.
2. **Project Documentation:** [docs/PROJECT_DOCUMENTATION.md](docs/PROJECT_DOCUMENTATION.md)
3. **Formal Project Report:** [docs/PROJECT_REPORT.md](docs/PROJECT_REPORT.md)
4. **Presentation (Deck & HTML Slides):** [docs/presentation.html](docs/presentation.html) and [docs/PRESENTATION.md](docs/PRESENTATION.md)
5. **Model Evaluation & Benchmarks:** [docs/BENCHMARK_RESULTS.md](docs/BENCHMARK_RESULTS.md)
6. **Demonstration Guide:** [docs/DEMO_GUIDE.md](docs/DEMO_GUIDE.md)


