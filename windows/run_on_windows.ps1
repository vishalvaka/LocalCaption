# LocalCaption - Windows PowerShell Launcher
Write-Host "LocalCaption - Windows Launcher" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Green

# Check if Python is installed
try {
    $pythonVersion = python --version 2>&1
    Write-Host "Found Python: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "Python is not installed or not in PATH" -ForegroundColor Red
    Write-Host "Please install Python 3.8+ from https://python.org" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Install dependencies
Write-Host "Installing dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt

# Download models if needed
if (-not (Test-Path "models")) {
    Write-Host "Downloading ASR models..." -ForegroundColor Yellow
    python setup_models.py
}

# Run LocalCaption
Write-Host "Starting LocalCaption..." -ForegroundColor Green
python run.py

Read-Host "Press Enter to exit"