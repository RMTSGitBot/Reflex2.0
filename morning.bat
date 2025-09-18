@echo off
call venv\Scripts\activate.bat
start "Reflexion Main" python main.py
python -m unittest discover -s tests -p "test_*.py"
pause