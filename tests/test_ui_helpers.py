from job_scanner.models import Insight, InsightKind, Verdict
from job_scanner.ui_helpers import fit_counts, format_salary, highlight_quotes, ranking_key, verdict_label


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


def test_highlight_quotes_escapes_html_special_characters():
    result = highlight_quotes("Tools & <required>", ["Tools"])
    assert result == "<mark>Tools</mark> &amp; &lt;required&gt;"


def test_format_salary_formats_range_and_falls_back_when_unparseable():
    assert format_salary("$45,000 - $135,000") == "$45,000 - $135,000"
    assert format_salary("competitive") == "competitive"
