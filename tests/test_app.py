from unittest.mock import MagicMock, patch

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


def test_run_analysis_counts_budget_even_when_a_posting_fails():
    usage_guard._state["date"] = None
    usage_guard._state["count"] = 0

    fake_client = MagicMock()
    fake_client.fetch_url_text.side_effect = RuntimeError("boom")

    try:
        with patch("job_scanner.app.st") as mock_st, patch(
            "job_scanner.app.LLMClient", return_value=fake_client
        ):
            mock_st.session_state = MagicMock()
            mock_st.spinner.return_value.__enter__ = MagicMock()
            mock_st.spinner.return_value.__exit__ = MagicMock(return_value=False)

            from job_scanner.app import run_analysis

            run_analysis("some background", [(1, "https://example.com/job")])

        assert usage_guard.remaining_today() == usage_guard.DAILY_POSTING_LIMIT - 1
    finally:
        usage_guard._state["date"] = None
        usage_guard._state["count"] = 0


def _fake_extraction_and_analysis(title: str):
    from job_scanner.analyzer import AnalysisResult
    from job_scanner.extractor import ExtractionResult
    from job_scanner.models import Category, Posting, Requirement, Responsibility, Verdict

    posting = Posting(
        title=title,
        company="Acme",
        responsibilities=[Responsibility(id="resp-1", text="Own the API", source_quote="own the API")],
        requirements=[Requirement(id="req-1", text="Kubernetes", category=Category.REQUIRED, source_quote="K8s")],
    )
    extraction = ExtractionResult(posting=posting, dropped_ids=[])
    analysis = AnalysisResult(
        summary="summary",
        verdict=Verdict.STRONG_MATCH,
        insights=[],
        dropped_count=0,
        search_actions=[],
    )
    return extraction, analysis


def test_run_analysis_populates_gap_patterns_on_success():
    usage_guard._state["date"] = None
    usage_guard._state["count"] = 0

    from job_scanner.models import GapPattern, GapPatternItem

    fake_client = MagicMock()
    fake_pattern = GapPattern(label="Kubernetes", items=[GapPatternItem(posting_number=1, insight_id="insight-1")])

    extraction_a, analysis_a = _fake_extraction_and_analysis("Posting A")
    extraction_b, analysis_b = _fake_extraction_and_analysis("Posting B")

    try:
        with patch("job_scanner.app.st") as mock_st, patch(
            "job_scanner.app.LLMClient", return_value=fake_client
        ), patch(
            "job_scanner.app.extract_posting", side_effect=[extraction_a, extraction_b]
        ), patch(
            "job_scanner.app.analyze_fit", side_effect=[analysis_a, analysis_b]
        ), patch(
            "job_scanner.app.find_gap_patterns", return_value=[fake_pattern]
        ) as mock_find_gap_patterns:
            mock_st.session_state = MagicMock()
            mock_st.spinner.return_value.__enter__ = MagicMock()
            mock_st.spinner.return_value.__exit__ = MagicMock(return_value=False)

            from job_scanner.app import run_analysis

            run_analysis("some background", [(1, "posting text A"), (2, "posting text B")])

            assert mock_st.session_state.gap_patterns == [fake_pattern]
            assert len(mock_st.session_state.results) == 2
            mock_find_gap_patterns.assert_called_once()
    finally:
        usage_guard._state["date"] = None
        usage_guard._state["count"] = 0


def test_run_analysis_isolates_gap_pattern_failure_from_results():
    usage_guard._state["date"] = None
    usage_guard._state["count"] = 0

    fake_client = MagicMock()
    extraction_a, analysis_a = _fake_extraction_and_analysis("Posting A")
    extraction_b, analysis_b = _fake_extraction_and_analysis("Posting B")

    try:
        with patch("job_scanner.app.st") as mock_st, patch(
            "job_scanner.app.LLMClient", return_value=fake_client
        ), patch(
            "job_scanner.app.extract_posting", side_effect=[extraction_a, extraction_b]
        ), patch(
            "job_scanner.app.analyze_fit", side_effect=[analysis_a, analysis_b]
        ), patch(
            "job_scanner.app.find_gap_patterns", side_effect=RuntimeError("boom")
        ):
            mock_st.session_state = MagicMock()
            mock_st.spinner.return_value.__enter__ = MagicMock()
            mock_st.spinner.return_value.__exit__ = MagicMock(return_value=False)

            from job_scanner.app import run_analysis

            run_analysis("some background", [(1, "posting text A"), (2, "posting text B")])

            assert mock_st.session_state.gap_patterns == []
            assert len(mock_st.session_state.results) == 2
    finally:
        usage_guard._state["date"] = None
        usage_guard._state["count"] = 0
