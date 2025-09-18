@echo off
SETLOCAL ENABLEEXTENSIONS
TITLE Reflexion DataHub – Live Mode

REM ─────────────────────────────────────────────
REM 🧠 Activate Python Environment
REM ─────────────────────────────────────────────
echo [🔧] Activating Reflexion environment...
call venv\Scripts\activate.bat

REM ─────────────────────────────────────────────
REM 🚀 Launch Reflexion System
REM ─────────────────────────────────────────────
echo [🚀] Starting Reflexion DataHub...
start "Reflexion Main" python main.py

REM ─────────────────────────────────────────────
REM 🧭 Leave Hub Running
REM ─────────────────────────────────────────────
echo [📡] Reflexion is now live and collecting data.
echo [🧠] Symbols in WARM mode will be evaluated and snapshot hydrated.
echo [🕒] Leave this window open to maintain ingestion and diagnostics.

pause
ENDLOCAL