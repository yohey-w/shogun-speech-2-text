@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
    echo [ERROR] .venv not found. Run install.bat first.
    pause
    exit /b 1
)
call .venv\Scripts\activate.bat
python floating_window.py
