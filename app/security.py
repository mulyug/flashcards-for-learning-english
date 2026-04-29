from argon2 import PasswordHasher
from argon2.exceptions import (
    InvalidHashError,
    VerificationError,
    VerifyMismatchError,
)
from fastapi import Request, Response
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.config import get_settings

_settings = get_settings()
_ph = PasswordHasher()

SESSION_COOKIE_NAME = "session"
_SESSION_SALT = "flashcards-session"


def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(stored_hash: str, password: str) -> bool:
    try:
        return _ph.verify(stored_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(_settings.secret_key, salt=_SESSION_SALT)


def _make_cookie_value(user_id: int) -> str:
    return _serializer().dumps({"uid": user_id})


def _max_age_seconds() -> int:
    return _settings.session_max_age_days * 86400


def get_user_id_from_request(request: Request) -> int | None:
    raw = request.cookies.get(SESSION_COOKIE_NAME)
    if not raw:
        return None
    try:
        data = _serializer().loads(raw, max_age=_max_age_seconds())
    except (BadSignature, SignatureExpired):
        return None
    if not isinstance(data, dict):
        return None
    uid = data.get("uid")
    if not isinstance(uid, int):
        return None
    return uid


def set_session_cookie(response: Response, user_id: int) -> None:
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=_make_cookie_value(user_id),
        max_age=_max_age_seconds(),
        httponly=True,
        secure=_settings.cookie_secure,
        samesite="lax",
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
