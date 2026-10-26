
const API = "http://127.0.0.1:8000";

const $ = id => document.getElementById(id);

function addCell(row, value) {
    const cell = row.insertCell();
    cell.textContent = value ?? "-";
}

function showRows(tableId, rows, columns, emptyMessage) {
    const table = $(tableId);
    table.replaceChildren();

    if (!rows.length) {
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
    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.detail || "Request failed");
    }

    return data;
}

async function refreshDashboard() {
    try {
        const [ordersData, trades] = await Promise.all([
            request("/orders"),
            request("/trades")
        ]);

        $("connection").textContent = "Backend connected";

        const book = ordersData.order_book;
        const orderHistory = ordersData.history;

        $("orderCount").textContent = orderHistory.length;
        $("tradeCount").textContent = trades.length;

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
            ["trade_id", "buy_order_id", "sell_order_id",
             "price", "quantity"],
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

    if (!Number.isFinite(price) || price <= 0 ||
        !Number.isSafeInteger(quantity) || quantity <= 0) {
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
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify(order)
        });

        $("message").textContent =
            `Order #${result.order_id}: ${result.filled_quantity} ` +
            `filled, ${result.remaining_quantity} remaining.`;

        event.target.reset();
        await refreshDashboard();
    } catch (error) {
        $("message").textContent = "Order failed: " + error.message;
    }
});

$("refreshButton").addEventListener("click", refreshDashboard);

refreshDashboard();
