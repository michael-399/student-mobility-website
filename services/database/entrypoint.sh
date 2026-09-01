#!/bin/sh
# Prepare the database, then launch the API server.
set -e

# The Postgres container hosts more than one database, and only the one
# named by POSTGRES_DB is created for us, so this backend creates its own
# on first start. Also waits for Postgres to accept connections.
python -m scripts.init_database

python -m flask --app main_module.py db upgrade -d migrations

# Optional: fill an empty database with development accounts.
if [ "${SEED_ON_START}" = "true" ]; then
    python -m seeds.dev_seed
fi

exec gunicorn \
    --bind 0.0.0.0:5000 \
    --workers "${WEB_CONCURRENCY:-2}" \
    --access-logfile - \
    "main_module:app"
