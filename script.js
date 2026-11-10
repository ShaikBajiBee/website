/**
 * ChronosMatch High-Frequency Trading Terminal Script
 * Handles real-time polling, order submissions, cancel operations,
 * Level 2 depth calculations, and Zero-Copy engine benchmarks.
 */

const API = "http://127.0.0.1:8000";

const $ = id => document.getElementById(id);

let currentBestBid = null;
let currentBestAsk = null;

function formatCurrency(val) {
    if (val == null || isNaN(val)) return "-";
    return "₹" + Number(val).toFixed(2);
}

function formatNumber(val) {
    if (val == null || isNaN(val)) return "0";
    return Number(val).toLocaleString();
}

function addCell(row, value, customClass = null) {
    const cell = row.insertCell();
    cell.textContent = value ?? "-";
    if (customClass) {
        cell.className = customClass;
    }
    return cell;
}

function showOrderRows(tableId, orders, isBuy) {
    const table = $(tableId);
    table.replaceChildren();

    if (!Array.isArray(orders) || orders.length === 0) {
        const row = table.insertRow();
        const cell = row.insertCell();
        cell.colSpan = 4;
        cell.textContent = isBuy ? "No pending buy orders (bids)" : "No pending sell orders (asks)";
        cell.style.color = "var(--text-muted)";
        cell.style.fontStyle = "italic";
        return;
    }

    orders.forEach(order => {
        const row = table.insertRow();
        addCell(row, `#${order.order_id}`);
        addCell(row, formatCurrency(order.price), isBuy ? "val-green" : "val-red");
        addCell(row, formatNumber(order.quantity));

        // Action cell with Cancel button
        const actionCell = row.insertCell();
        const cancelBtn = document.createElement("button");
        cancelBtn.type = "button";
        cancelBtn.className = "cancel-btn";
        cancelBtn.textContent = "Cancel";
        cancelBtn.onclick = async () => {
            try {
                await request(`/orders/${order.order_id}`, { method: "DELETE" });
                showMessage(`Order #${order.order_id} cancelled.`, false);
                await refreshDashboard();
            } catch (err) {
                showMessage(`Could not cancel order #${order.order_id}: ${err.message}`, true);
            }
        };
        actionCell.appendChild(cancelBtn);
    });
}

function showTradeRows(tableId, trades) {
    const table = $(tableId);
    table.replaceChildren();

    if (!Array.isArray(trades) || trades.length === 0) {
        const row = table.insertRow();
        const cell = row.insertCell();
        cell.colSpan = 5;
        cell.textContent = "No completed trades yet";
        cell.style.color = "var(--text-muted)";
        cell.style.fontStyle = "italic";
        return;
    }

    trades.slice(0, 50).forEach(trade => {
        const row = table.insertRow();
        addCell(row, `T-${trade.trade_id}`);
        addCell(row, `#${trade.buy_order_id}`);
        addCell(row, `#${trade.sell_order_id}`);
        addCell(row, formatCurrency(trade.price), "val-blue");
        addCell(row, formatNumber(trade.quantity));
    });
}

async function request(path, options = {}) {
    const response = await fetch(`${API}${path}`, options);
    const text = await response.text();
    let data;

    try {
        data = text ? JSON.parse(text) : {};
    } catch {
        throw new Error(`Invalid response from ${path}`);
    }

    if (!response.ok) {
        throw new Error(data.detail || `HTTP ${response.status} on ${path}`);
    }

    return data;
}

function showMessage(msg, isError = false) {
    const box = $("message");
    if (!box) return;
    box.textContent = msg;
    box.className = isError ? "error" : "success";
    if (!isError) {
        setTimeout(() => {
            if (box.className === "success") {
                box.textContent = "";
                box.className = "";
            }
        }, 6000);
    }
}

// Order Form helpers
function setSide(side) {
    $("side").value = side;
    if (side === "BUY") {
        $("btnSideBuy").className = "side-btn active buy-active";
        $("btnSideSell").className = "side-btn";
        $("submitOrderBtn").style.background = "linear-gradient(135deg, #10b981 0%, #059669 100%)";
    } else {
        $("btnSideBuy").className = "side-btn";
        $("btnSideSell").className = "side-btn active sell-active";
        $("submitOrderBtn").style.background = "linear-gradient(135deg, #f43f5e 0%, #e11d48 100%)";
    }
    updateEstimatedCost();
}

