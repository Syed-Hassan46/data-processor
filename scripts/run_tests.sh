#!/usr/bin/env bash
set -e

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -q

echo "running lint..."
flake8 src/ tests/ --max-line-length=100

echo "running unit tests..."
pytest tests/unit/ --cov=src --cov-report=html -v

echo "running integration tests..."
pytest tests/integration/ -v

echo "done"
