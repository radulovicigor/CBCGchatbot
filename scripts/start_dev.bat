@echo off
REM Development starter - Windows

echo ========================================
echo   CBCG Chatbot - Development Mode
echo ========================================
echo.

REM Aktivacija venv
if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
    echo [OK] Virtual environment activated
) else (
    echo [ERROR] .venv nije kreiran
    echo Run: python setup.py
    pause
    exit /b 1
)

REM Provera .env
if not exist .env (
    echo [WARNING] .env ne postoji
    echo Creating from template...
    python scripts/create_env.py
)

REM Meni
echo.
echo Izaberi opciju:
echo.
echo 1. Start API server
echo 2. Run tests
echo 3. Validate setup
echo 4. Check Azure connection
echo 5. Exit
echo.

set /p choice="Choice (1-5): "

if "%choice%"=="1" (
    echo.
    echo Starting API server...
    echo.
    cd apps/api
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
)

if "%choice%"=="2" (
    echo.
    echo Running tests...
    echo.
    python scripts/test_local.py
    pause
)

if "%choice%"=="3" (
    echo.
    python scripts/validate_setup.py
    pause
)

if "%choice%"=="4" (
    echo.
    python scripts/dev_helpers.py check-azure
    pause
)

if "%choice%"=="5" (
    exit /b 0
)

pause

