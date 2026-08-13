from job_scanner.models import Insight, InsightKind, Posting, SearchAction, SearchResultItem, Verdict
from job_scanner.ui_helpers import (
    build_tab_label,
    fit_counts,
    format_salary,
    format_search_actions,
    highlight_quotes_with_ids,
    ranking_key,
    verdict_label,
)


def _insight(kind: InsightKind, insight_id: str = "insight-1") -> Insight:
    return Insight(id=insight_id, text="Some insight text", kind=kind, supporting_ids=["req-1"])


def test_fit_counts_tallies_strengths_and_gaps_separately():
    insights = [
        _insight(InsightKind.STRENGTH, "insight-1"),
        _insight(InsightKind.GAP, "insight-2"),
    ]
    assert fit_counts(insights) == (1, 1)


def test_ranking_key_orders_strong_match_before_stretch_before_weak_fit():
    insights = [_insight(InsightKind.STRENGTH)]
    strong = ranking_key(Verdict.STRONG_MATCH, insights)
    stretch = ranking_key(Verdict.STRETCH, insights)
    weak = ranking_key(Verdict.WEAK_FIT, insights)
    assert strong < stretch < weak


def test_verdict_label_covers_every_verdict():
    assert verdict_label(Verdict.STRONG_MATCH) == "Strong fit"
    assert verdict_label(Verdict.STRETCH) == "Stretch"
    assert verdict_label(Verdict.WEAK_FIT) == "Weak fit"


def test_highlight_quotes_with_ids_escapes_html_special_characters():
    result = highlight_quotes_with_ids("Tools & <required>", {"req-1": "Tools"})
    assert result == '<mark data-cite-id="req-1">Tools</mark> &amp; &lt;required&gt;'


def test_highlight_quotes_with_ids_keeps_every_id_when_quotes_collide():
    result = highlight_quotes_with_ids("Uses Python daily.", {"req-1": "Python", "req-2": "Python"})
    assert result == 'Uses <mark data-cite-id="req-1 req-2">Python</mark> daily.'


def test_highlight_quotes_with_ids_merges_contained_short_quote_instead_of_nesting():
    text = "We need Kubernetes here. Own the production Kubernetes experience."
    id_lookup = {"resp-1": "Kubernetes", "req-2": "production Kubernetes experience"}
    result = highlight_quotes_with_ids(text, id_lookup)
    assert result == (
        'We need <mark data-cite-id="resp-1">Kubernetes</mark> here. '
        'Own the <mark data-cite-id="req-2 resp-1">production Kubernetes experience</mark>.'
    )


def test_highlight_quotes_with_ids_merges_partially_overlapping_quotes_instead_of_dropping_one():
    text = "the quick brown fox jumps"
    id_lookup = {"a": "quick brown", "b": "brown fox"}
    result = highlight_quotes_with_ids(text, id_lookup)
    assert result == 'the <mark data-cite-id="a b">quick brown fox</mark> jumps'


def test_format_salary_formats_range_and_falls_back_when_unparseable():
    assert format_salary("$45,000 - $135,000") == "$45,000 - $135,000"
    assert format_salary("competitive") == "competitive"


def test_format_salary_recognizes_per_hour_phrasing():
    assert format_salary("$45 per hour") == "$45/hour"


def test_format_salary_does_not_treat_per_inside_a_word_as_a_rate_suffix():
    assert format_salary("$45 the hopper week rotation") == "$45"


def _posting(title: str, company: str) -> Posting:
    return Posting(title=title, company=company, responsibilities=[], requirements=[])


def test_build_tab_label_escapes_markdown_in_bold_title():
    posting = _posting("Backend `Eng`ineer *II*", "Acme")
    label = build_tab_label(posting)
    assert label == r"**Backend \`Eng\`ineer \*II\***`Acme`"


def test_build_tab_label_strips_backticks_from_code_company():
    posting = _posting("Engineer", "Foo`Bar")
    label = build_tab_label(posting)
    assert label == "**Engineer**`Foo'Bar`"


def test_build_tab_label_replaces_newlines_with_spaces():
    posting = _posting("Line One\nLine Two", "Acme")
    label = build_tab_label(posting)
    assert "\n" not in label


def test_format_search_actions_escapes_markdown_in_query_and_titles():
    actions = [
        SearchAction(
            query="What is *args?",
            results=[SearchResultItem(title="Guide to *args and **kwargs", url="https://example.com")],
        )
    ]
    lines = format_search_actions(actions)
    assert lines == ["Searched “What is \\*args?” — found: Guide to \\*args and \\*\\*kwargs"]
