"""Pydantic request bodies for JSON endpoints."""

from datetime import datetime

from pydantic import BaseModel


class LoginBody(BaseModel):
    email: str | None = None
    password: str | None = None


class RegisterBody(BaseModel):
    email: str | None = None
    password: str | None = None
    name: str | None = None
    role: str | None = None


class EvaluateBody(BaseModel):
    status: str | None = None
    reason: str | None = None


class DatesBody(BaseModel):
    actualArrivalDate: datetime | None = None
    actualDepartureDate: datetime | None = None
