from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.csrf import ensure_csrf_token, require_csrf
from app.deps import get_db, require_user
from app.models import Card, User
from app.render import render

router = APIRouter()


@router.get("/cards", response_class=HTMLResponse)
def list_cards(
    request: Request,
    q: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
    csrf_token: str = Depends(ensure_csrf_token),  # noqa: ARG001 - sets cookie
):
    query = db.query(Card).filter(Card.user_id == user.id)
    if q:
        like = f"%{q}%"
        query = query.filter(or_(Card.english.ilike(like), Card.translation.ilike(like)))
    cards = query.order_by(Card.created_at.desc()).all()
    return render(
        request,
        "cards/list.html",
        {"cards": cards, "q": q or ""},
        user=user,
    )


@router.get("/cards/new", response_class=HTMLResponse)
def new_card_form(
    request: Request,
    user: User = Depends(require_user),
    csrf_token: str = Depends(ensure_csrf_token),  # noqa: ARG001
):
    return render(
        request,
        "cards/form.html",
        {"card": None, "action": "/cards", "submit_label": "Create card"},
        user=user,
    )


@router.post("/cards")
async def create_card(
    request: Request,
    english: str = Form(..., max_length=255),
    translation: str = Form(..., max_length=255),
    example: str | None = Form(None, max_length=2000),
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
    _csrf: None = Depends(require_csrf),
):
    card = Card(
        user_id=user.id,
        english=english.strip(),
        translation=translation.strip(),
        example=(example or "").strip() or None,
    )
    db.add(card)
    db.commit()
    return RedirectResponse(url="/cards", status_code=303)


@router.get("/cards/{card_id}/edit", response_class=HTMLResponse)
def edit_card_form(
    card_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
    csrf_token: str = Depends(ensure_csrf_token),  # noqa: ARG001
):
    card = _get_owned_card(db, user, card_id)
    return render(
        request,
        "cards/form.html",
        {
            "card": card,
            "action": f"/cards/{card.id}",
            "submit_label": "Save changes",
        },
        user=user,
    )


@router.post("/cards/{card_id}")
async def update_card(
    card_id: int,
    english: str = Form(..., max_length=255),
    translation: str = Form(..., max_length=255),
    example: str | None = Form(None, max_length=2000),
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
    _csrf: None = Depends(require_csrf),
):
    card = _get_owned_card(db, user, card_id)
    card.english = english.strip()
    card.translation = translation.strip()
    card.example = (example or "").strip() or None
    db.commit()
    return RedirectResponse(url="/cards", status_code=303)


@router.delete("/cards/{card_id}")
async def delete_card(
    card_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
    _csrf: None = Depends(require_csrf),
):
    card = _get_owned_card(db, user, card_id)
    db.delete(card)
    db.commit()
    return Response(status_code=200)


def _get_owned_card(db: Session, user: User, card_id: int) -> Card:
    card = db.get(Card, card_id)
    if card is None or card.user_id != user.id:
        raise HTTPException(status_code=404, detail="Card not found")
    return card
