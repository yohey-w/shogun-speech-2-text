@echo off
cd /d "%~dp0"
echo ========================================
echo   shogun-speech-2-text installer
echo ========================================
echo.

where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Install Python 3.10+ from https://python.org
    pause
    exit /b 1
)

echo [1/3] Creating virtual environment...
python -m venv .venv
if %errorlevel% neq 0 (
    echo [ERROR] Failed to create venv.
    pause
    exit /b 1
)

echo [2/3] Installing dependencies...
call .venv\Scripts\activate.bat
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] pip install failed. If pyaudio fails, try:
    echo   pip install pipwin ^&^& pipwin install pyaudio
    pause
    exit /b 1
)

echo [3/3] Setting up .env...
if not exist .env (
    copy .env.example .env
    echo.
    echo [ACTION REQUIRED] Edit .env and set your DEEPGRAM_API_KEY
    echo   Get your free key at https://console.deepgram.com
    echo   Sign up with Google = $200 free credit
)

echo.
echo ========================================
echo   Done! Run with:
echo     .venv\Scripts\python floating_window.py
echo ========================================
pause
