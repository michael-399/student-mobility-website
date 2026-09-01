"""Domain error type.

Services raise ``AppError`` with a stable string code (for example
"APPLICATION_NOT_FOUND", "INVALID_STATUS").  Routes translate those codes
into HTTP status codes and messages, so the service layer stays free of
any Flask or HTTP concern and can be exercised directly from tests.
"""


class AppError(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)
