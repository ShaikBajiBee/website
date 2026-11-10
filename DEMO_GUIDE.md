# ChronosMatch: Project Demonstration Guide
## Step-by-Step Live Demonstration Walkthrough

**Candidate:** Shaik Baji Bee  
**Role:** Data Associate L1. Intern  
**Company:** Infotact Solutions  
**Project Ref:** ITS/PY/1126  
**Date:** 10 November 2026  

---

This guide provides a step-by-step procedure to showcase the **ChronosMatch: Zero-Copy High-Frequency Trading Engine** during an evaluation or mentor review.

---

## 1. Quick Startup

### Step 1: Start the Backend API Server
In your terminal from the project root folder:
```powershell
python -m uvicorn backend.main:app --reload
```
The terminal will display:
```
INFO:     ChronosMatch database initialized
INFO:     ChronosMatch initialized. Next Order ID: ..., Next Trade ID: ...
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

### Step 2: Open the Web Dashboard
Open your web browser and navigate directly to:
```
http://127.0.0.1:8000/dashboard/
```
*(Or open `frontend/index.html` with VS Code Live Server on `http://127.0.0.1:5500`)*

The dashboard should immediately display:
- **Status:** `Zero-Copy Engine Online` (with a glowing emerald indicator)
- **Top Metrics:** Submitted Orders, Completed Trades, Best Bid, Best Ask, Spread
- **Trading Floor:** Order entry form, Pending Bids & Asks tables, Completed Trades tape

---

## 2. Demonstration Flow

### Demo 1: Manual Order Submission & Crossing Match
1. **Place a BUY Order:**
   - Click the green **BUY** tab.
   - Limit Price: `150.00`
   - Quantity: `20`
   - Click **Submit Order**.
   - Notice the order immediately appears in the **Pending Buy Orders (Bids)** table with ID `#X`, Price `₹150.00`, and Remaining `20`.
   - The Top Metrics ribbon updates: **Best Bid** shows `₹150.00`.

2. **Place a Matching SELL Order:**
   - Click the red **SELL** tab.
   - Limit Price: `150.00` (or lower, e.g. `148.00` to demonstrate price crossing).
   - Quantity: `15` (to demonstrate a **partial fill**).
   - Click **Submit Order**.
   - **Observe:**
     - A trade is instantly executed for `15` units at `₹150.00`.
     - The trade appears immediately in the **Executed Trade Feed (Tape)** table.
     - The Buy order in Pending Buy Orders updates its remaining quantity from `20` down to `5`.
     - Daily Trading Performance card increments **Trades Today** and **Total Quantity Traded**.

3. **Cancel a Resting Order:**
   - In the **Pending Buy Orders** table, click the red **Cancel** button on any active order.
   - Notice the order is removed from the active order book instantly, and its status is marked `CANCELLED` in the SQLite database.

---

### Demo 2: Streaming Automated Market Simulation
Open a second terminal window and run the live market simulation script:
```powershell
python scripts/simulate_feed.py --orders 40 --interval 0.4
```
**What happens on screen:**
- The terminal will stream orders into the engine.
- Watch your browser dashboard update live every few seconds!
- Orders and trades will animate into the order book and trade tape.
- Best Bid, Best Ask, and the Spread will dynamically adjust.

---

### Demo 3: Zero-Copy Engine Benchmark Lab
1. On the web dashboard, scroll down to the **⚡ Zero-Copy Engine Benchmark Lab**.
2. Click the **⚡ Run 25,000 Order Benchmark** button.
3. Within 1-2 seconds, the engine processes 25,000 orders through both standard Python dynamic heap allocation and the ChronosMatch 32-byte contiguous binary ring buffer.
4. **Point out to the evaluator:**
   - **Throughput:** ~475K ops/sec (Dict) vs **~930K ops/sec (Zero-Copy)** -> **~1.96× Speedup**.
   - **P50 Latency:** Sub-microsecond (~0.90 µs vs ~1.90 µs).
   - **P99 Tail Jitter:** Significantly lower tail latency due to zero GC deallocations.

---

### Demo 4: Running the Automated Test Suite
To demonstrate code reliability and regression testing to the evaluator:
```powershell
python -m unittest discover -s texts -v
```
All **19 unit and integration tests** will execute and pass cleanly in ~0.10s.

---

### Demo 5: Presenting the Slide Deck
Open `docs/presentation.html` in your web browser. Use the `Next →` button or keyboard `Arrow Right` key to navigate the 8 presentation slides covering problem definition, architecture, algorithms, benchmarks, and deliverables.
