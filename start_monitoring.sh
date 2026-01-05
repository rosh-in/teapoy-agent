#!/bin/bash
# Pi2Printer Email Monitoring Startup Script

echo "Starting Pi2Printer Email Monitor..."
echo "======================================"

cd "$(cd -- "$(dirname "$0")" >/dev/null 2>&1 && pwd)"

# Activate virtual environment
if [ -d "pi2printer-env" ]; then
    source pi2printer-env/bin/activate
    echo "✅ Virtual environment activated"
elif [ -d "printer-env" ]; then
    source printer-env/bin/activate
    echo "✅ Virtual environment activated"
else
    echo "❌ Virtual environment not found!"
    echo "   Please create it: python3 -m venv pi2printer-env"
    exit 1
fi

# Check if credentials exist
if [ ! -f "token.json" ]; then
    echo "❌ Gmail credentials not found!"
    echo "   Please run: python3 gmail_test.py"
    exit 1
fi

if [ ! -f ".env" ]; then
    echo "❌ Environment file not found!"
    echo "   Please create .env with GEMINI_API_KEY"
    exit 1
fi

# Show current status
echo "📊 Current Status:"
python3 pi2printer_cli.py status
echo ""

# Ask for monitoring interval
echo "Select monitoring interval:"
echo "  1) Real-time (1 minute) - High responsiveness"
echo "  2) Fast (2 minutes) - Good balance"
echo "  3) Normal (5 minutes) - Recommended default"
echo "  4) Slow (15 minutes) - Battery/resource saving"
echo "  5) Custom interval"
echo ""
echo -n "Choice (default: 3): "
read -t 15 choice
choice=${choice:-3}

case $choice in
    1) interval=1 ;;
    2) interval=2 ;;
    3) interval=5 ;;
    4) interval=15 ;;
    5) 
        echo -n "Enter custom interval in minutes: "
        read interval
        interval=${interval:-5}
        ;;
    *) interval=5 ;;
esac

echo "Starting monitoring with ${interval} minute intervals..."
echo "Press Ctrl+C to stop"
echo ""

# Warm up Ollama model
echo "🔥 Warming up Ollama model..."
./warm_up_ollama.sh
echo ""

# Start monitoring
python3 email_monitor.py --interval $interval
