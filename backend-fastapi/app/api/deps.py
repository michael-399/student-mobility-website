"""Request dependencies: authentication and role authorisation.

``get_current_user`` mirrors the legacy ``verifyToken`` middleware (Bearer
token → verify → load user, 401 on any failure).  ``require_role`` mirrors
the ``requireRole`` middleware factory (403 when the role is not allowed).
"""

import uuid
from collections.abc import Awaitable, Callable

import jwt
from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.db.models import User
from app.db.session import get_db


async def get_current_user(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail={"error": "No token provided"})

    token = authorization[7:]
    try:
        decoded = decode_token(token)
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail={"error": "Invalid token"})

    try:
        user_id = uuid.UUID(str(decoded.get("id")))
    except (ValueError, TypeError):
        raise HTTPException(status_code=401, detail={"error": "Invalid token"})

    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=401, detail={"error": "User not found"})
    return user


def require_role(*roles: str) -> Callable[..., Awaitable[User]]:
    async def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail={"error": "Insufficient permissions"})
        return user

    return checker
