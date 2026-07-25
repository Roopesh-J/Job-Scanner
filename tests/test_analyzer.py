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


def _mock_client(raw_output: dict) -> MagicMock:
    client = MagicMock()
    client.call_tool.return_value = raw_output
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
