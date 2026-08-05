from job_scanner.models import Category, Posting, Requirement, Responsibility, SearchAction, SearchResultItem
from job_scanner.ui_helpers import build_id_lookup, format_search_actions, format_sources


def _posting() -> Posting:
    return Posting(
        title="Backend Engineer",
        company="Acme",
        location="Remote",
        seniority="Senior",
        responsibilities=[Responsibility(id="resp-1", text="Own the API", source_quote="own the public API")],
        requirements=[Requirement(id="req-1", text="Python", category=Category.REQUIRED, source_quote="5+ years of Python")],
    )


def test_build_id_lookup_covers_requirements_and_responsibilities():
    lookup = build_id_lookup(_posting())
    assert lookup == {"req-1": "5+ years of Python", "resp-1": "own the public API"}


def test_format_sources_joins_quoted_matches_and_skips_unknown_ids():
    lookup = {"req-1": "5+ years of Python"}
    result = format_sources(["req-1", "req-99"], lookup)
    assert result == "“5+ years of Python”"


def test_format_sources_returns_empty_string_for_no_matches():
    assert format_sources(["req-99"], {}) == ""


def test_format_search_actions_lists_query_and_result_titles():
    actions = [
        SearchAction(
            query="example query",
            results=[
                SearchResultItem(title="First Result", url="https://example.com/first"),
                SearchResultItem(title="Second Result", url="https://example.com/second"),
            ],
        )
    ]
    lines = format_search_actions(actions)
    assert lines == ['Searched “example query” — found: First Result, Second Result']


def test_format_search_actions_handles_no_results():
    actions = [SearchAction(query="some obscure term", results=[])]
    lines = format_search_actions(actions)
    assert lines == ['Searched “some obscure term” — found: no results']
