from datetime import date

import pytest

from job_scanner import usage_guard


@pytest.fixture(autouse=True)
def reset_usage_guard_state():
    usage_guard._state["date"] = None
    usage_guard._state["count"] = 0
    yield
    usage_guard._state["date"] = None
    usage_guard._state["count"] = 0


def test_remaining_today_starts_at_the_full_daily_limit():
    assert usage_guard.remaining_today() == usage_guard.DAILY_POSTING_LIMIT


def test_record_processed_decreases_remaining_budget():
    usage_guard.record_processed(3)
    assert usage_guard.remaining_today() == usage_guard.DAILY_POSTING_LIMIT - 3


def test_record_processed_defaults_to_one():
    usage_guard.record_processed()
    assert usage_guard.remaining_today() == usage_guard.DAILY_POSTING_LIMIT - 1


def test_remaining_today_never_goes_negative():
    usage_guard.record_processed(usage_guard.DAILY_POSTING_LIMIT + 10)
    assert usage_guard.remaining_today() == 0


def test_counter_resets_when_the_utc_date_rolls_over(monkeypatch):
    usage_guard.record_processed(5)
    assert usage_guard.remaining_today() == usage_guard.DAILY_POSTING_LIMIT - 5

    monkeypatch.setattr(usage_guard, "_today", lambda: date(2099, 1, 1))

    assert usage_guard.remaining_today() == usage_guard.DAILY_POSTING_LIMIT
