.PHONY: dev install test check-canonical lint pdfs

install:
	pip install -r requirements.txt

dev:
	uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

test:
	pytest tests/ -v

check-canonical:
	python scripts/check_canonical.py

lint:
	ruff check .

# Render all non-stub one-pagers to static/pdfs/ (needs DATABASE_URL + quarto)
pdfs:
	python -m scripts.render_pdfs

# Run before every release
preflight: check-canonical test
	@echo "Preflight passed."
