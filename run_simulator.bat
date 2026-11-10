@echo off
title ChronosMatch Live Market Feed Simulator
echo ===================================================
echo   ChronosMatch Market Order Flow Simulator
echo   Simulating live streaming orders...
echo ===================================================
echo.

if exist .venv\Scripts\python.exe (
    .venv\Scripts\python.exe scripts/simulate_feed.py --orders 40 --interval 0.4
) else (
    python scripts/simulate_feed.py --orders 40 --interval 0.4
)

echo.
pause
