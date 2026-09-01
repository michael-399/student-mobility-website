"""Wait for Postgres and create this backend's database if it is missing.

The Postgres container only creates the one database named by
``POSTGRES_DB``, which a local (non-Docker) Postgres does not do at all,
so this backend creates its own database when it is missing, before
migrations can run.

Both steps are idempotent: an existing database is left alone, and a
Postgres that is already accepting connections is not waited for.
"""

import sys
import time

import psycopg
from psycopg import sql

from app.config import Config

# Postgres inside a container is reachable well before it finishes its
# own start-up, so a healthcheck is not always enough on a cold start.
CONNECT_TIMEOUT_SECONDS = 60
RETRY_INTERVAL_SECONDS = 1


def _connection_parts():
    """Split the configured URL into a maintenance URL and a database name.

    Creating a database requires connecting to a different one, so the
    connection is redirected to the always-present ``postgres`` database.
    """
    url = Config.SQLALCHEMY_DATABASE_URI
    # SQLAlchemy's driver suffix is not something libpq understands.
    libpq_url = url.replace("postgresql+psycopg://", "postgresql://")

    base, _, database = libpq_url.rpartition("/")
    database = database.split("?")[0]

    return (f"{base}/postgres", database)


def wait_for_postgres(maintenance_url: str) -> None:
    deadline = time.monotonic() + CONNECT_TIMEOUT_SECONDS
    last_error = None

    while time.monotonic() < deadline:
        try:
            with psycopg.connect(maintenance_url, connect_timeout=3):
                return
        except psycopg.OperationalError as error:
            last_error = error
            time.sleep(RETRY_INTERVAL_SECONDS)

    print(f"Postgres did not become reachable: {last_error}", file=sys.stderr)
    raise SystemExit(1)


def create_database_if_missing(maintenance_url: str, database: str) -> None:
    with psycopg.connect(maintenance_url, autocommit=True) as connection:
        exists = connection.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s",
            (database,),
        ).fetchone()

        if exists:
            print(f'Database "{database}" already exists.')

            return

        connection.execute(
            sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database))
        )
        print(f'Created database "{database}".')


def main() -> None:
    maintenance_url, database = _connection_parts()

    wait_for_postgres(maintenance_url)
    create_database_if_missing(maintenance_url, database)


if __name__ == "__main__":
    main()
