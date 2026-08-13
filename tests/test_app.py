import anthropic
import httpx

from job_scanner.app import _fail_remaining, _is_systemic

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
