@echo off
REM ContextSnap Manager - Easy Windows Launcher
REM Run this file to start the ContextSnap management interface

echo ========================================
echo ContextSnap Local LLM Manager
echo ========================================

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.8 or higher
    pause
    exit /b 1
)

REM Navigate to scripts directory
cd /d "%~dp0"

REM Run the manager
echo Starting ContextSnap Manager...
echo.
python manage.py

echo.
echo Press any key to exit...
pause >nul
