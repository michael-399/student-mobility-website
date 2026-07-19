"""FastAPI application entry point.

Equivalent of the legacy cmd/main.ts: mounts the API under /api, serves
uploaded files at /uploads, exposes /health, and seeds demo data on
startup.  Database schema is managed by Alembic (run before the server
starts — see entrypoint.sh), not created here.
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.routers import auth, lecturer, office, reference, student
from app.core.config import settings
from app.db.seed import seed
from app.db.session import SessionLocal
from app.http import HttpError


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Populate demo users/institutions if the database is empty.
    async with SessionLocal() as session:
        await seed(session)
    yield


app = FastAPI(title="Student Mobility API (FastAPI)", lifespan=lifespan)


@app.exception_handler(HttpError)
async def http_error_handler(_request: Request, exc: HttpError):
    # Legacy responses use a top-level {"error": "..."} body.
    return JSONResponse(status_code=exc.status_code, content={"error": exc.message})


# API routes under /api (mirrors the legacy router mounting).
app.include_router(auth.router, prefix="/api")
app.include_router(reference.institutions_router, prefix="/api")
app.include_router(reference.lecturers_router, prefix="/api")
app.include_router(student.router, prefix="/api")
app.include_router(lecturer.router, prefix="/api")
app.include_router(office.router, prefix="/api")

# Serve uploaded files at /uploads/<filename>.
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")


@app.get("/health")
async def health():
    return {"status": "ok"}
