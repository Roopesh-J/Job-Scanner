"""Sample results for manually exercising the results UI without live API calls.

Only wired up behind the JOBSCAN_DEV_DATA env var (see app.py) — never runs in a real deploy.
"""

from job_scanner.analyzer import AnalysisResult
from job_scanner.extractor import ExtractionResult
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


def sample_results() -> tuple[list[dict], list[tuple[int, str]]]:
    posting_1 = Posting(
        title="Senior Backend Engineer",
        company="Acme Corp",
        location="Remote (US)",
        seniority="Senior",
        salary="$150,000 - $190,000",
        responsibilities=[
            Responsibility(id="resp-1", text="Own the public API", source_quote="ownership of our public API"),
            Responsibility(id="resp-2", text="Lead infra migrations", source_quote="lead our migration to Kubernetes"),
        ],
        requirements=[
            Requirement(
                id="req-1", text="5+ years backend", category=Category.REQUIRED,
                source_quote="5+ years of backend engineering",
            ),
            Requirement(
                id="req-2", text="Kubernetes experience", category=Category.REQUIRED,
                source_quote="production Kubernetes experience",
            ),
            Requirement(
                id="req-3", text="Rust", category=Category.PREFERRED,
                source_quote="familiarity with Rust is a plus",
            ),
        ],
    )
    posting_text_1 = (
        "We're looking for a senior backend engineer with 5+ years of backend engineering "
        "experience and production Kubernetes experience. You'll take ownership of our public "
        "API and lead our migration to Kubernetes. Familiarity with Rust is a plus."
    )
    analysis_1 = AnalysisResult(
        summary="Strong match, especially on the infra side.",
        verdict=Verdict.STRONG_MATCH,
        insights=[
            Insight(
                id="insight-1", text="7 years of backend engineering.",
                kind=InsightKind.STRENGTH, supporting_ids=["req-1"],
            ),
            Insight(
                id="insight-2", text="Led a Kubernetes migration.",
                kind=InsightKind.STRENGTH, supporting_ids=["req-2", "resp-2"],
            ),
            Insight(
                id="insight-3", text="No listed experience with Rust.",
                kind=InsightKind.GAP, supporting_ids=["req-3"],
            ),
        ],
        dropped_count=0,
        search_actions=[
            SearchAction(
                query="Rust programming language",
                results=[SearchResultItem(title="The Rust Programming Language", url="https://www.rust-lang.org/")],
            ),
        ],
    )
    extraction_1 = ExtractionResult(posting=posting_1, dropped_ids=[])

    posting_2 = Posting(
        title="Platform Engineer",
        company="Globex",
        location=None,
        seniority="Mid-level",
        salary=None,
        responsibilities=[
            Responsibility(id="resp-1", text="Maintain CI/CD", source_quote="own our CI/CD pipelines"),
        ],
        requirements=[
            Requirement(
                id="req-1", text="Terraform", category=Category.REQUIRED,
                source_quote="hands-on Terraform experience",
            ),
            Requirement(
                id="req-2", text="Multi-region failover", category=Category.REQUIRED,
                source_quote="active-active deployments across regions",
            ),
        ],
    )
    posting_text_2 = (
        "Platform Engineer needed to own our CI/CD pipelines. Must have hands-on Terraform "
        "experience and active-active deployments across regions."
    )
    analysis_2 = AnalysisResult(
        summary="A stretch — the infra depth is there but a couple of specifics are missing.",
        verdict=Verdict.STRETCH,
        insights=[
            Insight(
                id="insight-1", text="Owns CI/CD pipelines today.",
                kind=InsightKind.STRENGTH, supporting_ids=["resp-1"],
            ),
            Insight(
                id="insight-2", text="No mention of Terraform.",
                kind=InsightKind.GAP, supporting_ids=["req-1"],
            ),
            Insight(
                id="insight-3", text="No experience with multi-region failover.",
                kind=InsightKind.GAP, supporting_ids=["req-2"],
            ),
        ],
        dropped_count=1,
        search_actions=[],
    )
    extraction_2 = ExtractionResult(posting=posting_2, dropped_ids=["req-3"])

    posting_3 = Posting(
        title="Data Scientist",
        company="Initech",
        location="New York, NY",
        seniority=None,
        salary="$90/hr",
        responsibilities=[],
        requirements=[
            Requirement(
                id="req-1", text="PhD in Statistics", category=Category.REQUIRED,
                source_quote="PhD in Statistics or related field",
            ),
        ],
    )
    posting_text_3 = "Seeking a Data Scientist. Requires a PhD in Statistics or related field."
    analysis_3 = AnalysisResult(
        summary="Not a fit right now — the core requirement isn't met.",
        verdict=Verdict.WEAK_FIT,
        insights=[
            Insight(id="insight-1", text="No PhD in Statistics.", kind=InsightKind.GAP, supporting_ids=["req-1"]),
        ],
        dropped_count=0,
        search_actions=[],
    )
    extraction_3 = ExtractionResult(posting=posting_3, dropped_ids=[])

    results = [
        {"posting_text": posting_text_1, "extraction": extraction_1, "analysis": analysis_1},
        {"posting_text": posting_text_2, "extraction": extraction_2, "analysis": analysis_2},
        {"posting_text": posting_text_3, "extraction": extraction_3, "analysis": analysis_3},
    ]
    errors = [(4, "Could not fetch URL. Try pasting in the posting text directly instead.")]
    return results, errors
