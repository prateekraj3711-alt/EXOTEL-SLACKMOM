#!/bin/bash
# Quick start script for local development

echo "🚀 Starting Exotel-Slack Complete System..."
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found!"
    echo "📋 Creating from env.example..."
    cp env.example .env
    echo "✅ Created .env file"
    echo ""
    echo "⚙️  Please edit .env with your credentials:"
    echo "   - SLACK_WEBHOOK_URL"
    echo "   - ASSEMBLYAI_API_KEY"
    echo "   - EXOTEL_API_KEY"
    echo "   - EXOTEL_API_TOKEN"
    echo "   - EXOTEL_SID"
    echo ""
    echo "Then run this script again."
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -q -r requirements.txt
echo "✅ Dependencies installed"
echo ""

# Create directories
mkdir -p downloads
mkdir -p data

# Load environment variables
export $(cat .env | grep -v '^#' | xargs)

# Start the application
echo "🌟 Starting application..."
echo "📡 Server will be available at: http://localhost:8000"
echo "🏥 Health check: http://localhost:8000/health"
echo "📚 API docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop"
echo ""

python app.py

