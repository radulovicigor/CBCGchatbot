#!/bin/bash
# Quick start script za Linux/Mac

echo "========================================"
echo "  CBCG SEPA Chatbot - Quick Start"
echo "========================================"
echo ""

# Provera Python instalacije
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python3 nije instaliran!"
    exit 1
fi

echo "[1/5] Kreiranje virtual environment..."
python3 -m venv .venv

echo "[2/5] Aktivacija venv..."
source .venv/bin/activate

echo "[3/5] Instalacija dependencies..."
pip install -r apps/api/requirements.txt
pip install -r apps/functions/requirements.txt
pip install -r apps/ingest/requirements.txt

echo "[4/5] Kreiranje .env fajla..."
python scripts/create_env.py

echo "[5/5] Setup zavrsen!"
echo ""
echo "========================================"
echo "  NACLEDNE KORACKE:"
echo "========================================"
echo "1. Edituj .env i popuni credentials"
echo "2. Pokreni: python scripts/validate_setup.py"
echo "3. Ako je sve OK: source .venv/bin/activate"
echo "4. Pokreni API: uvicorn apps.api.main:app --reload"
echo ""
echo "Detalji: START_HERE.md"
echo ""

