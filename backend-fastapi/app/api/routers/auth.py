"""Auth routes: POST /auth/login and POST /auth/register.

The register route is wired correctly here (the legacy version was
unreachable because of a missing leading slash) and login returns a
proper 400 for invalid credentials (the legacy controller had a typo
that swallowed that case).
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_token
from app.db.session import get_db
from app.errors import AppError
from app.http import HttpError
from app.schemas import LoginBody, RegisterBody
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


def _user_payload(user) -> dict:
    return {"id": str(user.id), "email": user.email, "name": user.name, "role": user.role}


@router.post("/login")
async def login(body: LoginBody, db: AsyncSession = Depends(get_db)):
    if not body.email or not body.password:
        raise HttpError(400, "Email and password required")
    try:
        user = await auth_service.login(db, body.email, body.password)
    except AppError as e:
        if e.code == "NO_USER_WITH_THIS_EMAIL":
            raise HttpError(400, "No user with this email")
        if e.code == "INVALID_CREDENTIALS":
            raise HttpError(400, "Invalid credentials")
        raise HttpError(500, "Login failed")

    token = create_token(user.id)
    return {"token": token, "user": _user_payload(user)}


@router.post("/register", status_code=201)
async def register(body: RegisterBody, db: AsyncSession = Depends(get_db)):
    try:
        user = await auth_service.register(db, body.email, body.password, body.name, body.role)
    except AppError as e:
        # The legacy controller returned 404 for all of these.
        if e.code == "ALL_FIELDS_REQUIRED":
            raise HttpError(404, "All fields are required")
        if e.code == "INVALID_ROLE":
            raise HttpError(404, "Invalid role")
        if e.code == "EMAIL_IN_USE":
            raise HttpError(404, "Email is already registered")
        raise HttpError(500, "Registration failed")

    token = create_token(user.id)
    return {"token": token, "user": _user_payload(user)}
