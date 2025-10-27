#!/bin/bash
# Development starter - Linux/Mac

echo "========================================"
echo "  CBCG Chatbot - Development Mode"
echo "========================================"
echo ""

# Aktivacija venv
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
    echo "[OK] Virtual environment activated"
else
    echo "[ERROR] .venv nije kreiran"
    echo "Run: python setup.py"
    exit 1
fi

# Provera .env
if [ ! -f ".env" ]; then
    echo "[WARNING] .env ne postoji"
    echo "Creating from template..."
    python scripts/create_env.py
fi

# Meni
echo ""
echo "Izaberi opciju:"
echo ""
echo "1. Start API server"
echo "2. Run tests"
echo "3. Validate setup"
echo "4. Check Azure connection"
echo "5. Exit"
echo ""

read -p "Choice (1-5): " choice

case $choice in
    1)
        echo ""
        echo "Starting API server..."
        echo ""
        cd apps/api
        uvicorn main:app --reload --host 0.0.0.0 --port 8000
        ;;
    2)
        echo ""
        echo "Running tests..."
        echo ""
        python scripts/test_local.py
        ;;
    3)
        echo ""
        python scripts/validate_setup.py
        ;;
    4)
        echo ""
        python scripts/dev_helpers.py check-azure
        ;;
    5)
        exit 0
        ;;
esac

