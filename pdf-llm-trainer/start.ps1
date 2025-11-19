# PowerShell script to start ASFC Application (Backend + Frontend)

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Starting ASFC Application (Backend + Frontend)" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Get script directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

# Function to kill process on port
function Stop-ProcessOnPort {
    param([int]$Port)
    
    $processes = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
    if ($processes) {
        foreach ($pid in $processes) {
            Write-Host "   Killing process $pid on port $Port..." -ForegroundColor Yellow
            Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
        }
        Start-Sleep -Seconds 2
    }
}

# Kill any existing process on port 5000
Write-Host "[1/3] Checking for existing processes on port 5000..." -ForegroundColor Yellow
try {
    Stop-ProcessOnPort -Port 5000
} catch {
    Write-Host "   No existing process found or unable to check" -ForegroundColor Gray
}

# Start backend
Write-Host "[2/3] Starting backend server on http://localhost:5000..." -ForegroundColor Yellow
Start-Process -NoNewWindow -FilePath "python" -ArgumentList "-m", "backend.start" -RedirectStandardOutput "backend.log" -RedirectStandardError "backend.log"
$backendProcess = Get-Process python | Where-Object { $_.Path -like "*python*" } | Select-Object -Last 1

Write-Host "   Backend started (PID: $($backendProcess.Id))" -ForegroundColor Green

# Wait for backend to start
Write-Host "   Waiting for backend to initialize..." -ForegroundColor Gray
$backendReady = $false
for ($i = 1; $i -le 10; $i++) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:5000/api/health" -Method GET -TimeoutSec 2 -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            Write-Host "   [OK] Backend is running!" -ForegroundColor Green
            $backendReady = $true
            break
        }
    } catch {
        if ($i -eq 10) {
            Write-Host "   [WARNING] Backend may still be starting..." -ForegroundColor Yellow
        } else {
            Start-Sleep -Seconds 1
        }
    }
}

# Start frontend
Write-Host "[3/3] Starting frontend server on http://localhost:5273..." -ForegroundColor Yellow
Set-Location frontend
Start-Process -NoNewWindow -FilePath "npm" -ArgumentList "run", "dev" -RedirectStandardOutput "..\frontend.log" -RedirectStandardError "..\frontend.log"
Start-Sleep -Seconds 2
$frontendProcess = Get-Process node | Select-Object -Last 1
Set-Location ..

Write-Host "   Frontend started (PID: $($frontendProcess.Id))" -ForegroundColor Green

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Both servers are running!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "✓ Backend:  http://localhost:5000" -ForegroundColor Green
Write-Host "✓ Frontend: http://localhost:5273" -ForegroundColor Green
Write-Host ""
Write-Host "Open your browser and go to: http://localhost:5273" -ForegroundColor Cyan
Write-Host ""
Write-Host "Logs:" -ForegroundColor Yellow
Write-Host "  - Backend:  Get-Content backend.log -Wait -Tail 20" -ForegroundColor Gray
Write-Host "  - Frontend: Get-Content frontend.log -Wait -Tail 20" -ForegroundColor Gray
Write-Host ""
Write-Host "Press Ctrl+C to stop both servers" -ForegroundColor Yellow
Write-Host ""

# Cleanup function
function Cleanup {
    Write-Host ""
    Write-Host "Stopping servers..." -ForegroundColor Yellow
    Stop-ProcessOnPort -Port 5000
    Stop-ProcessOnPort -Port 5273
    Write-Host "Servers stopped." -ForegroundColor Green
}

# Register cleanup on Ctrl+C
[Console]::TreatControlCAsInput = $false
$null = Register-ObjectEvent ([System.Console]) -EventName CancelKeyPress -Action {
    Cleanup
    exit
}

# Keep script running
Write-Host "Press Ctrl+C to stop both servers" -ForegroundColor Yellow
try {
    while ($true) {
        Start-Sleep -Seconds 5
    }
} catch {
    Write-Host "Error: $_" -ForegroundColor Red
} finally {
    Cleanup
}

