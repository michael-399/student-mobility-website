import os

from dotenv import load_dotenv

load_dotenv()


def _flag(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes", "on")


def _csv(name: str, default: str) -> list[str]:
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]


class Config:
    SECRET_KEY = os.getenv(
        "SECRET_KEY",
        "development-secret-key",
    )

    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://postgres:postgres@localhost:5432/mobility_flask",
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    UPLOAD_DIR = os.getenv(
        "UPLOAD_DIR",
        "uploads",
    )

    # Session cookie.  Authentication is the cookie, so these settings are
    # what stop it being read by scripts, sent to another site, or sent in
    # the clear.
    SESSION_COOKIE_HTTPONLY = True
    # "Lax" is right when the browser app is served from this same origin.
    # A separate front-end origin needs "None", which browsers only accept
    # together with Secure -- so that pairing must be deliberate.
    SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")
    SESSION_COOKIE_SECURE = _flag("SESSION_COOKIE_SECURE")

    # Browser origins allowed to call this API with credentials.  A
    # wildcard is not usable here: browsers reject "*" on a credentialed
    # request, so the front-end origin has to be named.
    CORS_ORIGINS = _csv("CORS_ORIGINS", "http://localhost:4200")
