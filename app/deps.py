from collections.abc import Generator

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import User
from app.security import get_user_id_from_request


class AuthRedirect(Exception):
    """Raised by route dependencies when an unauthenticated user hits a
    protected page; the global handler converts this into a 303 redirect to
    /login (or HX-Redirect for HTMX)."""


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_optional_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    user_id = get_user_id_from_request(request)
    if user_id is None:
        return None
    return db.get(User, user_id)


def require_user(request: Request, db: Session = Depends(get_db)) -> User:
    user_id = get_user_id_from_request(request)
    if user_id is None:
        raise AuthRedirect()
    user = db.get(User, user_id)
    if user is None:
        raise AuthRedirect()
    return user
