# Overseas Mobility Management Platform

Web application for managing the administrative phases of a Ca' Foscari
**Overseas** mobility — before departure, during the mobility, and after the
return — for the *Databases Mod. 2* project (A.Y. 2025/2026).

A Flask + SQLAlchemy REST API over PostgreSQL, with an Angular single-page
front end.

## What it does

Three roles share one application record and move it through a fixed lifecycle:

| Role | Can do |
|---|---|
| **Student** | Create applications; propose the exam mapping; upload the Learning Agreement and, later, revisions of it; record arrival and departure dates; upload the Transcript of Records; enter grades and exam dates |
| **Academic coordinator** | Read the applications assigned to them; approve or reject each Learning Agreement version with a date and, on rejection, a reason; approve or reject each exam recognition |
| **Overseas office** | Read every application; maintain the list of partner institutions; sign off the pre-departure check; close the application |

Application lifecycle:

```text
created ──upload LA──▶ waiting_la_approval ──office sign-off──▶ pre_departure_completed
   ▲                          │                                          │
   └──── LA rejected ─────────┘                                   student arrives
                                                                         ▼
closed ◀── office closes ── under_exam_recognition ◀── transcript ── mobility_in_progress
                                                                         ▲   │
                                        LA modification approved ────────┘   │
                                        (back to waiting_la_approval) ◀───────┘
```

Every status change is written to `application_status_history`, so the whole
lifecycle of an application stays auditable.

## Stack

| Layer | Choice |
|---|---|
| Database | PostgreSQL 16 |
| ORM / migrations | SQLAlchemy 2 (Flask-SQLAlchemy 3), Alembic via Flask-Migrate |
| API | Flask 3, session-cookie authentication, Argon2id password hashing |
| Front end | Angular 22 (standalone components), plain CSS |
| Packaging | Docker Compose (Postgres + Flask + Angular dev server) |

## Repository layout

```text
services/database/          Flask API
  app/
    models/                 SQLAlchemy models (one module per aggregate)
    routes/                 Blueprints: auth, reference, student, coordinator, office
    services/               Domain logic and the status workflow
    repositories.py         Queries, including per-role ownership scoping
    serializers.py          Model → JSON
    http.py                 Domain error code → HTTP status
    storage.py              Uploaded-file storage
  migrations/               Alembic revisions
  seeds/dev_seed.py         Development accounts and partner institutions
  tests/                    pytest suite (services, routes, constraints, downloads)
  database_docs/            Requirements, conceptual schema, logical schema
frontend/                   Angular single-page app
docs/                       Project report (PDF) and presentation
docker-compose.yml
```

## Running it

### With Docker (everything)

```bash
docker compose up --build
```

- Front end: <http://localhost:4200>
- API: <http://localhost:5001/api>  (published on 5001 because macOS answers on
  5000 with its AirPlay receiver)
- Postgres: `localhost:5432`, database `mobility_flask`

The backend container creates its database if needed, applies the migrations,
and — with `SEED_ON_START=true`, the default in `docker-compose.yml` — loads the
development accounts.

### Locally, without Docker

Postgres must be reachable on `localhost:5432`.

```bash
cd services/database
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m scripts.init_database
flask --app main_module.py db upgrade -d migrations
python -m seeds.dev_seed
python main_module.py          # http://127.0.0.1:5001
```

Front end, in a second terminal:

```bash
cd frontend
npm install
npm start                      # http://localhost:4200, proxied to the API
```

### Seeded accounts

All five share the password `password`.

| Email | Role |
|---|---|
| `student@test.com`, `student2@test.com` | Student |
| `lecturer@test.com`, `lecturer2@test.com` | Academic coordinator |
| `office@test.com` | Overseas office |

The seed also loads eight partner institutions. It matches on natural keys, so
running it again updates rather than duplicates.

## API

Everything lives under `/api`. Authentication is a signed session cookie set by
`POST /api/login`; every other endpoint requires it, and each blueprint
requires one specific role.

| Method | Path | Role |
|---|---|---|
| `POST` | `/api/login`, `/api/logout` | public |
| `GET` | `/api/me` | any signed-in user |
| `GET` | `/api/reference/institutions`, `/api/reference/coordinators` | any signed-in user |
| `GET POST` | `/api/student/applications` | student |
| `GET PATCH DELETE` | `/api/student/applications/<id>` | student (own only) |
| `POST` | `/api/student/applications/<id>/learning-agreements` | student |
| `PATCH` | `/api/student/applications/<id>/mobility-dates` | student |
| `POST` | `/api/student/applications/<id>/transcript` | student |
| `PUT` | `/api/student/applications/<id>/exam-results` | student |
| `GET` | `/api/coordinator/applications[/<id>]` | coordinator (assigned only) |
| `POST` | `/api/coordinator/applications/<id>/learning-agreement/decision` | coordinator |
| `POST` | `/api/coordinator/exam-results/<id>/decision` | coordinator |
| `GET` | `/api/office/applications[?status=…]` | office |
| `POST` | `/api/office/applications/<id>/pre-departure`, `/close` | office |
| `GET POST PATCH` | `/api/office/institutions[/<id>]` | office |
| `POST` | `/api/office/institutions/<id>/deactivate`, `/reactivate` | office |
| `GET` | `…/learning-agreements/<version>/file`, `…/transcript/file` | student, coordinator, office |
| `GET` | `/health/database` | public |

Document downloads are served per role through the same ownership scoping as the
rest of the API, so a file can only be fetched by someone entitled to the
application it belongs to.

## Design notes

- **One transaction per request.** Services stop at `db.session.flush()`; the
  commit or rollback happens once, in `create_app`. Any response of 400 or worse
  rolls the request back, so a refused operation leaves nothing behind.
- **Ownership is enforced in the queries.** A student's lookup is scoped to their
  own applications and a coordinator's to those assigned to them, so an
  application belonging to someone else comes back as *not found* rather than
  *forbidden*, which keeps its existence private.
- **Modifications are versions.** A revised study plan is the next
  `learning_agreement` version with its own mappings. The mapping in force is the
  highest approved version, so an approved modification replaces it and a
  rejected one leaves the previous plan standing, with no rows moved or deleted.
- **Integrity is in the schema where it can be.** Enumerated status types,
  composite keys, `RESTRICT`/`CASCADE` foreign keys, and CHECK constraints for
  the academic-year format, positive credits, date ordering, and the legal
  combinations of decision status / decision date / rejection reason. Rules that
  span rows or depend on the caller are enforced in the service layer;
  `database_docs/logical_schema.md` lists which is which.
- **Passwords** are hashed with Argon2id; only the encoded hash is stored, and
  verification is done by the hashing library.

## Tests

```bash
cd services/database
pytest
```

The suite runs against `mobility_flask_test` on `localhost:5432` (override with
`DATABASE_URL`), which must exist and be migrated:

```bash
createdb mobility_flask_test
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/mobility_flask_test \
  flask --app main_module.py db upgrade -d migrations
```

It covers the three role services, the HTTP routes and their authorisation, the
database constraints, the seed, document downloads, and the application wiring.

## Documentation

| Document | Contents |
|---|---|
| `docs/report.pdf` | Project report: functionalities, conceptual and logical design, main queries, design choices, contributions |
| `services/database/database_docs/requirements_and_business_rules.md` | Functional requirements (FR-xx) and business rules (BR-xx) |
| `services/database/database_docs/conceptual_schema.md` | Entities, relationships, cardinalities, participation |
| `services/database/database_docs/logical_schema.md` | Tables, types, keys and constraints, and what the schema deliberately does not enforce |
