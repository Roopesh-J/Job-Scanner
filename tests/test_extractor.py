from unittest.mock import MagicMock

from job_scanner.extractor import extract_posting, is_url
from job_scanner.models import Category

POSTING_TEXT = (
    "We need someone with 5+ years of Python and ownership of our public API. Salary: $150,000 - $180,000."
)

RAW_TOOL_OUTPUT = {
    "title": "Backend Engineer",
    "company": "Acme",
    "location": "Remote",
    "seniority": "Senior",
    "salary": "$150,000 - $180,000",
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
    assert result.posting.salary == "$150,000 - $180,000"
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


def test_extract_posting_drops_fabricated_salary():
    raw_with_bad_salary = {**RAW_TOOL_OUTPUT, "salary": "$999,000 - $1,200,000"}
    client = _mock_client(raw_with_bad_salary)

    result = extract_posting(POSTING_TEXT, client)

    assert result.posting.salary is None


def test_extract_posting_sets_salary_to_none_when_not_mentioned():
    raw_without_salary = {**RAW_TOOL_OUTPUT, "salary": ""}
    client = _mock_client(raw_without_salary)

    result = extract_posting(POSTING_TEXT, client)

    assert result.posting.salary is None


def test_is_url_distinguishes_urls_from_pasted_text():
    assert is_url("https://example.com/job") is True
    assert is_url("http://example.com/job") is True
    assert is_url("We are looking for a Senior Engineer...") is False
