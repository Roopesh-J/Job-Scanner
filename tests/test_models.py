import pytest
from pydantic import ValidationError

from job_scanner.models import Category, Insight, InsightKind, Posting, Requirement, Responsibility


def test_requirement_accepts_valid_category():
    req = Requirement(id="req-1", text="5+ years Python", category=Category.REQUIRED, source_quote="5+ years of Python")
    assert req.category == Category.REQUIRED


def test_requirement_rejects_invalid_category():
    with pytest.raises(ValidationError):
        Requirement(id="req-1", text="x", category="not-a-real-category", source_quote="x")


def test_posting_all_ids_combines_requirements_and_responsibilities():
    posting = Posting(
        title="Backend Engineer",
        company="Acme",
        location="Remote",
        seniority="Senior",
        responsibilities=[Responsibility(id="resp-1", text="Own the API", source_quote="own our public API")],
        requirements=[Requirement(id="req-1", text="Python", category=Category.REQUIRED, source_quote="Python")],
    )
    assert posting.all_ids() == {"resp-1", "req-1"}


def test_insight_requires_valid_kind():
    with pytest.raises(ValidationError):
        Insight(id="insight-1", text="x", kind="not-a-real-kind", supporting_requirement_ids=["req-1"])


def test_insight_accepts_strength_and_gap_kinds():
    strength = Insight(id="insight-1", text="Strong Python background", kind=InsightKind.STRENGTH, supporting_requirement_ids=["req-1"])
    gap = Insight(id="insight-2", text="No Kubernetes experience", kind=InsightKind.GAP, supporting_requirement_ids=["req-2"])
    assert strength.kind == InsightKind.STRENGTH
    assert gap.kind == InsightKind.GAP
