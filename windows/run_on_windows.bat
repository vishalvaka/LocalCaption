@echo off
echo LocalCaption - Windows Launcher
echo ================================

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://python.org
    pause
    exit /b 1
)

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt

REM Download models if needed
if not exist "models" (
    echo Downloading ASR models...
    python setup_models.py
)

REM Run LocalCaption
echo Starting LocalCaption...
python run.py

pause