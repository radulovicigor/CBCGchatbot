@echo off
echo Starting CBCG Chatbot API...
echo.

cd /d "%~dp0"
call .venv\Scripts\activate.bat

echo Environment activated.
echo Starting API server on http://localhost:8000
echo Press Ctrl+C to stop
echo.

python -m uvicorn apps.api.main:app --reload --host 127.0.0.1 --port 8000

