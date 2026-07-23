from unittest.mock import MagicMock

from job_scanner.extractor import extract_posting
from job_scanner.models import Category

POSTING_TEXT = "We need someone with 5+ years of Python and ownership of our public API."

RAW_TOOL_OUTPUT = {
    "title": "Backend Engineer",
    "company": "Acme",
    "location": "Remote",
    "seniority": "Senior",
    "responsibilities": [
        {"text": "Own the public API", "source_quote": "ownership of our public API"},
    ],
    "requirements": [
        {"text": "5+ years Python", "category": "required", "source_quote": "5+ years of Python"},
    ],
}


def _mock_client(raw_output: dict) -> MagicMock:
    client = MagicMock()
    client.call_tool.return_value = raw_output
    return client


def test_extract_posting_builds_posting_with_assigned_ids():
    client = _mock_client(RAW_TOOL_OUTPUT)

    result = extract_posting(POSTING_TEXT, client)

    assert result.posting.title == "Backend Engineer"
    assert result.posting.requirements[0].id == "req-1"
    assert result.posting.requirements[0].category == Category.REQUIRED
    assert result.posting.responsibilities[0].id == "resp-1"
    assert result.dropped_ids == []


def test_extract_posting_drops_ungrounded_item_but_keeps_the_rest():
    two_requirements_one_bad = {
        **RAW_TOOL_OUTPUT,
        "requirements": [
            {"text": "5+ years Python", "category": "required", "source_quote": "5+ years of Python"},
            {"text": "Fabricated requirement", "category": "required", "source_quote": "this text is not in the posting"},
        ],
    }
    client = _mock_client(two_requirements_one_bad)

    result = extract_posting(POSTING_TEXT, client)

    assert len(result.posting.requirements) == 1
    assert result.posting.requirements[0].text == "5+ years Python"
    assert result.dropped_ids == ["req-2"]
