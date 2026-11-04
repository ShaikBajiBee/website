
const API = "http://127.0.0.1:8000";

const $ = id => document.getElementById(id);

function addCell(row, value) {
    const cell = row.insertCell();
    cell.textContent = value ?? "-";
}

function showRows(tableId, rows, columns, emptyMessage) {
    const table = $(tableId);
    table.replaceChildren();

    if (!Array.isArray(rows) || rows.length === 0) {
        const row = table.insertRow();
        const cell = row.insertCell();
        cell.colSpan = columns.length;
        cell.textContent = emptyMessage;
        return;
    }

    rows.forEach(item => {
        const row = table.insertRow();
        columns.forEach(key => addCell(row, item[key]));
    });
}

async function request(path, options = {}) {
    const response = await fetch(`${API}${path}`, options);

    // Avoid a confusing JSON parsing error for non-JSON responses.
    const text = await response.text();
    let data;

    try {
        data = text ? JSON.parse(text) : {};
    } catch {
        throw new Error(`Invalid response from ${path}`);
    }

    if (!response.ok) {
        throw new Error(
            data.detail || `HTTP ${response.status} on ${path}`
        );
    }

    return data;
}

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
        record.timestamp ??
        record.created_at ??
        record.executed_at ??
        record.datetime ??
        record.date;

    if (value == null) return null;

    let date;

    if (typeof value === "number") {
        date = new Date(
            value < 1e12 ? value * 1000 : value
        );
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

function updateDailyInformation(orderHistory, trades) {
    const today = todayKey();

    const todaysOrders = orderHistory.filter(
        order => recordDate(order) === today
    );

    const todaysTrades = trades.filter(
        trade => recordDate(trade) === today
    );

    const quantity = todaysTrades.reduce(
        (sum, trade) => sum + Number(trade.quantity || 0),
        0
    );

    $("todayDate").textContent =
        new Date().toLocaleDateString();

    $("dailyOrderCount").textContent =
        todaysOrders.length;

    $("dailyTradeCount").textContent =
        todaysTrades.length;

    $("dailyQuantity").textContent = quantity;
}

async function refreshDashboard() {
    try {
        const [ordersData, tradesData] = await Promise.all([
            request("/orders"),
            request("/trades")
        ]);

        const book = ordersData.order_book;
        const orderHistory = ordersData.history;
        const trades = Array.isArray(tradesData)
            ? tradesData
            : tradesData.trades;

        if (
            !book ||
            !Array.isArray(book.buys) ||
            !Array.isArray(book.sells) ||
            !Array.isArray(orderHistory) ||
            !Array.isArray(trades)
        ) {
            throw new Error("Unexpected API data format");
        }

        $("connection").textContent = "Backend connected";
        $("message").textContent = "";

        $("orderCount").textContent = orderHistory.length;
        $("tradeCount").textContent = trades.length;

        updateDailyInformation(orderHistory, trades);

        showRows(
            "buyTable",
            book.buys,
            ["order_id", "price", "quantity"],
            "No pending buy orders"
        );

        showRows(
            "sellTable",
            book.sells,
            ["order_id", "price", "quantity"],
            "No pending sell orders"
        );

        showRows(
            "tradeTable",
            trades,
            [
                "trade_id",
                "buy_order_id",
                "sell_order_id",
                "price",
                "quantity"
            ],
            "No completed trades"
        );

    } catch (error) {
        $("connection").textContent = "Backend disconnected";
        $("message").textContent =
            "Could not load dashboard: " + error.message;
    }
}

$("orderForm").addEventListener("submit", async event => {
    event.preventDefault();

    const price = Number($("price").value);
    const quantity = Number($("quantity").value);

    if (
        !Number.isFinite(price) ||
        price <= 0 ||
        !Number.isSafeInteger(quantity) ||
        quantity <= 0
    ) {
        $("message").textContent =
            "Enter a positive price and whole-number quantity.";
        return;
    }

    const order = {
        side: $("side").value,
        price,
        quantity
    };

    try {
        const result = await request("/orders", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(order)
        });

        $("message").textContent =
            `Order #${result.order_id}: ` +
            `${result.filled_quantity} filled, ` +
            `${result.remaining_quantity} remaining.`;

        event.target.reset();
        await refreshDashboard();

    } catch (error) {
        $("message").textContent =
            "Order failed: " + error.message;
    }
});

$("refreshButton").addEventListener(
    "click",
    refreshDashboard
);

updateDailyInformation([], []);
refreshDashboard();
