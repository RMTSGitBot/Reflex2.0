@echo off
cd /d "C:\Users\mikem\OneDrive\Projects\reflexion"
python -m dbmanager.app
if %errorlevel% neq 0 (
    echo An error occurred while running the dbmanager engine.
    exit /b %errorlevel%
)
pause