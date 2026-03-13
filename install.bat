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

pip install --no-cache-dir -r requirements.txt
if %errorlevel% neq 0 (
    echo [WARN] pyaudio build failed. Installing Microsoft C++ Build Tools via winget...
    winget install Microsoft.VisualStudio.2022.BuildTools --silent --override "--wait --quiet --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended"
    if %errorlevel% neq 0 (
        echo [WARN] winget install failed or already installed. Retrying pip...
    )
    pip install --no-cache-dir -r requirements.txt
    if %errorlevel% neq 0 (
        echo [ERROR] Still failed after installing Build Tools.
        echo   Please restart your PC and re-run install.bat
        pause
        exit /b 1
    )
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
