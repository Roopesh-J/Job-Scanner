from job_scanner.models import Category, Posting, Requirement
from job_scanner.validation import find_invalid_references, find_ungrounded_quotes


def _posting(source_quote: str) -> Posting:
    return Posting(
        title="Backend Engineer",
        company="Acme",
        location="Remote",
        seniority="Senior",
        responsibilities=[],
        requirements=[Requirement(id="req-1", text="Python", category=Category.REQUIRED, source_quote=source_quote)],
    )


def test_find_ungrounded_quotes_returns_empty_when_quote_is_verbatim():
    posting_text = "We need someone with 5+ years of Python experience."
    posting = _posting(source_quote="5+ years of Python")
    assert find_ungrounded_quotes(posting, posting_text) == []


def test_find_ungrounded_quotes_flags_paraphrased_quote():
    posting_text = "We need someone with 5+ years of Python experience."
    posting = _posting(source_quote="five years of Python")
    assert find_ungrounded_quotes(posting, posting_text) == ["req-1"]


def test_find_invalid_references_returns_only_unknown_ids():
    valid_ids = {"req-1", "resp-1"}
    result = find_invalid_references(["req-1", "req-99"], valid_ids)
    assert result == ["req-99"]


def test_find_invalid_references_returns_empty_when_all_known():
    valid_ids = {"req-1", "resp-1"}
    assert find_invalid_references(["req-1", "resp-1"], valid_ids) == []
