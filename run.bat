@echo off
setlocal
echo 🚀 Spotify Smart Downloader - Windows Bootstrapper
echo --------------------------------------------------
echo 📢 IMPORTANT: Google Chrome must be installed for the scraper to work!
echo --------------------------------------------------

:: 1. Check for Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo 🔍 Python not found. Attempting to install via winget...
    where winget >nul 2>&1
    if %errorlevel% equ 0 (
        winget install -e --id Python.Python.3 --accept-package-agreements --accept-source-agreements
        if %errorlevel% neq 0 (
            echo ❌ Automatic install failed. Please install Python manually from python.org
            pause
            exit /b 1
        )
        echo ✅ Python installed successfully. Please restart this script.
        pause
        exit /b 0
    ) else (
        echo ❌ winget not found. Please install Python from python.org
        pause
        exit /b 1
    )
)

:: 2. Check for Chrome (Quick path check)
reg query "HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe" >nul 2>&1
if %errorlevel% neq 0 (
    echo 🔍 Google Chrome not found. It is required for the scraper.
    echo 🛠️ Attempting to install via winget...
    where winget >nul 2>&1
    if %errorlevel% equ 0 (
        winget install -e --id Google.Chrome --accept-package-agreements --accept-source-agreements
        if %errorlevel% neq 0 (
             echo ⚠️ Chrome auto-install failed. Please install it manually.
        )
    ) else (
        echo ⚠️ winget not found. Please install Google Chrome manually.
    )
)

:: 2. Setup Backend
cd backend
if not exist "venv" (
    python -m venv venv
)
call venv\Scripts\activate
pip install -r requirements.txt

:: 3. Start Backend
start /b python main.py

:: 4. Check for Flutter
where flutter >nul 2>&1
if %errorlevel% equ 0 (
    echo 📱 Flutter detected. Starting frontend...
    cd ../frontend
    if not exist "windows" (
        flutter create . --no-pub
    )
    flutter pub get
    flutter run -d windows
) else (
    echo 🔍 Flutter not found. Attempting to install via winget...
    where winget >nul 2>&1
    if %errorlevel% equ 0 (
        winget install -e --id Flutter.Flutter --accept-package-agreements --accept-source-agreements
        if %errorlevel% equ 0 (
            echo ✅ Flutter installed. Please restart this script to apply PATH changes.
            pause
            exit /b 0
        ) else (
            echo ❌ Flutter auto-install failed. Please install it manually.
        )
    ) else (
        echo ⚠️ Flutter not found in PATH.
        echo Please install Flutter to run the frontend Windows app.
    )
)

pause
