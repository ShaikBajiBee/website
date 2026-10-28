# ChronosMatch: Zero-Copy High-Frequency Trading Engine

**Reference No.:** ITS/PY/1126

ChronosMatch is a Python-based order matching engine with a browser dashboard. It accepts BUY and SELL orders, matches compatible orders by price and time priority, records completed trades, and stores order/trade history in SQLite.

> **Project note:** This is an educational prototype. Although the project title mentions “Zero-Copy,” the current implementation does not demonstrate or benchmark a zero-copy architecture. It should not be used for live financial trading.

## Features

- Submit BUY and SELL orders through a web dashboard.
- Match orders when the incoming order price crosses the best available opposite-side order.
- Prioritize better prices and use submission sequence for orders at the same price.
- Support partial fills and fully filled orders.
- View pending buy orders, pending sell orders, and completed trades.
- Persist order and trade history in a local SQLite database.
- Validate order side, price, and quantity.

## Technology Stack

- **Backend:** Python, FastAPI, Uvicorn, Pydantic
- **Frontend:** HTML, CSS, JavaScript
- **Database:** SQLite
- **Tests:** Python `unittest`

## Project Structure

```text
ChronosMatch project/
├── backend/
│   ├── __init__.py
│   ├── main.py
│   ├── order_book.py
│   ├── database.py
│   ├── chronosmatch.db       # Created/used for local order and trade history
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── script.js
├── texts/
│   └── test_order_book.py
├── requirements.txt
└── README.md
```

## Requirements

- Python 3.10 or newer recommended
- A modern web browser
- VS Code is optional

## Setup and Run (Windows / VS Code)

Open the project folder in VS Code, then open **Terminal → New Terminal**.

### 1. Create and activate a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, you can use Command Prompt instead:

```bat
.venv\Scripts\activate.bat
```

### 2. Install dependencies

Run this from the project root folder:

```powershell
python -m pip install -r requirements.txt
```

### 3. Start the backend API

From the project root folder, run:

```powershell
python -m uvicorn backend.main:app --reload
```

The API will be available at:

- API base: http://127.0.0.1:8000/
- Interactive API docs: http://127.0.0.1:8000/docs

Keep this terminal running while using the dashboard.

### 4. Open the frontend dashboard

The frontend is a static site. In VS Code, open `frontend/index.html` with the **Live Server** extension. It normally opens at `http://127.0.0.1:5500`, which is allowed by the backend's CORS configuration.

If you do not use Live Server, serve the project root with a local static web server configured to use port `5500`, then open the frontend page. Opening the HTML directly as a `file://` URL may cause browser connection/CORS issues.

## API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/` | Check whether the API is running |
| `POST` | `/orders` | Submit a BUY or SELL order |
| `GET` | `/orders` | Get the current order book and saved order history |
| `GET` | `/trades` | Get saved trade history |

### Example order request

Send a `POST` request to `http://127.0.0.1:8000/orders` with JSON:

```json
{
  "side": "BUY",
  "price": 100.00,
  "quantity": 10
}
```

`side` must be `BUY` or `SELL`, `price` must be a positive finite number, and `quantity` must be a positive integer.

## Run Tests

From the project root folder:

```powershell
python -m unittest discover -s texts -v
```

## How Matching Works

1. Validate the incoming order.
2. Look at the best available order on the opposite side.
3. If prices cross, execute a trade for the smaller remaining quantity.
4. Continue matching while the incoming order can trade and compatible opposite-side orders remain.
5. Keep any unfilled quantity in the order book.
6. Save order and trade records in SQLite.

BUY orders are prioritized by highest price first. SELL orders are prioritized by lowest price first. For equal prices, earlier submitted orders have priority.

## Limitations

- This is a local educational/demo implementation, not a production trading system.
- The in-memory order book resets when the backend process restarts, while the SQLite database keeps historical records. The current code does not rebuild the live order book from saved history on startup.
- The project has not established zero-copy behavior or high-frequency performance through profiling or benchmarks.
- Production use would require additional work, including concurrency control, recovery/replay, robust persistence transactions, monitoring, security, and extensive testing.

## License

No license is specified in the current project files. Add a license if you intend to distribute the project publicly.
