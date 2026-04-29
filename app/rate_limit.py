from fastapi import Request
from fastapi.responses import JSONResponse, Response
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.csrf import CSRF_COOKIE_NAME
from app.templating import templates

limiter = Limiter(key_func=get_remote_address, default_limits=[])


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    accept = request.headers.get("accept", "")
    if "text/html" in accept:
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "csrf_token": request.cookies.get(CSRF_COOKIE_NAME, ""),
                "error": "Too many attempts. Please wait and try again later.",
                "current_user": None,
            },
            status_code=429,
        )
    return JSONResponse(
        status_code=429,
        content={"detail": "Too many requests. Please try again later."},
    )
