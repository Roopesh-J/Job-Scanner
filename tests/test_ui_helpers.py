from job_scanner.models import (
    Category,
    Insight,
    InsightKind,
    Posting,
    Requirement,
    Responsibility,
    SearchAction,
    SearchResultItem,
    Verdict,
)
from job_scanner.ui_helpers import (
    build_id_lookup,
    build_meta_line,
    cite_targets,
    citation_hover_css,
    fit_counts,
    format_salary,
    format_search_actions,
    highlight_quotes,
    highlight_quotes_with_ids,
    ranking_key,
    verdict_label,
)


def _posting(salary: str | None = None) -> Posting:
    return Posting(
        title="Backend Engineer",
        company="Acme",
        location="Remote",
        seniority="Senior",
        salary=salary,
        responsibilities=[Responsibility(id="resp-1", text="Own the API", source_quote="own the public API")],
        requirements=[Requirement(id="req-1", text="Python", category=Category.REQUIRED, source_quote="5+ years of Python")],
    )


def _insight(kind: InsightKind, insight_id: str = "insight-1") -> Insight:
    return Insight(id=insight_id, text="Some insight text", kind=kind, supporting_ids=["req-1"])


def test_fit_counts_tallies_strengths_and_gaps_separately():
    insights = [
        _insight(InsightKind.STRENGTH, "insight-1"),
        _insight(InsightKind.STRENGTH, "insight-2"),
        _insight(InsightKind.GAP, "insight-3"),
    ]
    assert fit_counts(insights) == (2, 1)


def test_fit_counts_handles_empty_list():
    assert fit_counts([]) == (0, 0)


def test_ranking_key_orders_strong_match_before_stretch_before_weak_fit():
    insights = [_insight(InsightKind.STRENGTH)]
    strong = ranking_key(Verdict.STRONG_MATCH, insights)
    stretch = ranking_key(Verdict.STRETCH, insights)
    weak = ranking_key(Verdict.WEAK_FIT, insights)
    assert strong < stretch < weak


def test_ranking_key_breaks_ties_within_same_verdict_by_strength_minus_gap():
    better = ranking_key(Verdict.STRETCH, [_insight(InsightKind.STRENGTH, "a"), _insight(InsightKind.STRENGTH, "b")])
    worse = ranking_key(Verdict.STRETCH, [_insight(InsightKind.GAP, "a"), _insight(InsightKind.GAP, "b")])
    assert better < worse


def test_verdict_label_covers_every_verdict():
    assert verdict_label(Verdict.STRONG_MATCH) == "Strong match"
    assert verdict_label(Verdict.STRETCH) == "Stretch"
    assert verdict_label(Verdict.WEAK_FIT) == "Weak fit"


def test_highlight_quotes_wraps_matching_substring_in_mark():
    result = highlight_quotes("Own the public API end to end.", ["the public API"])
    assert result == "Own <mark>the public API</mark> end to end."


def test_highlight_quotes_escapes_html_special_characters_outside_quotes():
    result = highlight_quotes("Tools & frameworks <required>", [])
    assert result == "Tools &amp; frameworks &lt;required&gt;"


def test_highlight_quotes_skips_empty_and_duplicate_quotes():
    result = highlight_quotes("Python and Python again", ["Python", "", "Python"])
    assert result == "<mark>Python</mark> and <mark>Python</mark> again"


def test_build_meta_line_joins_non_empty_parts_and_escapes_html():
    posting = _posting(salary="$100,000")
    posting = posting.model_copy(update={"location": "Remote <negotiable>"})
    line = build_meta_line(posting)
    assert line == "<span>Remote &lt;negotiable&gt;</span><span>$100,000</span><span>Senior</span>"


def test_build_meta_line_shows_fallback_text_for_missing_salary():
    line = build_meta_line(_posting(salary=None))
    assert line == "<span>Remote</span><span>Salary not listed</span><span>Senior</span>"


def test_build_meta_line_shows_fallback_text_for_missing_location_and_seniority():
    posting = Posting(
        title="Backend Engineer",
        company="Acme",
        location=None,
        seniority=None,
        salary="$100k",
        responsibilities=[],
        requirements=[],
    )
    assert build_meta_line(posting) == (
        "<span>Location not listed</span><span>$100,000</span><span>Level not listed</span>"
    )


def test_format_salary_formats_single_figure():
    assert format_salary("$80000") == "$80,000"


def test_format_salary_formats_range_with_dollar_signs():
    assert format_salary("$45,000 - $135,000") == "$45,000 - $135,000"


def test_format_salary_formats_range_joined_by_and():
    assert format_salary("$65,000 and $80,000") == "$65,000 - $80,000"


def test_format_salary_expands_k_shorthand():
    assert format_salary("120k - 150k") == "$120,000 - $150,000"


def test_format_salary_preserves_rate_suffix():
    assert format_salary("$45/hr") == "$45/hr"


def test_format_salary_falls_back_to_raw_when_unparseable():
    assert format_salary("competitive") == "competitive"


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
    assert lines == ["Searched “example query” — found: First Result, Second Result"]


def test_format_search_actions_handles_no_results():
    actions = [SearchAction(query="some obscure term", results=[])]
    lines = format_search_actions(actions)
    assert lines == ["Searched “some obscure term” — found: no results"]


def test_build_id_lookup_combines_responsibilities_and_requirements():
    lookup = build_id_lookup(_posting())
    assert lookup == {"resp-1": "own the public API", "req-1": "5+ years of Python"}


def test_highlight_quotes_with_ids_tags_each_mark_with_its_cite_id():
    result = highlight_quotes_with_ids("Own the public API end to end.", {"resp-1": "the public API"})
    assert result == 'Own <mark data-cite-id="resp-1">the public API</mark> end to end.'


def test_highlight_quotes_with_ids_skips_empty_quotes():
    result = highlight_quotes_with_ids("No markup here.", {"req-1": ""})
    assert result == "No markup here."


def test_cite_targets_joins_only_ids_present_in_lookup():
    lookup = {"req-1": "5+ years of Python", "resp-1": "own the public API"}
    assert cite_targets(["req-1", "missing-id", "resp-1"], lookup) == "req-1 resp-1"


def test_cite_targets_returns_empty_string_when_no_ids_match():
    assert cite_targets(["missing-id"], {"req-1": "5+ years of Python"}) == ""


def test_citation_hover_css_returns_empty_string_for_no_ids():
    assert citation_hover_css(set()) == ""


def test_citation_hover_css_emits_a_rule_referencing_each_cite_id():
    css = citation_hover_css({"req-1"})
    assert '[data-cite-target~="req-1"]' in css
    assert 'mark[data-cite-id="req-1"]' in css
