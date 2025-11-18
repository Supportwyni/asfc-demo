#!/bin/bash

echo "============================================================"
echo "Starting ASFC Application (Backend + Frontend)"
echo "============================================================"
echo ""

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Store PIDs for cleanup
BACKEND_PID=""
FRONTEND_PID=""

# Cleanup function
cleanup() {
    echo ""
    echo "Stopping servers..."
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null || true
    fi
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null || true
    fi
    # Also kill by port in case PIDs didn't work
    if command -v lsof >/dev/null 2>&1; then
        lsof -ti:5000 | xargs kill -9 2>/dev/null || true
        lsof -ti:5173 | xargs kill -9 2>/dev/null || true
    fi
    exit 0
}

# Trap Ctrl+C
trap cleanup INT TERM

# Kill any existing process on port 5000
echo "[1/3] Checking for existing processes on port 5000..."

# Try different methods depending on OS
if command -v lsof >/dev/null 2>&1; then
    # Linux/Mac
    if lsof -Pi :5000 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        echo "   Killing existing process on port 5000..."
        lsof -ti:5000 | xargs kill -9 2>/dev/null || true
        sleep 2
    fi
elif command -v netstat >/dev/null 2>&1; then
    # Windows (Git Bash)
    PID=$(netstat -ano | grep :5000 | grep LISTENING | awk '{print $5}' | head -1)
    if [ ! -z "$PID" ]; then
        echo "   Killing existing process $PID on port 5000..."
        taskkill //F //PID $PID 2>/dev/null || kill -9 $PID 2>/dev/null || true
        sleep 2
    fi
fi

# Start backend in background
echo "[2/3] Starting backend server on http://localhost:5000..."
python -m backend.start > backend.log 2>&1 &
BACKEND_PID=$!
echo "   Backend started with PID: $BACKEND_PID"

# Wait for backend to start
echo "   Waiting for backend to initialize..."
for i in {1..10}; do
    if curl -s http://localhost:5000/api/health > /dev/null 2>&1; then
        echo "   [OK] Backend is running!"
        break
    fi
    if [ $i -eq 10 ]; then
        echo "   [WARNING] Backend may still be starting..."
    else
        sleep 1
    fi
done

# Start frontend
echo "[3/3] Starting frontend server on http://localhost:5173..."
cd frontend
npm run dev > ../frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..
echo "   Frontend started with PID: $FRONTEND_PID"

echo ""
echo "============================================================"
echo "Both servers are running!"
echo "============================================================"
echo ""
echo "✓ Backend:  http://localhost:5000 (PID: $BACKEND_PID)"
echo "✓ Frontend: http://localhost:5173 (PID: $FRONTEND_PID)"
echo ""
echo "Open your browser and go to: http://localhost:5173"
echo ""
echo "Logs:"
echo "  - Backend:  tail -f backend.log"
echo "  - Frontend: tail -f frontend.log"
echo ""
echo "Press Ctrl+C to stop both servers"
echo ""

# Keep script running and wait for both processes
wait $BACKEND_PID $FRONTEND_PID 2>/dev/null || {
    # If wait fails, just keep script alive
    while kill -0 $BACKEND_PID 2>/dev/null || kill -0 $FRONTEND_PID 2>/dev/null; do
        sleep 1
    done
}

