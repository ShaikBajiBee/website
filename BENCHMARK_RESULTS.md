# ChronosMatch: Performance Benchmark & Evaluation Results
## Quantitative Latency & Throughput Analysis

**Project Name:** ChronosMatch: Zero-Copy High-Frequency Trading Engine  
**Author:** Shaik Baji Bee (Data Associate L1. Intern)  
**Organization:** Infotact Solutions  
**Reference ID:** ITS/PY/1126  
**Evaluation Date:** 10 November 2026  

---

## 1. Benchmark Methodology

High-Frequency Trading (HFT) architectures are evaluated on two primary dimensions:
1. **Throughput (Orders Per Second):** The sustained volume of order modifications and executions the engine can process per second.
2. **Deterministic Latency Distribution (P50, P90, P99, P99.9):** The time required to ingest and match an individual order, particularly the variance (tail jitter) caused by system interrupts or garbage collection.

### Test Environment
- **Runtime:** Python 3.14 (64-bit)
- **Timing Instrument:** Hardware high-resolution clock (`time.perf_counter_ns()`)
- **Sample Size:** 25,000 order sequence burst
- **Order Characteristics:** 50% BUY, 50% SELL, distributed across 50 discrete price levels.

---

## 2. Experimental Results Summary

| Benchmark Metric | Standard Python Heap Dict | ChronosMatch Zero-Copy Buffer | Relative Improvement |
|---|---|---|---|
| **Total Test Volume** | 25,000 orders | 25,000 orders | Baseline |
| **Elapsed Execution Time** | 0.0526 s | **0.0268 s** | **49.0% Reduction** |
| **Sustained Throughput** | 475,285 ops/sec | **932,835 ops/sec** | **~1.96× Faster** |
| **Mean Latency** | 2,104 ns (~2.10 µs) | **1,072 ns (~1.07 µs)** | **~49% Lower** |
| **P50 (Median) Latency** | 1,900 ns (~1.90 µs) | **900 ns (~0.90 µs)** | **2.11× Faster** |
| **P90 Latency** | 2,800 ns (~2.80 µs) | **1,400 ns (~1.40 µs)** | **2.00× Faster** |
| **P95 Latency** | 3,400 ns (~3.40 µs) | **1,700 ns (~1.70 µs)** | **2.00× Faster** |
| **P99 (Tail) Latency** | 6,100 ns (~6.10 µs) | **2,800 ns (~2.80 µs)** | **2.18× Faster** |
| **Maximum Jitter Spike** | 42,300 ns (~42.3 µs) | **8,900 ns (~8.9 µs)** | **4.75× Less Jitter** |

---

## 3. Latency Distribution Analysis

```
Latency Percentile Comparison (Microseconds - Lower is Better)

Percentile   Standard Dict     ChronosMatch Zero-Copy
─────────────────────────────────────────────────────
P50 (Median) █ 1.90 µs         ▌ 0.90 µs
P90          ██ 2.80 µs        █ 1.40 µs
P95          ███ 3.40 µs       █▌ 1.70 µs
P99 (Tail)   ██████ 6.10 µs    ██▌ 2.80 µs
Max Spike    ████████████ 42µs ██ 8.90 µs
```

### Key Technical Findings:
1. **Suppression of Tail Jitter:** In standard dynamic heap allocation, Python's generational garbage collection triggers periodic scan phases when the allocation threshold is reached, creating 40+ microsecond tail spikes. ChronosMatch eliminates these pauses because memory is pre-allocated and never deallocated during operation.
2. **Cache Locality:** With contiguous 32-byte binary structures, two order records fit neatly within a single 64-byte L1 CPU cache line, enabling hardware prefetching and maximizing CPU efficiency.

---

## 4. How to Reproduce Benchmarks

The benchmark can be executed in two ways:

### A. Via the Interactive Web Dashboard
1. Open the ChronosMatch Web Dashboard at `http://127.0.0.1:8000/dashboard/`.
2. Scroll to the **⚡ Zero-Copy Engine Benchmark Lab** section.
3. Click the **"⚡ Run 25,000 Order Benchmark"** button.
4. The live benchmark results will be calculated and displayed on the interface.

### B. Via Terminal Execution
```powershell
python -c "from backend.zero_copy import ZeroCopyBenchmark; import json; print(json.dumps(ZeroCopyBenchmark.run_benchmark(25000), indent=2))"
```
