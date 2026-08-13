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


def test_extract_posting_drops_malformed_items_but_keeps_the_rest():
    malformed_output = {
        **RAW_TOOL_OUTPUT,
        "responsibilities": [
            {"text": "Own the public API", "source_quote": "ownership of our public API"},
            {"text": "Missing quote field"},
        ],
        "requirements": [
            {"text": "5+ years Python", "category": "required", "source_quote": "5+ years of Python"},
            {"text": "Bad category", "category": "not-a-real-category", "source_quote": "5+ years of Python"},
        ],
    }
    client = _mock_client(malformed_output)

    result = extract_posting(POSTING_TEXT, client)

    assert len(result.posting.responsibilities) == 1
    assert result.posting.responsibilities[0].id == "resp-1"
    assert len(result.posting.requirements) == 1
    assert result.posting.requirements[0].id == "req-1"


def test_extract_posting_drops_fabricated_salary():
    raw_with_bad_salary = {**RAW_TOOL_OUTPUT, "salary": "$999,000 - $1,200,000"}
    client = _mock_client(raw_with_bad_salary)

    result = extract_posting(POSTING_TEXT, client)

    assert result.posting.salary is None


def test_extract_posting_does_not_ground_salary_from_unrelated_digits_elsewhere_in_text():
    # "$1, 5, 0, 000" here are unrelated numbers in an unrelated sentence — a naive
    # strip-all-whitespace-and-commas-then-substring-check would wrongly treat this as grounds
    # for a fabricated "$150,000" salary just because the digits happen to concatenate.
    posting_text_with_unrelated_digits = (
        "We need someone with 5+ years of Python and ownership of our public API. "
        "Team budget lines: $1, 5, 0, 000 dollars across three departments this year."
    )
    raw_with_fabricated_salary = {**RAW_TOOL_OUTPUT, "salary": "$150,000"}
    client = _mock_client(raw_with_fabricated_salary)

    result = extract_posting(posting_text_with_unrelated_digits, client)

    assert result.posting.salary is None


def test_extract_posting_grounds_salary_despite_dash_spacing_difference():
    posting_text_spaced_dash = (
        "We need someone with 5+ years of Python and ownership of our public API. "
        "Compensation: $120,000 - $150,000 per year."
    )
    raw_with_tight_dash_salary = {**RAW_TOOL_OUTPUT, "salary": "$120,000-$150,000"}
    client = _mock_client(raw_with_tight_dash_salary)

    result = extract_posting(posting_text_spaced_dash, client)

    assert result.posting.salary == "$120,000-$150,000"


def test_extract_posting_grounds_salary_despite_en_dash_in_posting_text():
    posting_text_en_dash = (
        "We need someone with 5+ years of Python and ownership of our public API. "
        "Compensation: $120,000–$150,000 per year."
    )
    raw_with_ascii_dash_salary = {**RAW_TOOL_OUTPUT, "salary": "$120,000-$150,000"}
    client = _mock_client(raw_with_ascii_dash_salary)

    result = extract_posting(posting_text_en_dash, client)

    assert result.posting.salary == "$120,000-$150,000"


def test_extract_posting_drops_requirement_with_non_string_category():
    raw_with_bad_category = {
        **RAW_TOOL_OUTPUT,
        "requirements": [
            {"text": "5+ years Python", "category": "required", "source_quote": "5+ years of Python"},
            {"text": "Bad category type", "category": ["required"], "source_quote": "5+ years of Python"},
        ],
    }
    client = _mock_client(raw_with_bad_category)

    result = extract_posting(POSTING_TEXT, client)

    assert len(result.posting.requirements) == 1
    assert result.posting.requirements[0].text == "5+ years Python"


def test_extract_posting_treats_non_string_salary_as_not_mentioned():
    raw_with_non_string_salary = {**RAW_TOOL_OUTPUT, "salary": 50000}
    client = _mock_client(raw_with_non_string_salary)

    result = extract_posting(POSTING_TEXT, client)

    assert result.posting.salary is None


def test_extract_posting_grounds_salary_despite_comma_and_spacing_differences():
    posting_text_no_commas = (
        "We need someone with 5+ years of Python and ownership of our public API. Salary: $150000-$180000."
    )
    client = _mock_client(RAW_TOOL_OUTPUT)  # salary is "$150,000 - $180,000"

    result = extract_posting(posting_text_no_commas, client)

    assert result.posting.salary == "$150,000 - $180,000"


def test_extract_posting_sets_salary_to_none_when_not_mentioned():
    raw_without_salary = {**RAW_TOOL_OUTPUT, "salary": ""}
    client = _mock_client(raw_without_salary)

    result = extract_posting(POSTING_TEXT, client)

    assert result.posting.salary is None


def test_extract_posting_trims_a_full_sentence_salary_down_to_the_figures():
    posting_text_with_sentence_salary = (
        "We need someone with 5+ years of Python and ownership of our public API. "
        "The annual salary for this position is between $65,000 and $80,000 USD "
        "depending on experience."
    )
    raw_with_sentence_salary = {
        **RAW_TOOL_OUTPUT,
        "salary": "The annual salary for this position is between $65,000 and $80,000 USD depending on experience.",
    }
    client = _mock_client(raw_with_sentence_salary)

    result = extract_posting(posting_text_with_sentence_salary, client)

    assert result.posting.salary == "$65,000 and $80,000"


def test_extract_posting_treats_unknown_placeholder_location_as_none():
    raw_with_placeholder = {**RAW_TOOL_OUTPUT, "location": "<UNKNOWN>"}
    client = _mock_client(raw_with_placeholder)

    result = extract_posting(POSTING_TEXT, client)

    assert result.posting.location is None


def test_extract_posting_treats_empty_seniority_as_none():
    raw_without_seniority = {**RAW_TOOL_OUTPUT, "seniority": ""}
    client = _mock_client(raw_without_seniority)

    result = extract_posting(POSTING_TEXT, client)

    assert result.posting.seniority is None


def test_extract_posting_keeps_real_location_and_seniority():
    client = _mock_client(RAW_TOOL_OUTPUT)

    result = extract_posting(POSTING_TEXT, client)

    assert result.posting.location == "Remote"
    assert result.posting.seniority == "Senior"


def test_is_url_distinguishes_urls_from_pasted_text():
    assert is_url("https://example.com/job") is True
    assert is_url("http://example.com/job") is True
    assert is_url("We are looking for a Senior Engineer...") is False
