@echo off
REM Quick start script za Windows
echo ========================================
echo   CBCG SEPA Chatbot - Quick Start
echo ========================================
echo.

REM Provera Python instalacije
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python nije instaliran!
    pause
    exit /b 1
)

echo [1/5] Kreiranje virtual environment...
python -m venv .venv
if errorlevel 1 (
    echo [ERROR] Greska pri kreiranju venv
    pause
    exit /b 1
)

echo [2/5] Aktivacija venv...
call .venv\Scripts\activate.bat

echo [3/5] Instalacija dependencies...
pip install -r apps/api/requirements.txt
pip install -r apps/functions/requirements.txt
pip install -r apps/ingest/requirements.txt

echo [4/5] Kreiranje .env fajla...
python scripts/create_env.py

echo [5/5] Setup zavrsen!
echo.
echo ========================================
echo   NACLEDNE KORACKE:
echo ========================================
echo 1. Edituj .env i popuni credentials
echo 2. Pokreni: python scripts/validate_setup.py
echo 3. Ako je sve OK: .venv\Scripts\activate
echo 4. Pokreni API: uvicorn apps.api.main:app --reload
echo.
echo Detalji: START_HERE.md
echo.
pause

