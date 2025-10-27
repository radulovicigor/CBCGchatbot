# Makefile za CBCG Chatbot

.PHONY: help setup install test run-api run-functions create-indexes ingest clean

help:
	@echo "CBCG SEPA Chatbot - Komande:"
	@echo "  make setup          - Setup virtualno okruženje"
	@echo "  make install        - Instaliraj sve zavisnosti"
	@echo "  make create-indexes - Kreiraj Azure AI Search indekse"
	@echo "  make ingest         - Ingest SEPA_QnA.pdf"
	@echo "  make run-api        - Pokreni FastAPI server"
	@echo "  make run-functions  - Pokreni Functions lokalno"
	@echo "  make test           - Pokreni testove"
	@echo "  make clean          - Očisti cache"

setup:
	python -m venv .venv
	@echo "Run: .venv\Scripts\activate  (Windows) ili source .venv/bin/activate (Linux/Mac)"

install:
	pip install -r apps/api/requirements.txt
	pip install -r apps/functions/requirements.txt
	pip install -r apps/ingest/requirements.txt

create-indexes:
	python -c "from apps.ingest.push_to_search import create_index_faq, create_index_news; create_index_faq(); create_index_news()"

ingest:
	python -m apps.ingest.push_to_search data/SEPA_QnA.pdf

run-api:
	cd apps/api && uvicorn main:app --reload --host 0.0.0.0 --port 8000

run-functions:
	cd apps/functions && func start

test:
	pytest tests/ -v

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +

