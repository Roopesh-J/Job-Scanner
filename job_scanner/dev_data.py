"""Sample results for manually exercising the results UI without live API calls.

Only wired up behind the JOBSCAN_DEV_DATA env var (see app.py) — never runs in a real deploy.
"""

from job_scanner.analyzer import AnalysisResult
from job_scanner.extractor import ExtractionResult
from job_scanner.models import (
    Category,
    GapPattern,
    GapPatternItem,
    Insight,
    InsightKind,
    Posting,
    Requirement,
    Responsibility,
    SearchAction,
    SearchResultItem,
    Verdict,
)


def sample_results() -> tuple[list[dict], list[tuple[int, str]], list[GapPattern]]:
    posting_1 = Posting(
        title="Senior Backend Engineer",
        company="Acme Corp",
        location="Remote (US)",
        seniority="Senior",
        salary="$150,000 - $190,000",
        responsibilities=[
            Responsibility(
                id="resp-1", text="Own the public API",
                source_quote="end-to-end ownership of our public API",
            ),
            Responsibility(
                id="resp-2", text="Lead infra migrations",
                source_quote="lead our migration to Kubernetes",
            ),
            Responsibility(
                id="resp-3", text="Mentor junior engineers",
                source_quote="mentor two junior engineers",
            ),
            Responsibility(
                id="resp-4", text="Drive on-call and reliability practices",
                source_quote="drive our on-call rotation and reliability practices",
            ),
        ],
        requirements=[
            Requirement(
                id="req-1", text="5+ years backend", category=Category.REQUIRED,
                source_quote="5+ years of backend engineering experience",
            ),
            Requirement(
                id="req-2", text="Kubernetes experience", category=Category.REQUIRED,
                source_quote="production Kubernetes experience",
            ),
            Requirement(
                id="req-3", text="Distributed systems fundamentals", category=Category.REQUIRED,
                source_quote="strong distributed systems fundamentals",
            ),
            Requirement(
                id="req-4", text="Terraform", category=Category.PREFERRED,
                source_quote="Terraform experience is a bonus",
            ),
            Requirement(
                id="req-5", text="Rust", category=Category.PREFERRED,
                source_quote="familiarity with Rust is a plus",
            ),
            Requirement(
                id="req-6", text="Startup experience", category=Category.UNCLEAR,
                source_quote="startup experience is a plus but not required",
            ),
        ],
    )
    posting_text_1 = (
        "Acme Corp is looking for a senior backend engineer to take end-to-end ownership of our "
        "public API. The role requires 5+ years of backend engineering experience, production "
        "Kubernetes experience, and strong distributed systems fundamentals. You'll lead our "
        "migration to Kubernetes, mentor two junior engineers, and drive our on-call rotation and "
        "reliability practices. Terraform experience is a bonus, familiarity with Rust is a plus, "
        "and startup experience is a plus but not required."
    )
    analysis_1 = AnalysisResult(
        summary="Strong match, especially on the infra side.",
        verdict=Verdict.STRONG_MATCH,
        insights=[
            Insight(
                id="insight-1", text="7 years of backend engineering, including 3 at high-growth startups.",
                kind=InsightKind.STRENGTH, supporting_ids=["req-1", "req-6"],
            ),
            Insight(
                id="insight-2", text="Led a Kubernetes migration end-to-end at a previous company.",
                kind=InsightKind.STRENGTH, supporting_ids=["req-2", "resp-2"],
            ),
            Insight(
                id="insight-3", text="Deep distributed systems background from designing a multi-region payments pipeline.",
                kind=InsightKind.STRENGTH, supporting_ids=["req-3"],
            ),
            Insight(
                id="insight-4", text="Mentored two junior engineers in a prior role.",
                kind=InsightKind.STRENGTH, supporting_ids=["resp-3"],
            ),
            Insight(
                id="insight-5", text="No listed experience with Rust.",
                kind=InsightKind.GAP, supporting_ids=["req-5"],
            ),
            Insight(
                id="insight-6", text="No mention of Terraform.",
                kind=InsightKind.GAP, supporting_ids=["req-4"],
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
        location="Hybrid (Austin, TX)",
        seniority="Mid-level",
        salary=None,
        responsibilities=[
            Responsibility(
                id="resp-1", text="Own CI/CD pipelines",
                source_quote="own our CI/CD pipelines end to end",
            ),
            Responsibility(
                id="resp-2", text="Reduce cloud spend",
                source_quote="identify and execute on cloud cost optimizations",
            ),
            Responsibility(
                id="resp-3", text="Build internal developer tooling",
                source_quote="build self-service tooling for other engineering teams",
            ),
        ],
        requirements=[
            Requirement(
                id="req-1", text="Terraform", category=Category.REQUIRED,
                source_quote="hands-on Terraform experience",
            ),
            Requirement(
                id="req-2", text="Multi-region failover", category=Category.REQUIRED,
                source_quote="active-active deployments across multiple regions",
            ),
            Requirement(
                id="req-3", text="Go or Python scripting", category=Category.PREFERRED,
                source_quote="comfortable scripting in Go or Python",
            ),
            Requirement(
                id="req-4", text="Observability tooling (Datadog)", category=Category.PREFERRED,
                source_quote="experience with Datadog or a similar observability stack",
            ),
            Requirement(
                id="req-5", text="On-call participation", category=Category.UNCLEAR,
                source_quote="Willingness to participate in an on-call rotation",
            ),
        ],
    )
    posting_text_2 = (
        "Globex is hiring a Platform Engineer to own our CI/CD pipelines end to end and identify "
        "and execute on cloud cost optimizations. You'll also build self-service tooling for other "
        "engineering teams. We're looking for hands-on Terraform experience and active-active "
        "deployments across multiple regions. You should be comfortable scripting in Go or Python, "
        "and experience with Datadog or a similar observability stack is a plus. Willingness to "
        "participate in an on-call rotation is expected."
    )
    analysis_2 = AnalysisResult(
        summary="A stretch — the infra depth is there but a couple of specifics are missing.",
        verdict=Verdict.STRETCH,
        insights=[
            Insight(
                id="insight-1", text="Owns CI/CD pipelines today, including build and deploy automation.",
                kind=InsightKind.STRENGTH, supporting_ids=["resp-1"],
            ),
            Insight(
                id="insight-2", text="Comfortable scripting in Python for internal tooling.",
                kind=InsightKind.STRENGTH, supporting_ids=["req-3"],
            ),
            Insight(
                id="insight-3", text="No mention of Terraform.",
                kind=InsightKind.GAP, supporting_ids=["req-1"],
            ),
            Insight(
                id="insight-4", text="No experience with multi-region, active-active deployments.",
                kind=InsightKind.GAP, supporting_ids=["req-2"],
            ),
            Insight(
                id="insight-5", text="No listed experience with Datadog or similar observability tools.",
                kind=InsightKind.GAP, supporting_ids=["req-4"],
            ),
        ],
        dropped_count=1,
        search_actions=[],
    )
    extraction_2 = ExtractionResult(posting=posting_2, dropped_ids=["req-6"])

    posting_3 = Posting(
        title="Data Scientist",
        company="Initech",
        location="New York, NY",
        seniority=None,
        salary="$90/hr",
        responsibilities=[
            Responsibility(
                id="resp-1", text="Build and maintain the churn model",
                source_quote="build and maintain our customer churn model",
            ),
            Responsibility(
                id="resp-2", text="Partner with growth on experiment design",
                source_quote="partner closely with the growth team on experiment design",
            ),
        ],
        requirements=[
            Requirement(
                id="req-1", text="PhD in Statistics", category=Category.REQUIRED,
                source_quote="PhD in Statistics, Applied Math, or a related field",
            ),
            Requirement(
                id="req-2", text="SQL", category=Category.PREFERRED,
                source_quote="Strong SQL skills",
            ),
            Requirement(
                id="req-3", text="A/B testing experience", category=Category.PREFERRED,
                source_quote="experience designing and analyzing A/B tests",
            ),
            Requirement(
                id="req-4", text="Python and pandas", category=Category.UNCLEAR,
                source_quote="Familiarity with Python and pandas is a plus",
            ),
        ],
    )
    posting_text_3 = (
        "Initech is seeking a Data Scientist to build and maintain our customer churn model and "
        "partner closely with the growth team on experiment design. The role requires a PhD in "
        "Statistics, Applied Math, or a related field. Strong SQL skills are required, and "
        "experience designing and analyzing A/B tests is preferred. Familiarity with Python and "
        "pandas is a plus."
    )
    analysis_3 = AnalysisResult(
        summary="Not a fit right now — the core requirement isn't met.",
        verdict=Verdict.WEAK_FIT,
        insights=[
            Insight(
                id="insight-1", text="No PhD in Statistics or related field.",
                kind=InsightKind.GAP, supporting_ids=["req-1"],
            ),
            Insight(
                id="insight-2", text="Strong SQL background from five years of analytics work.",
                kind=InsightKind.STRENGTH, supporting_ids=["req-2"],
            ),
            Insight(
                id="insight-3", text="No experience designing or analyzing A/B tests.",
                kind=InsightKind.GAP, supporting_ids=["req-3"],
            ),
        ],
        dropped_count=0,
        search_actions=[],
    )
    extraction_3 = ExtractionResult(posting=posting_3, dropped_ids=[])

    posting_4 = Posting(
        title="DevOps Engineer",
        company="Initrode",
        location="Remote (US)",
        seniority="Mid-level",
        salary="$130,000 - $160,000",
        responsibilities=[
            Responsibility(
                id="resp-1", text="Own cloud infrastructure",
                source_quote="own our cloud infrastructure end to end",
            ),
            Responsibility(
                id="resp-2", text="Implement disaster recovery",
                source_quote="implement disaster recovery across regions",
            ),
            Responsibility(
                id="resp-3", text="Support security compliance audits",
                source_quote="support quarterly security compliance audits",
            ),
        ],
        requirements=[
            Requirement(
                id="req-1", text="Terraform", category=Category.REQUIRED,
                source_quote="Strong Terraform skills required",
            ),
            Requirement(
                id="req-2", text="Kubernetes", category=Category.REQUIRED,
                source_quote="Kubernetes in production",
            ),
            Requirement(
                id="req-3", text="Multi-region deployments", category=Category.PREFERRED,
                source_quote="Experience with multi-region deployments is a plus",
            ),
            Requirement(
                id="req-4", text="AWS certification", category=Category.UNCLEAR,
                source_quote="AWS certification is nice to have",
            ),
            Requirement(
                id="req-5", text="Security/compliance background", category=Category.PREFERRED,
                source_quote="background supporting SOC 2 or similar compliance audits",
            ),
        ],
    )
    posting_text_4 = (
        "DevOps Engineer needed to own our cloud infrastructure end to end and implement disaster "
        "recovery across regions. You'll also support quarterly security compliance audits. Strong "
        "Terraform skills required, along with Kubernetes in production. Experience with "
        "multi-region deployments is a plus, AWS certification is nice to have, and a background "
        "supporting SOC 2 or similar compliance audits is a plus."
    )
    analysis_4 = AnalysisResult(
        summary="Good infra fit, but the IaC tooling gap shows up again here.",
        verdict=Verdict.STRETCH,
        insights=[
            Insight(
                id="insight-1", text="Led a Kubernetes migration into production.",
                kind=InsightKind.STRENGTH, supporting_ids=["req-2"],
            ),
            Insight(
                id="insight-2", text="No mention of Terraform.",
                kind=InsightKind.GAP, supporting_ids=["req-1"],
            ),
            Insight(
                id="insight-3", text="No experience with multi-region deployments.",
                kind=InsightKind.GAP, supporting_ids=["req-3"],
            ),
            Insight(
                id="insight-4", text="Supported SOC 2 audits in a prior role.",
                kind=InsightKind.STRENGTH, supporting_ids=["req-5"],
            ),
        ],
        dropped_count=0,
        search_actions=[],
    )
    extraction_4 = ExtractionResult(posting=posting_4, dropped_ids=[])

    results = [
        {"posting_text": posting_text_1, "extraction": extraction_1, "analysis": analysis_1},
        {"posting_text": posting_text_2, "extraction": extraction_2, "analysis": analysis_2},
        {"posting_text": posting_text_3, "extraction": extraction_3, "analysis": analysis_3},
        {"posting_text": posting_text_4, "extraction": extraction_4, "analysis": analysis_4},
    ]
    errors = [(5, "Could not fetch URL. Try pasting in the posting text directly instead.")]
    gap_patterns = [
        GapPattern(
            label="Terraform",
            items=[
                GapPatternItem(posting_number=1, insight_id="insight-6"),
                GapPatternItem(posting_number=2, insight_id="insight-3"),
                GapPatternItem(posting_number=4, insight_id="insight-2"),
            ],
        ),
        GapPattern(
            label="Multi-region infrastructure experience",
            items=[
                GapPatternItem(posting_number=2, insight_id="insight-4"),
                GapPatternItem(posting_number=4, insight_id="insight-3"),
            ],
        ),
    ]
    return results, errors, gap_patterns
