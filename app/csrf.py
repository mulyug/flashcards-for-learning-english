import hmac
import secrets

from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.config import get_settings

CSRF_COOKIE_NAME = "csrf_token"
CSRF_HEADER_NAME = "X-CSRF-Token"
CSRF_FORM_FIELD = "csrf_token"


def _new_token() -> str:
    return secrets.token_urlsafe(32)


class CsrfMiddleware(BaseHTTPMiddleware):
    """Ensures every request has a CSRF token available.

    On the way in: read the cookie (or mint a new token if missing) and
    expose it on `request.state.csrf_token` so render helpers and templates
    can embed it into forms / HTMX headers.

    On the way out: set the cookie if the client did not already have it.
    No body manipulation, so this is safe to use as BaseHTTPMiddleware.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        existing = request.cookies.get(CSRF_COOKIE_NAME)
        token = existing or _new_token()
        request.state.csrf_token = token

        response = await call_next(request)

        if not existing:
            settings = get_settings()
            response.set_cookie(
                key=CSRF_COOKIE_NAME,
                value=token,
                httponly=False,
                secure=settings.cookie_secure,
                samesite="lax",
                path="/",
            )
        return response


def ensure_csrf_token(request: Request) -> str:
    """Convenience dep — returns the per-request CSRF token from state."""
    token = getattr(request.state, "csrf_token", None)
    if token is None:
        token = request.cookies.get(CSRF_COOKIE_NAME, "")
        request.state.csrf_token = token
    return token


async def require_csrf(request: Request) -> None:
    """Validate CSRF on unsafe requests via the double-submit cookie pattern.

    Submitted token may come from `X-CSRF-Token` header (HTMX) or a hidden
    `csrf_token` form field (plain HTML forms).
    """
    cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
    submitted = request.headers.get(CSRF_HEADER_NAME)
    if not submitted:
        content_type = request.headers.get("content-type", "")
        if (
            "application/x-www-form-urlencoded" in content_type
            or "multipart/form-data" in content_type
        ):
            try:
                form = await request.form()
            except Exception:
                form = None
            if form is not None:
                value = form.get(CSRF_FORM_FIELD)
                if isinstance(value, str):
                    submitted = value
    if (
        not cookie_token
        or not submitted
        or not hmac.compare_digest(cookie_token, submitted)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF token invalid")
