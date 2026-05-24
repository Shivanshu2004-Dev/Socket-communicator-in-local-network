#!/bin/bash
# File Transfer App - Quick Start (Linux/Mac)

echo ""
echo "========================================"
echo "  Chat & File Transfer Application"
echo "========================================"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed"
    echo "Please install Python 3.7+ using your package manager"
    echo ""
    echo "Ubuntu/Debian: sudo apt-get install python3 python3-pip"
    echo "macOS: brew install python3"
    exit 1
fi

# Check if requirements are installed
if ! python3 -c "import flask" 2>/dev/null; then
    echo ""
    echo "Installing required packages..."
    pip3 install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "Error: Failed to install requirements"
        exit 1
    fi
fi

echo ""
echo "Dependencies installed successfully!"
echo ""
echo "Starting the application..."
echo ""

# Create a temp file for server PID
PIDFILE="/tmp/filetransfer_server.pid"
WEBAPP_PIDFILE="/tmp/filetransfer_webapp.pid"

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "Shutting down..."
    if [ -f "$PIDFILE" ]; then
        kill $(cat $PIDFILE) 2>/dev/null
    fi
    if [ -f "$WEBAPP_PIDFILE" ]; then
        kill $(cat $WEBAPP_PIDFILE) 2>/dev/null
    fi
    exit 0
}

# Set trap to cleanup on Ctrl+C
trap cleanup SIGINT

# Start the server in background
echo "Starting Chat Server on port 9009..."
python3 server.py > /tmp/server.log 2>&1 &
echo $! > $PIDFILE
sleep 2

# Start the web app in background
echo "Starting Web Application on port 5000..."
python3 web_app.py > /tmp/webapp.log 2>&1 &
echo $! > $WEBAPP_PIDFILE
sleep 2

echo ""
echo "========================================"
echo "Opening browser at http://localhost:5000"
echo "========================================"
echo ""
echo "To access the app:"
echo "  Local:  http://localhost:5000"
echo "  Remote: http://YOUR_IP:5000"
echo ""

# Try to open browser
if command -v xdg-open &> /dev/null; then
    xdg-open http://localhost:5000 2>/dev/null &
elif command -v open &> /dev/null; then
    open http://localhost:5000 2>/dev/null &
fi

echo "Both servers are running"
echo "Press Ctrl+C to stop the application"
echo ""

# Wait indefinitely
wait
