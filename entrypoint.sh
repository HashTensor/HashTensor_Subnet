#!/bin/bash
set -e

# Run Alembic migrations
PYTHONPATH=. alembic upgrade head

# Start the FastAPI app
uvicorn src.main:app --host "${HOST:-0.0.0.0}" --port "${PORT:-8000}"