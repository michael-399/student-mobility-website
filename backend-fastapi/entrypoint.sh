#!/bin/sh
# Apply database migrations, then launch the API server.
set -e

alembic upgrade head
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
