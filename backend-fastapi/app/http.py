"""HTTP error type + helper to translate domain error codes.

``HttpError`` carries the exact status code and message the Angular
frontend expects, and is rendered as a top-level ``{"error": ...}`` body
(matching the legacy Express responses) by the handler in main.py.
"""

from app.errors import AppError


class HttpError(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(message)


def translate(err: AppError, mapping: dict[str, tuple[int, str]], default: tuple[int, str]) -> HttpError:
    status_code, message = mapping.get(err.code, default)
    return HttpError(status_code, message)
