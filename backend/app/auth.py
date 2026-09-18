"""Single shared passphrase gate for the hosted demo.

Not a real auth layer: the app has one demo user and no accounts. The point is
only that a leaked URL does not let strangers spend the OpenRouter credits.
"""

import secrets

from fastapi import Request
from fastapi.responses import JSONResponse

HEADER = "x-demo-password"

# Everything the API exposes; static files and /health stay open.
PROTECTED_PREFIXES = ("/chat", "/transactions", "/budgets", "/goals", "/auth", "/docs", "/redoc", "/openapi.json")


def is_protected(path: str) -> bool:
    return any(path == p or path.startswith(p + "/") for p in PROTECTED_PREFIXES)


async def demo_password_middleware(request: Request, call_next):
    password = request.app.state.demo_password
    # CORS preflights carry no custom headers and must pass for the browser to
    # send the real request.
    if password and request.method != "OPTIONS" and is_protected(request.url.path):
        supplied = request.headers.get(HEADER, "")
        if not secrets.compare_digest(supplied.encode(), password.encode()):
            return JSONResponse({"detail": "Password della demo mancante o errata."}, status_code=401)
    return await call_next(request)
