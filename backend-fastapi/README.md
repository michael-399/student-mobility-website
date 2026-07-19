# Student Mobility — FastAPI / PostgreSQL backend

A from-scratch reimplementation of the legacy Node/Express/Mongoose/MongoDB
backend using **Python 3.12 · FastAPI · async SQLAlchemy 2.0 · Alembic ·
PostgreSQL**. It is a **drop-in replacement**: the same Angular frontend
(unchanged) works against it because the HTTP contract — routes, JSON
shapes, `_id` naming, JWT auth, error messages — is reproduced exactly.

## Running both stacks at once

`docker compose up --build` (from this folder) starts the legacy and the new
stack side by side, each with its own database, backend, and a copy of the
identical Angular frontend:

| Stack | Frontend | Backend API | Database |
|-------|----------|-------------|----------|
| Legacy (Node/Mongo) | http://localhost:4200 | http://localhost:3000 | MongoDB :27017 |
| New (FastAPI/Postgres) | http://localhost:4201 | http://localhost:8000 | PostgreSQL :5432 |

Both frontends are the same code; only their `API_PROXY_TARGET` differs.
Log in with any seeded account (password `password`):
`student@test.com`, `lecturer@test.com`, `office@test.com` (+ `student2`, `lecturer2`).

Interactive API docs for the new backend: http://localhost:8000/docs.

## Architecture

Layering mirrors the original (`routes → controllers → services → repo`):

```
app/
  main.py            FastAPI app, /api mount, /uploads static, /health, startup seed
  core/              config (pydantic-settings) + security (bcrypt, JWT)
  db/                SQLAlchemy models, async session, seeder
  api/deps.py        get_current_user (JWT) + require_role (RBAC)   ~ auth/roles middleware
  api/routers/       auth, reference (institutions+lecturers), student, lecturer, office  ~ controllers
  services/          business logic + state machine                 ~ services
  repositories.py    scoped queries over the Application aggregate   ~ repo
  serializers.py     builds the exact legacy JSON (populate rules, _id, omit-None)
  schemas.py         Pydantic request bodies
  storage.py         multer-equivalent upload storage
alembic/             migrations (0001_initial creates the whole schema)
```

## Data model

MongoDB's embedded arrays are normalised into child tables, each with a
`position` column that preserves the original array index (the API
addresses sub-documents by index: `/learning-agreement/:index`,
`/scores/:scoreIndex`). Primary keys are UUIDs, serialised to JSON as
`_id`. See [`app/db/models.py`](app/db/models.py):

`applications` ← `learning_agreements`, `exam_mappings`, `modifications`
(← `modification_exam_mappings`), `exam_scores`. The optional
`transcriptOfRecords` object is flattened onto the `applications` row.

## Decisions applied

- **UUID PKs serialised as `_id`** — frontend untouched.
- **Async SQLAlchemy** (`asyncpg`).
- **Functionality kept 1:1** — no new features.
- **Bugs fixed** (were faults in the legacy code):
  1. `POST /api/auth/register` is now reachable (legacy route string
     `"register"` was missing its leading slash).
  2. Invalid-password login now returns `400 Invalid credentials` (legacy
     controller compared against a mis-spelled `"INVALID CRFEDENTIALS"` and
     silently hung).

## Local (non-Docker) run

Requires a running PostgreSQL. `pip install -r requirements.txt`, copy
`.env.example` to `.env`, then:

```
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

## Notes

- The database schema is owned by Alembic; `alembic upgrade head` runs
  before the server starts (see `entrypoint.sh` / the compose command).
- Demo data is seeded on startup only when the database is empty.
- Uploaded files live under `uploads/` (a Docker volume in compose).
