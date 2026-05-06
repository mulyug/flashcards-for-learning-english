from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.config import get_settings
from app.csrf import CSRF_COOKIE_NAME, ensure_csrf_token, require_csrf
from app.deps import get_db
from app.models import User
from app.rate_limit import limiter
from app.security import (
    SESSION_COOKIE_NAME,
    clear_session_cookie,
    set_session_cookie,
    verify_password,
)
from app.templating import templates

router = APIRouter()
settings = get_settings()


@router.get("/login", response_class=HTMLResponse)
def login_form(
    request: Request,
    csrf_token: str = Depends(ensure_csrf_token),
):
    if request.cookies.get(SESSION_COOKIE_NAME):
        return RedirectResponse(url="/cards", status_code=303)
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "csrf_token": csrf_token, "error": None},
    )


@router.post("/login")
@limiter.limit(f"{settings.login_max_attempts}/{settings.login_lockout_minutes}minute")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
    _csrf: None = Depends(require_csrf),
):
    now = datetime.now(UTC)
    user = db.query(User).filter(User.username == username).first()

    if user and user.locked_until is not None:
        locked_until = _ensure_aware(user.locked_until)
        if locked_until > now:
            return _login_error(
                request, "Account temporarily locked. Please wait and try again."
            )

    if user is None or not verify_password(user.password_hash, password):
        if user is not None:
            user.failed_attempts += 1
            if user.failed_attempts >= settings.login_max_attempts:
                user.locked_until = now + timedelta(minutes=settings.login_lockout_minutes)
                user.failed_attempts = 0
            db.commit()
        return _login_error(request, "Invalid username or password.")

    user.failed_attempts = 0
    user.locked_until = None
    db.commit()

    response = RedirectResponse(url="/cards", status_code=303)
    set_session_cookie(response, user.id)
    return response


@router.post("/logout")
async def logout(_csrf: None = Depends(require_csrf)):
    response = RedirectResponse(url="/login", status_code=303)
    clear_session_cookie(response)
    return response


def _ensure_aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def _login_error(request: Request, message: str) -> HTMLResponse:
    csrf_token = request.cookies.get(CSRF_COOKIE_NAME) or getattr(
        request.state, "csrf_token", ""
    )
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "csrf_token": csrf_token, "error": message},
        status_code=400,
    )
