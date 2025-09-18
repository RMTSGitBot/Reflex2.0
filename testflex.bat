@echo off
SETLOCAL ENABLEEXTENSIONS
TITLE Reflexion Boot + Test Suite

REM ─────────────────────────────────────────────
REM 🧠 Activate Python Environment
REM ─────────────────────────────────────────────
echo [🔧] Activating Python environment...
call venv\Scripts\activate.bat

REM ─────────────────────────────────────────────
REM 🚀 Launch Reflexion System
REM ─────────────────────────────────────────────
echo [🚀] Starting Reflexion DataHub...
start "Reflexion Main" python main.py

REM ─────────────────────────────────────────────
REM 🧪 Run Test Suite
REM ─────────────────────────────────────────────
echo [🧪] Running test suite...
python -m unittest discover -s tests -p "test_*.py"

REM ─────────────────────────────────────────────
REM ✅ Done
REM ─────────────────────────────────────────────
echo [✅] Reflexion launched and tests executed.
pause
ENDLOCAL