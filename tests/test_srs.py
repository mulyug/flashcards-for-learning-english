from datetime import datetime, timedelta, timezone

import pytest

from app.srs import DEFAULT_EASE, MIN_EASE, Grade, apply_grade

NOW = datetime(2026, 4, 28, 12, 0, tzinfo=timezone.utc)


def test_first_review_easy_sets_interval_one_and_increases_ease():
    s = apply_grade(
        Grade.EASY, repetitions=0, ease_factor=DEFAULT_EASE, interval_days=0, now=NOW
    )
    assert s.repetitions == 1
    assert s.interval_days == 1
    assert s.due_at == NOW + timedelta(days=1)
    assert s.last_reviewed_at == NOW
    assert s.ease_factor == pytest.approx(2.6)


def test_first_review_medium_keeps_progress_and_drops_ease():
    s = apply_grade(
        Grade.MEDIUM, repetitions=0, ease_factor=DEFAULT_EASE, interval_days=0, now=NOW
    )
    assert s.repetitions == 1
    assert s.interval_days == 1
    assert s.ease_factor == pytest.approx(2.36)


def test_first_review_hard_resets_progress():
    s = apply_grade(
        Grade.HARD, repetitions=3, ease_factor=2.5, interval_days=15, now=NOW
    )
    assert s.repetitions == 0
    assert s.interval_days == 1
    assert s.ease_factor == pytest.approx(2.18)


def test_second_successful_review_jumps_to_six_days():
    s = apply_grade(
        Grade.EASY, repetitions=1, ease_factor=2.6, interval_days=1, now=NOW
    )
    assert s.repetitions == 2
    assert s.interval_days == 6
    assert s.due_at == NOW + timedelta(days=6)


def test_third_review_uses_ease_factor_for_interval():
    s = apply_grade(
        Grade.MEDIUM, repetitions=2, ease_factor=2.5, interval_days=6, now=NOW
    )
    assert s.repetitions == 3
    assert s.interval_days == round(6 * 2.5)
    assert s.ease_factor == pytest.approx(2.36)


def test_ease_factor_floor():
    s = apply_grade(
        Grade.HARD, repetitions=2, ease_factor=MIN_EASE, interval_days=10, now=NOW
    )
    assert s.ease_factor == MIN_EASE


def test_hard_does_not_increment_reps_even_when_already_high():
    s = apply_grade(
        Grade.HARD, repetitions=10, ease_factor=2.4, interval_days=30, now=NOW
    )
    assert s.repetitions == 0
    assert s.interval_days == 1


def test_easy_after_many_reps_grows_interval():
    s = apply_grade(
        Grade.EASY, repetitions=5, ease_factor=2.7, interval_days=50, now=NOW
    )
    assert s.repetitions == 6
    assert s.interval_days == round(50 * 2.7)
    assert s.ease_factor == pytest.approx(2.8)
