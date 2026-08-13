from unittest.mock import MagicMock

import pytest

from job_scanner.analyzer import analyze_fit
from job_scanner.models import Category, InsightKind, Posting, Requirement, Responsibility, Verdict


def _posting() -> Posting:
    return Posting(
        title="Backend Engineer",
        company="Acme",
        location="Remote",
        seniority="Senior",
        responsibilities=[Responsibility(id="resp-1", text="Own the API", source_quote="own the API")],
        requirements=[Requirement(id="req-1", text="Python", category=Category.REQUIRED, source_quote="Python")],
    )


def _mock_client(raw_output: dict, raw_search_actions: list[dict] | None = None) -> MagicMock:
    client = MagicMock()
    client.call_tool_with_search.return_value = (raw_output, raw_search_actions or [])
    return client


def test_analyze_fit_builds_insights_with_assigned_ids():
    raw_output = {
        "summary": "Overall fit summary text.",
        "verdict": "strong_match",
        "insights": [
            {"text": "Strong Python background", "kind": "strength", "supporting_ids": ["req-1"]},
        ],
    }
    client = _mock_client(raw_output)

    result = analyze_fit(_posting(), "5 years of Python experience.", client)

    assert result.summary == "Overall fit summary text."
    assert result.verdict == Verdict.STRONG_MATCH
    assert result.insights[0].id == "insight-1"
    assert result.insights[0].kind == InsightKind.STRENGTH
    assert result.dropped_count == 0
    assert result.search_actions == []


def test_analyze_fit_drops_insight_citing_unknown_id_but_keeps_the_rest():
    raw_output = {
        "summary": "Overall fit summary text.",
        "verdict": "stretch",
        "insights": [
            {"text": "Bogus insight", "kind": "gap", "supporting_ids": ["req-99"]},
            {"text": "Strong Python background", "kind": "strength", "supporting_ids": ["req-1"]},
        ],
    }
    client = _mock_client(raw_output)

    result = analyze_fit(_posting(), "profile text", client)

    assert len(result.insights) == 1
    assert result.insights[0].id == "insight-1"
    assert result.insights[0].text == "Strong Python background"
    assert result.dropped_count == 1
    assert result.search_actions == []


def test_analyze_fit_includes_search_actions_when_present():
    raw_output = {
        "summary": "Overall fit summary text.",
        "verdict": "strong_match",
        "insights": [
            {"text": "Strong Python background", "kind": "strength", "supporting_ids": ["req-1"]},
        ],
    }
    raw_search_actions = [
        {"query": "example query", "results": [{"title": "Example Result", "url": "https://example.com/result"}]}
    ]
    client = _mock_client(raw_output, raw_search_actions)

    result = analyze_fit(_posting(), "profile text", client)

    assert len(result.search_actions) == 1
    assert result.search_actions[0].query == "example query"
    assert result.search_actions[0].results[0].title == "Example Result"


def test_analyze_fit_raises_clear_error_when_summary_is_missing_on_every_attempt():
    raw_output = {
        "verdict": "strong_match",
        "insights": [
            {"text": "Strong Python background", "kind": "strength", "supporting_ids": ["req-1"]},
        ],
    }
    client = _mock_client(raw_output)

    with pytest.raises(RuntimeError, match="incomplete"):
        analyze_fit(_posting(), "profile text", client)

    assert client.call_tool_with_search.call_count == 2


def test_analyze_fit_raises_clear_error_when_verdict_is_missing_on_every_attempt():
    raw_output = {
        "summary": "Overall fit summary text.",
        "insights": [
            {"text": "Strong Python background", "kind": "strength", "supporting_ids": ["req-1"]},
        ],
    }
    client = _mock_client(raw_output)

    with pytest.raises(RuntimeError, match="incomplete"):
        analyze_fit(_posting(), "profile text", client)

    assert client.call_tool_with_search.call_count == 2


def test_analyze_fit_raises_clear_error_when_verdict_is_not_a_valid_option():
    raw_output = {
        "summary": "Overall fit summary text.",
        "verdict": "definitely_hire_them",
        "insights": [
            {"text": "Strong Python background", "kind": "strength", "supporting_ids": ["req-1"]},
        ],
    }
    client = _mock_client(raw_output)

    with pytest.raises(RuntimeError, match="incomplete"):
        analyze_fit(_posting(), "profile text", client)

    assert client.call_tool_with_search.call_count == 2


