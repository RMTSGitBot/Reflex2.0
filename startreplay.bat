@echo off
REM ============================================
REM Reflexion Replay Launcher - 2025-08-25
REM ============================================

REM Set working directory to the location of this script
cd /d "%~dp0"

REM --- Environment Variables ---
REM Enable replay mode
set REFLEXION_REPLAY=true

REM Set the replay start date (YYYY-MM-DD)
set REFLEXION_REPLAY_DATE=2025-08-25

REM Optional: set Python path if not in PATH
REM set PATH=C:\Path\To\Python;%PATH%

REM --- Launch Reflexion ---
echo [🛫] Starting Reflexion in REPLAY mode for %REFLEXION_REPLAY_DATE%...
python main.py

REM Keep window open after exit
pause