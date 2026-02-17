
@echo off
cd /d "%~dp0"
call venv\Scripts\activate.bat
cd execution
python main.py
pause
