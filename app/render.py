from typing import Any

from fastapi import Request
from starlette.responses import Response

from app.csrf import CSRF_COOKIE_NAME
from app.models import User
from app.templating import templates


def render(
    request: Request,
    template: str,
    context: dict[str, Any] | None = None,
    *,
    user: User | None = None,
    status_code: int = 200,
    headers: dict[str, str] | None = None,
) -> Response:
    csrf_token = getattr(request.state, "csrf_token", None) or request.cookies.get(
        CSRF_COOKIE_NAME, ""
    )
    base_ctx: dict[str, Any] = {
        "request": request,
        "csrf_token": csrf_token,
        "current_user": user,
    }
    if context:
        base_ctx.update(context)
    return templates.TemplateResponse(
        template, base_ctx, status_code=status_code, headers=headers
    )