function adjustPrice(delta) {
    const input = $("price");
    const current = parseFloat(input.value) || 100.0;
    input.value = Math.max(0.01, (current + delta)).toFixed(2);
    updateEstimatedCost();
}

function setQty(val) {
    $("quantity").value = val;
    updateEstimatedCost();
}

function setPriceToBest(side) {
    const target = side === "BUY" ? currentBestBid : currentBestAsk;
    if (target != null) {
        $("price").value = Number(target).toFixed(2);
        updateEstimatedCost();
    }
}

function updateEstimatedCost() {
    const p = parseFloat($("price").value) || 0;
    const q = parseInt($("quantity").value, 10) || 0;
    const total = p * q;
    $("orderValueDisplay").textContent = formatCurrency(total);
}

// Wire form buttons
$("btnSideBuy").addEventListener("click", () => setSide("BUY"));
$("btnSideSell").addEventListener("click", () => setSide("SELL"));
$("price").addEventListener("input", updateEstimatedCost);
$("quantity").addEventListener("input", updateEstimatedCost);

function todayKey() {
    const now = new Date();
    return [
        now.getFullYear(),
        String(now.getMonth() + 1).padStart(2, "0"),
        String(now.getDate()).padStart(2, "0")
    ].join("-");
}

function recordDate(record) {
    const value =
        record.created_at ??
        record.timestamp ??
        record.executed_at ??
        record.datetime ??
        record.date;

    if (value == null) return null;

    let date;
    if (typeof value === "number") {
        date = new Date(value < 1e12 ? value * 1000 : value);
    } else {
        date = new Date(value);
    }

    if (Number.isNaN(date.getTime())) return null;

    return [
        date.getFullYear(),
        String(date.getMonth() + 1).padStart(2, "0"),
        String(date.getDate()).padStart(2, "0")
    ].join("-");
}

function updateDailyInformation(orderHistory, trades, apiDailyStats) {
    $("todayDate").textContent = new Date().toLocaleDateString(undefined, {
        weekday: 'short',
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });

    if (apiDailyStats) {
        $("dailyOrderCount").textContent = formatNumber(apiDailyStats.daily_order_count);
        $("dailyTradeCount").textContent = formatNumber(apiDailyStats.daily_trade_count);
        $("dailyQuantity").textContent = formatNumber(apiDailyStats.daily_quantity_traded);
        return;
    }

    const today = todayKey();
    const todaysOrders = orderHistory.filter(o => recordDate(o) === today);
    const todaysTrades = trades.filter(t => recordDate(t) === today);
    const quantity = todaysTrades.reduce((sum, t) => sum + Number(t.quantity || 0), 0);

    $("dailyOrderCount").textContent = formatNumber(todaysOrders.length);
    $("dailyTradeCount").textContent = formatNumber(todaysTrades.length);
    $("dailyQuantity").textContent = formatNumber(quantity);
}

async function refreshDashboard() {
    try {
        const [ordersData, tradesData, dailyStats] = await Promise.all([
            request("/orders"),
            request("/trades"),
            request("/stats/daily").catch(() => null)
        ]);

        const book = ordersData.order_book;
        const orderHistory = ordersData.history || [];
        const trades = Array.isArray(tradesData) ? tradesData : (tradesData.trades || []);

        const conn = $("connection");
        conn.textContent = "Zero-Copy Engine Online";
        conn.className = "";

        $("orderCount").textContent = formatNumber(orderHistory.length);
        $("tradeCount").textContent = formatNumber(trades.length);

        // Update Best Bid, Ask, Spread
        const buys = book.buys || [];
        const sells = book.sells || [];

        currentBestBid = buys.length > 0 ? buys[0].price : null;
        currentBestAsk = sells.length > 0 ? sells[0].price : null;

        $("bestBidDisplay").textContent = currentBestBid != null ? formatCurrency(currentBestBid) : "-";
        $("bestAskDisplay").textContent = currentBestAsk != null ? formatCurrency(currentBestAsk) : "-";

        if (currentBestBid != null && currentBestAsk != null) {
            const spread = currentBestAsk - currentBestBid;
            $("spreadDisplay").textContent = `₹${spread.toFixed(2)}`;
            $("spreadDisplay").style.color = spread <= 0 ? "var(--buy-green)" : "var(--text-primary)";
        } else {
            $("spreadDisplay").textContent = "-";
        }

        updateDailyInformation(orderHistory, trades, dailyStats);

        showOrderRows("buyTable", buys, true);
        showOrderRows("sellTable", sells, false);
        showTradeRows("tradeTable", trades);

    } catch (error) {
        const conn = $("connection");
        conn.textContent = "Backend Offline";
        conn.className = "disconnected";
    }
}

