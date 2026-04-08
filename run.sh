#!/bin/bash

# Spotify Smart Downloader - Bootstrapper
# This script prepares the environment and launches the application.

set -e

# Kill any processes stuck on Port 17017 (standard default) to ensure a clean start
echo "🧹 Cleaning up old port remnants..."
lsof -ti:17017 | xargs kill -9 2>/dev/null || true
rm -f .port # Clear legacy files

echo "🚀 Starting Spotify Smart Downloader Setup..."

# 1. Check for Python
if ! command -v python3 &> /dev/null; then
    echo "🔍 Python 3 not found. Attempting to install via Homebrew..."
    if ! command -v brew &> /dev/null; then
        echo "❌ Homebrew not found. Please install Homebrew first: https://brew.sh/"
        exit 1
    fi
    brew install python
fi

# 2. Check for Google Chrome (macOS specific check)
if [ "$(uname)" == "Darwin" ]; then
    if [ ! -d "/Applications/Google Chrome.app" ]; then
        echo "🔍 Google Chrome not found. Required for the scraper."
        echo "🛠️  Attempting to install via Homebrew..."
        if command -v brew &> /dev/null; then
            brew install --cask google-chrome
        else
            echo "⚠️ Homebrew not found. Please install Google Chrome manually."
        fi
    fi
fi

# 2. Setup Backend Environment
echo "📦 Preparing backend..."
if [ ! -d "backend/venv" ]; then
    python3 -m venv backend/venv
fi
source backend/venv/bin/activate
pip install -r backend/requirements.txt

# 3. Start Backend in Background
echo "⚙️  Starting FastAPI Backend..."
# Use a fresh export to ensure current folder takes precedence
export PYTHONPATH="."
python3 -m backend.main &
BACKEND_PID=$!

# Wait for backend to be healthy
echo "⏳ Waiting for backend to warm up on Port 17017..."
ASSIGNED_PORT="17017"
echo "📡 Backend using FIXED port: $ASSIGNED_PORT"

while ! curl -s http://127.0.0.1:$ASSIGNED_PORT/status > /dev/null; do
    sleep 0.5
done
echo "✅ Backend is healthy on port $ASSIGNED_PORT."

# 4. Check for Flutter
if command -v flutter &> /dev/null; then
    echo "📱 Flutter detected. Starting frontend..."
    export SKIP_BACKEND_SPAWN=1
    cd frontend
    if [ ! -d "macos" ] && [ ! -d "windows" ] && [ ! -d "android" ]; then
        flutter create . --no-pub
    fi
    flutter pub get
    flutter run -d macos --dart-define=BACKEND_PORT=$ASSIGNED_PORT
else
    echo "🔍 Flutter not found. Attempting to install via Homebrew..."
    if command -v brew &> /dev/null; then
        brew install --cask flutter
        echo "✅ Flutter installed. Please restart this script to apply PATH changes."
        exit 0
    else
        echo "⚠️ Flutter not found in PATH."
        echo "Please visit http://127.0.0.1:$ASSIGNED_PORT for the API."
    fi
fi

# Cleanup on exit
trap "kill $BACKEND_PID 2>/dev/null || true" EXIT
wait
