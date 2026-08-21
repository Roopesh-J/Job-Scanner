from dataclasses import dataclass
from unittest.mock import MagicMock

from job_scanner.models import Category, InsightKind, Posting, Requirement, Responsibility
from job_scanner.patterns import find_gap_patterns


@dataclass
class _FakeInsight:
    id: str
    text: str
    kind: InsightKind


@dataclass
class _FakeAnalysis:
    insights: list


@dataclass
class _FakeExtraction:
    posting: Posting


def _posting(title: str = "Backend Engineer", company: str = "Acme") -> Posting:
    return Posting(
        title=title,
        company=company,
        responsibilities=[Responsibility(id="resp-1", text="Own the API", source_quote="own the API")],
        requirements=[Requirement(id="req-1", text="Kubernetes", category=Category.REQUIRED, source_quote="K8s")],
    )


def _result(title: str, insights: list) -> dict:
    return {"extraction": _FakeExtraction(posting=_posting(title=title)), "analysis": _FakeAnalysis(insights=insights)}


def _mock_client(raw_output: dict) -> MagicMock:
    client = MagicMock()
    client.call_tool.return_value = raw_output
    return client


def test_returns_empty_and_skips_llm_call_when_batch_has_fewer_than_two_postings():
    results = [_result("Only Posting", [_FakeInsight(id="insight-1", text="No Rust", kind=InsightKind.GAP)])]
    client = MagicMock()

    patterns = find_gap_patterns(results, client)

    assert patterns == []
    client.call_tool.assert_not_called()


def test_returns_empty_and_skips_llm_call_when_no_gap_insights_exist():
    results = [
        _result("Posting A", [_FakeInsight(id="insight-1", text="Strong Python", kind=InsightKind.STRENGTH)]),
        _result("Posting B", [_FakeInsight(id="insight-1", text="Strong Go", kind=InsightKind.STRENGTH)]),
    ]
    client = MagicMock()

    patterns = find_gap_patterns(results, client)

    assert patterns == []
    client.call_tool.assert_not_called()


def test_builds_pattern_from_well_formed_response():
    results = [
        _result("Posting A", [_FakeInsight(id="insight-1", text="No Kubernetes", kind=InsightKind.GAP)]),
        _result("Posting B", [_FakeInsight(id="insight-1", text="No K8s experience", kind=InsightKind.GAP)]),
    ]
    raw_output = {
        "groups": [
            {
                "label": "Kubernetes",
                "items": [
                    {"posting_number": 1, "insight_id": "insight-1"},
                    {"posting_number": 2, "insight_id": "insight-1"},
                ],
            }
        ]
    }
    client = _mock_client(raw_output)

    patterns = find_gap_patterns(results, client)

    assert len(patterns) == 1
    assert patterns[0].label == "Kubernetes"
    assert [(i.posting_number, i.insight_id) for i in patterns[0].items] == [(1, "insight-1"), (2, "insight-1")]


def test_drops_group_with_out_of_range_posting_number_but_keeps_valid_groups():
    results = [
        _result("Posting A", [_FakeInsight(id="insight-1", text="No Kubernetes", kind=InsightKind.GAP)]),
        _result("Posting B", [_FakeInsight(id="insight-1", text="No K8s", kind=InsightKind.GAP)]),
    ]
    raw_output = {
        "groups": [
            {"label": "Bogus", "items": [{"posting_number": 99, "insight_id": "insight-1"}]},
            {
                "label": "Kubernetes",
                "items": [
                    {"posting_number": 1, "insight_id": "insight-1"},
                    {"posting_number": 2, "insight_id": "insight-1"},
                ],
            },
        ]
    }
    client = _mock_client(raw_output)

    patterns = find_gap_patterns(results, client)

    assert len(patterns) == 1
    assert patterns[0].label == "Kubernetes"


def test_drops_item_citing_insight_id_that_is_not_a_gap_on_that_posting():
    results = [
        _result(
            "Posting A",
            [
                _FakeInsight(id="insight-1", text="No Kubernetes", kind=InsightKind.GAP),
                _FakeInsight(id="insight-2", text="Strong Python", kind=InsightKind.STRENGTH),
            ],
        ),
        _result("Posting B", [_FakeInsight(id="insight-1", text="No K8s", kind=InsightKind.GAP)]),
    ]
    raw_output = {
        "groups": [
            {
                "label": "Kubernetes",
                "items": [
                    {"posting_number": 1, "insight_id": "insight-2"},
                    {"posting_number": 2, "insight_id": "insight-1"},
                ],
            }
        ]
    }
    client = _mock_client(raw_output)

    patterns = find_gap_patterns(results, client)

    assert patterns == []


def test_drops_group_that_validates_down_to_a_single_item():
    results = [
        _result("Posting A", [_FakeInsight(id="insight-1", text="No Kubernetes", kind=InsightKind.GAP)]),
        _result("Posting B", [_FakeInsight(id="insight-1", text="No K8s", kind=InsightKind.GAP)]),
    ]
    raw_output = {
        "groups": [
            {
                "label": "Kubernetes",
                "items": [
                    {"posting_number": 1, "insight_id": "insight-1"},
                    {"posting_number": 99, "insight_id": "insight-1"},
                ],
            }
        ]
    }
    client = _mock_client(raw_output)

    patterns = find_gap_patterns(results, client)

    assert patterns == []


def test_drops_group_with_empty_label():
    results = [
        _result("Posting A", [_FakeInsight(id="insight-1", text="No Kubernetes", kind=InsightKind.GAP)]),
        _result("Posting B", [_FakeInsight(id="insight-1", text="No K8s", kind=InsightKind.GAP)]),
    ]
    raw_output = {
        "groups": [
            {
                "label": "   ",
                "items": [
                    {"posting_number": 1, "insight_id": "insight-1"},
                    {"posting_number": 2, "insight_id": "insight-1"},
                ],
            }
        ]
    }
    client = _mock_client(raw_output)

    patterns = find_gap_patterns(results, client)

    assert patterns == []
