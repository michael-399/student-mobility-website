"""Domain error type.

Services raise ``AppError`` with a stable string code (the same codes the
original TypeScript services threw, e.g. "MISSING_FILE", "INVALID_STATUS").
Routers translate those codes into the exact HTTP status + message the
Angular frontend expects — the mapping lives in the routers because, in
the legacy controllers, the same code sometimes maps to different HTTP
statuses depending on the endpoint.
"""


class AppError(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)
