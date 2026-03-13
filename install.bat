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

echo Installing PyAudio...
pip install --no-cache-dir pyaudio --only-binary :all:
if %errorlevel% neq 0 (
    echo [WARN] No prebuilt PyAudio wheel found. Trying pipwin...
    pip install --no-cache-dir pipwin
    pipwin install pyaudio
    if %errorlevel% neq 0 (
        echo [ERROR] PyAudio install failed.
        echo   Please install Microsoft C++ Build Tools from:
        echo   https://visualstudio.microsoft.com/visual-cpp-build-tools/
        echo   Then re-run install.bat
        pause
        exit /b 1
    )
)

echo Installing remaining dependencies...
pip install --no-cache-dir deepgram-sdk>=3.0.0,<4.0.0 python-dotenv>=1.0.0 requests>=2.31.0 pynput>=1.7.6 pyautogui>=0.9.54 pyperclip>=1.8.0 pystray>=0.19.5 Pillow>=10.0.0
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install dependencies.
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
    echo   If you add non-ASCII keyterms later, save .env as UTF-8
)

echo.
echo ========================================
echo   Done! Run with:
echo     .venv\Scripts\python floating_window.py
echo ========================================
pause
