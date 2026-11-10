@echo off
title ChronosMatch Backend Server
echo ===================================================
echo   Starting ChronosMatch High-Frequency Trading Engine
echo   API Base: http://127.0.0.1:8000/
echo   Dashboard: http://127.0.0.1:8000/dashboard/
echo   Press Ctrl+C to stop the server
echo ===================================================
echo.

if exist .venv\Scripts\python.exe (
    .venv\Scripts\python.exe -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
) else (
    python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
)

pause
