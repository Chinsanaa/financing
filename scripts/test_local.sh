#!/bin/bash

echo "=========================================="
echo "Local Testing Guide — Financing SaaS"
echo "=========================================="
echo ""

# Check if we're in the right directory
if [ ! -f "backend/main.py" ]; then
    echo "ERROR: Run this from the project root (financing/)"
    exit 1
fi

echo "Step 1: Install Backend Dependencies"
echo "=====================================..."
cd backend
pip install -q -r requirements.txt 2>/dev/null && echo "[OK] Dependencies installed" || echo "[WARN] Could not install dependencies"

echo ""
echo "Step 2: Start FastAPI Backend"
echo "=============================="
echo "Running: uvicorn main:app --reload --host 127.0.0.1 --port 8000"
echo "Backend will be at: http://localhost:8000"
echo "Swagger UI at: http://localhost:8000/docs"
echo "Health check at: http://localhost:8000/health"
echo ""
echo ">>> KEEP THIS WINDOW OPEN <<<"
echo ""

# Start the backend
uvicorn main:app --reload --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!

# Wait for backend to start
sleep 3

# Test health check
echo ""
echo "Testing backend health..."
HEALTH=$(curl -s http://localhost:8000/health | grep -o '"status":"ok"')
if [ -n "$HEALTH" ]; then
    echo "[OK] Backend is running and healthy"
else
    echo "[WARN] Could not reach backend health check"
fi

echo ""
echo "Step 3: In a NEW TERMINAL, start Next.js Frontend"
echo "=================================================="
echo "Commands:"
echo "  cd frontend"
echo "  npm install"
echo "  cp .env.example .env.local"
echo "  # Edit .env.local with:"
echo "  #   NEXT_PUBLIC_SUPABASE_URL=https://<your-project-ref>.supabase.co"
echo "  #   NEXT_PUBLIC_SUPABASE_ANON_KEY=<your_anon_key>"
echo "  #   NEXT_PUBLIC_API_URL=http://localhost:8000"
echo "  npm run dev"
echo ""
echo "Frontend will be at: http://localhost:3000"
echo ""
echo "Step 4: Test the Full Flow"
echo "=========================="
echo "1. Open http://localhost:3000 in browser"
echo "2. Signup with a test email"
echo "3. Verify email (check Supabase dashboard → Auth → Users)"
echo "4. Login"
echo "5. Go to Upload tab and upload a CSV"
echo "6. Go to Label tab and categorize transactions"
echo "7. Go to Training tab and start model training"
echo "8. Watch the dashboard update"
echo ""
echo "Step 5: Check Backend Logs"
echo "=========================="
echo "Watch this window for FastAPI logs"
echo "Look for:"
echo "  - POST /uploads/ — CSV upload"
echo "  - POST /training/retrain — model training"
echo "  - Errors or exceptions"
echo ""
echo "Press Ctrl+C to stop the backend"

# Keep the script running
wait $BACKEND_PID