def test_analyze_fit_drops_malformed_insight_item_that_is_not_an_object():
    raw_output = {
        "summary": "Overall fit summary text.",
        "verdict": "strong_match",
        "insights": [
            "not a valid insight object",
            {"text": "Strong Python background", "kind": "strength", "supporting_ids": ["req-1"]},
        ],
    }
    client = _mock_client(raw_output)

    result = analyze_fit(_posting(), "profile text", client)

    assert len(result.insights) == 1
    assert result.insights[0].text == "Strong Python background"
    assert result.dropped_count == 1


def test_analyze_fit_drops_insight_with_non_string_supporting_id():
    raw_output = {
        "summary": "Overall fit summary text.",
        "verdict": "strong_match",
        "insights": [
            {"text": "Weird citation", "kind": "strength", "supporting_ids": [{"weird": "dict"}]},
            {"text": "Strong Python background", "kind": "strength", "supporting_ids": ["req-1"]},
        ],
    }
    client = _mock_client(raw_output)

    result = analyze_fit(_posting(), "profile text", client)

    assert len(result.insights) == 1
    assert result.insights[0].text == "Strong Python background"
    assert result.dropped_count == 1


def test_analyze_fit_retries_when_verdict_is_not_a_string():
    raw_output = {
        "summary": "Overall fit summary text.",
        "verdict": ["not", "a", "string"],
        "insights": [
            {"text": "Strong Python background", "kind": "strength", "supporting_ids": ["req-1"]},
        ],
    }
    client = _mock_client(raw_output)

    with pytest.raises(RuntimeError, match="incomplete"):
        analyze_fit(_posting(), "profile text", client)

    assert client.call_tool_with_search.call_count == 2


def test_analyze_fit_drops_insight_with_no_supporting_ids():
    raw_output = {
        "summary": "Overall fit summary text.",
        "verdict": "strong_match",
        "insights": [
            {"text": "Uncited claim", "kind": "strength", "supporting_ids": []},
            {"text": "Strong Python background", "kind": "strength", "supporting_ids": ["req-1"]},
        ],
    }
    client = _mock_client(raw_output)

    result = analyze_fit(_posting(), "profile text", client)

    assert len(result.insights) == 1
    assert result.insights[0].text == "Strong Python background"
    assert result.dropped_count == 1


def test_analyze_fit_drops_insight_with_non_string_text():
    raw_output = {
        "summary": "Overall fit summary text.",
        "verdict": "strong_match",
        "insights": [
            {"text": 123, "kind": "strength", "supporting_ids": ["req-1"]},
            {"text": "Strong Python background", "kind": "strength", "supporting_ids": ["req-1"]},
        ],
    }
    client = _mock_client(raw_output)

    result = analyze_fit(_posting(), "profile text", client)

    assert len(result.insights) == 1
    assert result.insights[0].text == "Strong Python background"
    assert result.dropped_count == 1


def test_analyze_fit_drops_insight_with_invalid_kind():
    raw_output = {
        "summary": "Overall fit summary text.",
        "verdict": "strong_match",
        "insights": [
            {"text": "Neutral observation", "kind": "neutral", "supporting_ids": ["req-1"]},
            {"text": "Strong Python background", "kind": "strength", "supporting_ids": ["req-1"]},
        ],
    }
    client = _mock_client(raw_output)

    result = analyze_fit(_posting(), "profile text", client)

    assert len(result.insights) == 1
    assert result.insights[0].text == "Strong Python background"
    assert result.dropped_count == 1


def test_analyze_fit_raises_clear_error_when_insights_is_not_a_list():
    raw_output = {
        "summary": "Overall fit summary text.",
        "verdict": "strong_match",
        "insights": "this should have been an array of insight objects",
    }
    client = _mock_client(raw_output)

    with pytest.raises(RuntimeError, match="incomplete"):
        analyze_fit(_posting(), "profile text", client)

    assert client.call_tool_with_search.call_count == 2


def test_analyze_fit_retries_once_and_succeeds_if_second_attempt_is_complete():
    incomplete_output = {
        "insights": [
            {"text": "Strong Python background", "kind": "strength", "supporting_ids": ["req-1"]},
        ]
    }
    complete_output = {
        "summary": "Overall fit summary text.",
        "verdict": "weak_fit",
        "insights": [
            {"text": "Strong Python background", "kind": "strength", "supporting_ids": ["req-1"]},
        ],
    }
    client = MagicMock()
    client.call_tool_with_search.side_effect = [(incomplete_output, []), (complete_output, [])]

    result = analyze_fit(_posting(), "profile text", client)

    assert result.summary == "Overall fit summary text."
    assert result.verdict == Verdict.WEAK_FIT
    assert client.call_tool_with_search.call_count == 2
