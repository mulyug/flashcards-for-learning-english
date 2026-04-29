from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum


class Grade(str, Enum):
    HARD = "hard"
    MEDIUM = "medium"
    EASY = "easy"


GRADE_QUALITY: dict[Grade, int] = {
    Grade.HARD: 2,
    Grade.MEDIUM: 3,
    Grade.EASY: 5,
}

DEFAULT_EASE = 2.5
MIN_EASE = 1.3


@dataclass(frozen=True)
class SrsState:
    repetitions: int
    ease_factor: float
    interval_days: int
    due_at: datetime
    last_reviewed_at: datetime


def apply_grade(
    grade: Grade,
    *,
    repetitions: int,
    ease_factor: float,
    interval_days: int,
    now: datetime,
) -> SrsState:
    """Apply a SM-2 grade to a card's state and return the new state.

    Maps Hard/Medium/Easy to SM-2 quality scores 2/3/5. q < 3 resets the
    repetition counter and schedules the card for tomorrow. Ease factor is
    floored at 1.3 to keep intervals from collapsing.
    """
    q = GRADE_QUALITY[grade]

    if q < 3:
        new_repetitions = 0
        new_interval = 1
    else:
        if repetitions == 0:
            new_interval = 1
        elif repetitions == 1:
            new_interval = 6
        else:
            new_interval = max(1, round(interval_days * ease_factor))
        new_repetitions = repetitions + 1

    new_ease = ease_factor + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
    new_ease = max(MIN_EASE, new_ease)

    return SrsState(
        repetitions=new_repetitions,
        ease_factor=new_ease,
        interval_days=new_interval,
        due_at=now + timedelta(days=new_interval),
        last_reviewed_at=now,
    )
