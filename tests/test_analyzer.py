from unittest.mock import MagicMock

from job_scanner.analyzer import analyze_fit
from job_scanner.models import Category, InsightKind, Posting, Requirement, Responsibility


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
        "insights": [
            {"text": "Strong Python background", "kind": "strength", "supporting_ids": ["req-1"]},
        ]
    }
    client = _mock_client(raw_output)

    result = analyze_fit(_posting(), "5 years of Python experience.", client)

    assert result.insights[0].id == "insight-1"
    assert result.insights[0].kind == InsightKind.STRENGTH
    assert result.dropped_count == 0
    assert result.search_actions == []


def test_analyze_fit_drops_insight_citing_unknown_id_but_keeps_the_rest():
    raw_output = {
        "insights": [
            {"text": "Bogus insight", "kind": "gap", "supporting_ids": ["req-99"]},
            {"text": "Strong Python background", "kind": "strength", "supporting_ids": ["req-1"]},
        ]
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
        "insights": [
            {"text": "Strong Python background", "kind": "strength", "supporting_ids": ["req-1"]},
        ]
    }
    raw_search_actions = [
        {"query": "what is KQL", "results": [{"title": "Kusto Query Language", "url": "https://example.com/kql"}]}
    ]
    client = _mock_client(raw_output, raw_search_actions)

    result = analyze_fit(_posting(), "profile text", client)

    assert len(result.search_actions) == 1
    assert result.search_actions[0].query == "what is KQL"
    assert result.search_actions[0].results[0].title == "Kusto Query Language"


def test_analyze_fit_calls_client_with_search_capability():
    raw_output = {"insights": []}
    client = _mock_client(raw_output)

    analyze_fit(_posting(), "profile text", client)

    client.call_tool_with_search.assert_called_once()
    _, kwargs = client.call_tool_with_search.call_args
    assert kwargs["tool_name"] == "analyze_fit"
