from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.csrf import ensure_csrf_token, require_csrf
from app.deps import get_db, require_user
from app.models import Card, User
from app.render import render
from app.srs import Grade, apply_grade

router = APIRouter()


def _due_count(db: Session, user: User, now: datetime) -> int:
    return (
        db.query(func.count(Card.id))
        .filter(Card.user_id == user.id, Card.due_at <= now)
        .scalar()
        or 0
    )


def _next_due(db: Session, user: User, now: datetime) -> Card | None:
    return (
        db.query(Card)
        .filter(Card.user_id == user.id, Card.due_at <= now)
        .order_by(Card.due_at.asc(), Card.id.asc())
        .first()
    )


@router.get("/review", response_class=HTMLResponse)
def review_index(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
    csrf_token: str = Depends(ensure_csrf_token),  # noqa: ARG001
):
    now = datetime.now(timezone.utc)
    return render(
        request,
        "review/index.html",
        {"due_count": _due_count(db, user, now)},
        user=user,
    )


@router.get("/review/next", response_class=HTMLResponse)
def next_card(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
    csrf_token: str = Depends(ensure_csrf_token),  # noqa: ARG001
):
    now = datetime.now(timezone.utc)
    card = _next_due(db, user, now)
    if card is None:
        return render(request, "review/_done.html", {}, user=user)
    return render(
        request,
        "review/_card.html",
        {"card": card, "remaining": _due_count(db, user, now)},
        user=user,
    )


@router.post("/review/{card_id}/grade", response_class=HTMLResponse)
async def grade_card(
    card_id: int,
    request: Request,
    grade: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
    _csrf: None = Depends(require_csrf),
):
    try:
        grade_enum = Grade(grade.lower())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid grade") from exc

    card = db.get(Card, card_id)
    if card is None or card.user_id != user.id:
        raise HTTPException(status_code=404, detail="Card not found")

    now = datetime.now(timezone.utc)
    state = apply_grade(
        grade_enum,
        repetitions=card.repetitions,
        ease_factor=card.ease_factor,
        interval_days=card.interval_days,
        now=now,
    )
    card.repetitions = state.repetitions
    card.ease_factor = state.ease_factor
    card.interval_days = state.interval_days
    card.due_at = state.due_at
    card.last_reviewed_at = state.last_reviewed_at
    db.commit()

    next_c = _next_due(db, user, now)
    if next_c is None:
        return render(request, "review/_done.html", {}, user=user)
    return render(
        request,
        "review/_card.html",
        {"card": next_c, "remaining": _due_count(db, user, now)},
        user=user,
    )
