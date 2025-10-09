@echo off
REM Quick start script for local development on Windows

echo 🚀 Starting Exotel-Slack Complete System...
echo.

REM Check if .env exists
if not exist .env (
    echo ⚠️  .env file not found!
    echo 📋 Creating from env.example...
    copy env.example .env >nul
    echo ✅ Created .env file
    echo.
    echo ⚙️  Please edit .env with your credentials:
    echo    - SLACK_WEBHOOK_URL
    echo    - ASSEMBLYAI_API_KEY
    echo    - EXOTEL_API_KEY
    echo    - EXOTEL_API_TOKEN
    echo    - EXOTEL_SID
    echo.
    echo Then run this script again.
    pause
    exit /b 1
)

REM Check if virtual environment exists
if not exist venv (
    echo 📦 Creating virtual environment...
    python -m venv venv
    echo ✅ Virtual environment created
)

REM Activate virtual environment
echo 🔌 Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies
echo 📥 Installing dependencies...
pip install -q -r requirements.txt
echo ✅ Dependencies installed
echo.

REM Create directories
if not exist downloads mkdir downloads
if not exist data mkdir data

REM Start the application
echo 🌟 Starting application...
echo 📡 Server will be available at: http://localhost:8000
echo 🏥 Health check: http://localhost:8000/health
echo 📚 API docs: http://localhost:8000/docs
echo.
echo Press Ctrl+C to stop
echo.

python app.py

