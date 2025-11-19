@echo off
REM Batch script to start ASFC Application (Backend + Frontend)

echo ============================================================
echo Starting ASFC Application (Backend + Frontend)
echo ============================================================
echo.

REM Get script directory
cd /d "%~dp0"

REM Kill any existing process on port 5000
echo [1/3] Checking for existing processes on port 5000...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5000 ^| findstr LISTENING') do (
    echo    Killing process %%a on port 5000...
    taskkill /F /PID %%a >nul 2>&1
)
timeout /t 2 /nobreak >nul

REM Start backend
echo [2/3] Starting backend server on http://localhost:5000...
start "ASFC Backend" /min cmd /c "python -m backend.start > backend.log 2>&1"

REM Wait for backend to start
echo    Waiting for backend to initialize...
timeout /t 3 /nobreak >nul

REM Check if backend is running
set BACKEND_READY=0
for /L %%i in (1,1,10) do (
    powershell -Command "try { $response = Invoke-WebRequest -Uri 'http://localhost:5000/api/health' -Method GET -TimeoutSec 2 -ErrorAction Stop; if ($response.StatusCode -eq 200) { exit 0 } } catch { exit 1 }" >nul 2>&1
    if !errorlevel! equ 0 (
        echo    [OK] Backend is running!
        set BACKEND_READY=1
        goto :backend_ready
    )
    timeout /t 1 /nobreak >nul
)
:backend_ready

REM Start frontend
echo [3/3] Starting frontend server on http://localhost:5273...
cd frontend
start "ASFC Frontend" /min cmd /c "npm run dev > ..\frontend.log 2>&1"
cd ..

echo.
echo ============================================================
echo Both servers are running!
echo ============================================================
echo.
echo Backend:  http://localhost:5000
echo Frontend: http://localhost:5273
echo.
echo Open your browser and go to: http://localhost:5273
echo.
echo Logs:
echo   - Backend:  type backend.log
echo   - Frontend: type frontend.log
echo.
echo Press any key to stop both servers...
pause >nul

REM Kill processes on ports
echo.
echo Stopping servers...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5000 ^| findstr LISTENING') do (
    taskkill /F /PID %%a >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5273 ^| findstr LISTENING') do (
    taskkill /F /PID %%a >nul 2>&1
)

echo Servers stopped.
pause

