import anthropic
import httpx

from job_scanner import usage_guard
from job_scanner.app import _apply_daily_budget, _fail_remaining, _is_systemic

_FAKE_REQUEST = httpx.Request("POST", "https://api.anthropic.com/v1/messages")


def _fake_response(status_code: int) -> httpx.Response:
    return httpx.Response(status_code, request=_FAKE_REQUEST)


def test_fail_remaining_marks_current_and_later_postings_not_earlier_ones():
    posting_inputs = [(1, "a"), (2, "b"), (3, "c"), (4, "d")]
    errors = [(1, "an earlier per-posting error")]

    _fail_remaining(posting_inputs, from_index=1, errors=errors)

    assert errors == [
        (1, "an earlier per-posting error"),
        (2, "There was an error while running one or more of the postings. Please try again in some time."),
        (3, "There was an error while running one or more of the postings. Please try again in some time."),
        (4, "There was an error while running one or more of the postings. Please try again in some time."),
    ]


def test_is_systemic_true_for_auth_rate_limit_and_connection_errors():
    assert _is_systemic(anthropic.APIConnectionError(request=_FAKE_REQUEST)) is True
    assert _is_systemic(
        anthropic.RateLimitError(message="rate limited", response=_fake_response(429), body=None)
    ) is True
    assert _is_systemic(
        anthropic.AuthenticationError(message="bad key", response=_fake_response(401), body=None)
    ) is True


def test_is_systemic_false_for_timeout_even_though_it_subclasses_connection_error():
    assert issubclass(anthropic.APITimeoutError, anthropic.APIConnectionError)
    assert _is_systemic(anthropic.APITimeoutError(request=_FAKE_REQUEST)) is False


def test_is_systemic_false_for_unrelated_exceptions():
    assert _is_systemic(ValueError("something else")) is False
    assert _is_systemic(RuntimeError("a friendly message")) is False


def test_apply_daily_budget_allows_everything_when_budget_covers_the_batch(monkeypatch):
    monkeypatch.setattr(usage_guard, "remaining_today", lambda: 10)
    posting_inputs = [(1, "a"), (2, "b")]
    errors = []

    result = _apply_daily_budget(posting_inputs, errors)

    assert result == posting_inputs
    assert errors == []


def test_apply_daily_budget_trims_batch_and_errors_the_rest(monkeypatch):
    monkeypatch.setattr(usage_guard, "remaining_today", lambda: 2)
    posting_inputs = [(1, "a"), (2, "b"), (3, "c"), (4, "d")]
    errors = []

    result = _apply_daily_budget(posting_inputs, errors)

    assert result == [(1, "a"), (2, "b")]
    assert errors == [
        (3, "Daily usage limit reached. Try again tomorrow."),
        (4, "Daily usage limit reached. Try again tomorrow."),
    ]


def test_apply_daily_budget_zero_remaining_errors_everything(monkeypatch):
    monkeypatch.setattr(usage_guard, "remaining_today", lambda: 0)
    posting_inputs = [(1, "a"), (2, "b")]
    errors = []

    result = _apply_daily_budget(posting_inputs, errors)

    assert result == []
    assert errors == [
        (1, "Daily usage limit reached. Try again tomorrow."),
        (2, "Daily usage limit reached. Try again tomorrow."),
    ]


def test_fail_remaining_accepts_a_custom_message():
    posting_inputs = [(1, "a"), (2, "b")]
    errors = []

    _fail_remaining(posting_inputs, from_index=0, errors=errors, message="custom message")

    assert errors == [(1, "custom message"), (2, "custom message")]