// Order Form Submission
$("orderForm").addEventListener("submit", async event => {
    event.preventDefault();

    const price = Number($("price").value);
    const quantity = Number($("quantity").value);
    const side = $("side").value;

    if (!Number.isFinite(price) || price <= 0 || !Number.isSafeInteger(quantity) || quantity <= 0) {
        showMessage("Enter a valid positive price and whole-number quantity.", true);
        return;
    }

    const payload = {
        side,
        price,
        quantity,
        order_type: "LIMIT"
    };

    try {
        const result = await request("/orders", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        const orderId = result.order_id ?? result.order?.order_id;
        const filled = result.filled_quantity ?? result.order?.filled_quantity ?? 0;
        const remaining = result.remaining_quantity ?? result.order?.remaining_quantity ?? 0;
        const status = result.status ?? result.order?.status ?? "OPEN";

        showMessage(`Order #${orderId} (${side} @ ₹${price.toFixed(2)}) processed: ${filled} filled, ${remaining} remaining [${status}].`, false);

        await refreshDashboard();

    } catch (error) {
        showMessage("Order failed: " + error.message, true);
    }
});

$("refreshButton").addEventListener("click", refreshDashboard);

// Benchmark Lab Integration
function renderBenchmarkMetrics(data) {
    if (!data) return;
    const std = data.standard_dict;
    const zc = data.zero_copy;

    if (std) {
        $("benchDictThroughput").textContent = `${formatNumber(std.throughput_orders_per_sec)} ops/sec`;
        $("benchDictAvg").textContent = `${std.avg_latency_ns} ns`;
        $("benchDictP50").textContent = `${std.p50_latency_us} µs`;
        $("benchDictP99").textContent = `${std.p99_latency_us} µs`;
    }

    if (zc) {
        $("benchZcThroughput").textContent = `${formatNumber(zc.throughput_orders_per_sec)} ops/sec`;
        $("benchZcAvg").textContent = `${zc.avg_latency_ns} ns`;
        $("benchZcP50").textContent = `${zc.p50_latency_us} µs`;
        $("benchZcP99").textContent = `${zc.p99_latency_us} µs`;
    }

    if (data.speedup_factor) {
        $("benchSpeedup").textContent = `${data.speedup_factor}x Faster`;
    }
}

async function loadLatestBenchmark() {
    try {
        const data = await request("/benchmark/latest");
        if (data && data.standard_dict) {
            renderBenchmarkMetrics(data);
        }
    } catch {
        // Benchmark not yet run; ready state will be shown
    }
}

$("runBenchmarkBtn").addEventListener("click", async () => {
    const btn = $("runBenchmarkBtn");
    const originalText = btn.textContent;
    btn.textContent = "⚡ Running 25K Orders...";
    btn.disabled = true;
    $("benchStatus").textContent = "Benchmarking...";

    try {
        const resp = await request("/benchmark/run", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ num_orders: 25000 })
        });
        renderBenchmarkMetrics(resp.benchmark);
        $("benchStatus").textContent = "Complete";
        showMessage("Zero-Copy benchmark completed successfully!", false);
    } catch (err) {
        showMessage("Benchmark failed: " + err.message, true);
        $("benchStatus").textContent = "Error";
    } finally {
        btn.textContent = originalText;
        btn.disabled = false;
    }
});

// Initial boot & periodic polling
updateDailyInformation([], [], null);
refreshDashboard();
loadLatestBenchmark();

// Poll every 3 seconds for live dashboard updates
setInterval(refreshDashboard, 3000);
