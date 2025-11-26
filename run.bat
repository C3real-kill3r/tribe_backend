@echo off
REM Robust Windows batch script for running Tribe Backend

setlocal enabledelayedexpansion

REM Script directory
cd /d "%~dp0"

REM Print header
echo.
echo ============================================================
echo           Tribe Backend - Development Server
echo ============================================================
echo.

REM Check Python version
echo Checking Python version...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.11+
    exit /b 1
)
echo [OK] Python found

REM Setup virtual environment
echo.
echo Setting up virtual environment...
if not exist "venv" (
    python -m venv venv
    echo [OK] Virtual environment created
) else (
    echo [INFO] Virtual environment already exists
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Upgrade pip
echo.
echo Upgrading pip...
python -m pip install --upgrade pip --quiet

REM Install dependencies
echo.
echo Installing dependencies...
if exist "requirements.txt" (
    pip install -r requirements.txt --quiet
    echo [OK] Dependencies installed
) else (
    echo [ERROR] requirements.txt not found
    exit /b 1
)

REM Check .env file
if not exist ".env" (
    if exist ".env.example" (
        echo.
        echo [WARNING] .env file not found, creating from .env.example...
        copy .env.example .env
        echo [WARNING] Please update .env with your configuration!
    ) else (
        echo [ERROR] .env file not found and .env.example doesn't exist
        exit /b 1
    )
)

REM Run migrations (optional)
echo.
echo Checking database migrations...
python -m alembic upgrade head >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Migration check failed, continuing...
)

REM Start server
echo.
echo ============================================================
echo Starting development server...
echo API will be available at: http://localhost:8000
echo API Documentation: http://localhost:8000/docs
echo Press Ctrl+C to stop
echo ============================================================
echo.

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

