"""Sample results shown to any visitor via the "See a sample analysis" button on the input
page — a clean, error-free preview of what a real batch run looks like, so someone can see the
depth of the tool before pasting their own background and postings.
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
    posting_anchorpoint = Posting(
        title="Staff Software Engineer",
        company="Anchorpoint",
        location="Remote (US)",
        seniority="Staff",
        salary="$190,000 - $230,000",
        responsibilities=[
            Responsibility(
                id="resp-1", text="Set technical direction for the payments team",
                source_quote="set technical direction for the payments team",
            ),
            Responsibility(
                id="resp-2", text="Review architecture proposals across the org",
                source_quote="review architecture proposals across the engineering org",
            ),
        ],
        requirements=[
            Requirement(
                id="req-1", text="8+ years of software engineering experience", category=Category.REQUIRED,
                source_quote="8+ years of software engineering experience",
            ),
            Requirement(
                id="req-2", text="Track record of setting technical direction for a team", category=Category.REQUIRED,
                source_quote="track record of setting technical direction for a team",
            ),
            Requirement(
                id="req-3", text="Kafka-based event streaming experience", category=Category.PREFERRED,
                source_quote="Experience with Kafka-based event streaming is a plus",
            ),
            Requirement(
                id="req-4", text="Experience with high-throughput payment systems", category=Category.PREFERRED,
                source_quote="experience with high-throughput payment systems is a plus",
            ),
        ],
    )
    posting_text_anchorpoint = (
        "Anchorpoint is hiring a Staff Software Engineer to set technical direction for the payments team. "
        "You'll review architecture proposals across the engineering org. We're looking for 8+ years of "
        "software engineering experience and a track record of setting technical direction for a team. "
        "Experience with Kafka-based event streaming is a plus, and experience with high-throughput "
        "payment systems is a plus."
    )
    analysis_anchorpoint = AnalysisResult(
        summary="Strong match — deep technical leadership and directly relevant payments experience.",
        verdict=Verdict.STRONG_MATCH,
        insights=[
            Insight(
                id="insight-1", text="9 years of software engineering, the last 3 as a de facto technical lead.",
                kind=InsightKind.STRENGTH, supporting_ids=["req-1"],
            ),
            Insight(
                id="insight-2",
                text="Set the technical direction for a checkout-services migration used company-wide.",
                kind=InsightKind.STRENGTH, supporting_ids=["req-2", "resp-1"],
            ),
            Insight(
                id="insight-3",
                text="Built a high-throughput payment reconciliation system processing 2M+ transactions/day.",
                kind=InsightKind.STRENGTH, supporting_ids=["req-4"],
            ),
            Insight(
                id="insight-4", text="No listed experience with Kafka-based event streaming.",
                kind=InsightKind.GAP, supporting_ids=["req-3"],
            ),
        ],
        dropped_count=0,
        search_actions=[],
    )
    extraction_anchorpoint = ExtractionResult(posting=posting_anchorpoint, dropped_ids=[])

    posting_meridian = Posting(
        title="Senior Backend Engineer",
        company="Meridian Health",
        location="Remote (US)",
        seniority="Senior",
        salary="$155,000 - $190,000",
        responsibilities=[
            Responsibility(
                id="resp-1", text="Own the claims-processing API",
                source_quote="own our claims-processing API end to end",
            ),
            Responsibility(
                id="resp-2", text="Lead the migration to event-driven architecture",
                source_quote="lead our migration to an event-driven architecture",
            ),
            Responsibility(
                id="resp-3", text="Mentor two engineers on the team",
                source_quote="mentor two engineers on the team",
            ),
        ],
        requirements=[
            Requirement(
                id="req-1", text="6+ years of backend engineering experience", category=Category.REQUIRED,
                source_quote="6+ years of backend engineering experience",
            ),
            Requirement(
                id="req-2", text="Production experience with distributed systems", category=Category.REQUIRED,
                source_quote="hands-on experience building distributed systems in production",
            ),
            Requirement(
                id="req-3", text="Experience deploying services on Kubernetes", category=Category.REQUIRED,
                source_quote="experience deploying services on Kubernetes",
            ),
            Requirement(
                id="req-4", text="Experience with HIPAA-compliant systems", category=Category.PREFERRED,
                source_quote="Experience with HIPAA-compliant systems is a plus",
            ),
        ],
    )
    posting_text_meridian = (
        "Meridian Health is hiring a Senior Backend Engineer to own our claims-processing API end to end. "
        "You'll lead our migration to an event-driven architecture and mentor two engineers on the team. "
        "We're looking for 6+ years of backend engineering experience, hands-on experience building "
        "distributed systems in production, and experience deploying services on Kubernetes. Experience "
        "with HIPAA-compliant systems is a plus."
    )
    analysis_meridian = AnalysisResult(
        summary="Strong match — deep backend and distributed systems experience, with the migration and "
        "mentorship work directly relevant.",
        verdict=Verdict.STRONG_MATCH,
        insights=[
            Insight(
                id="insight-1", text="8 years of backend engineering, most recently leading a services team.",
                kind=InsightKind.STRENGTH, supporting_ids=["req-1"],
            ),
            Insight(
                id="insight-2", text="Designed and shipped an event-driven order pipeline at a previous company.",
                kind=InsightKind.STRENGTH, supporting_ids=["req-2", "resp-2"],
            ),
            Insight(
                id="insight-3", text="Mentored three junior engineers over the past two years.",
                kind=InsightKind.STRENGTH, supporting_ids=["resp-3"],
            ),
            Insight(
                id="insight-4", text="No listed experience deploying services on Kubernetes.",
                kind=InsightKind.GAP, supporting_ids=["req-3"],
            ),
            Insight(
                id="insight-5", text="No listed experience with HIPAA-compliant systems.",
                kind=InsightKind.GAP, supporting_ids=["req-4"],
            ),
        ],
        dropped_count=0,
        search_actions=[
            SearchAction(
                query="HIPAA compliant backend systems",
                results=[
                    SearchResultItem(
                        title="HIPAA Compliance Basics for Engineers",
                        url="https://www.hhs.gov/hipaa/for-professionals/index.html",
                    ),
                ],
            ),
        ],
    )
    extraction_meridian = ExtractionResult(posting=posting_meridian, dropped_ids=[])

    posting_cascade = Posting(
        title="Platform Engineer",
        company="Cascade Systems",
        location="Austin, TX (Hybrid)",
        seniority="Senior",
        salary="$150,000 - $180,000",
        responsibilities=[
            Responsibility(
                id="resp-1", text="Own the internal deployment platform",
                source_quote="own our internal deployment platform",
            ),
            Responsibility(
                id="resp-2", text="Reduce infrastructure costs across environments",
                source_quote="reduce infrastructure costs across our staging and production environments",
            ),
        ],
        requirements=[
            Requirement(
                id="req-1", text="5+ years of platform or infrastructure engineering experience",
                category=Category.REQUIRED,
                source_quote="5+ years of platform or infrastructure engineering experience",
            ),
            Requirement(
                id="req-2", text="Advanced Kubernetes operations at scale", category=Category.REQUIRED,
                source_quote="advanced Kubernetes operations at scale",
            ),
            Requirement(
                id="req-3", text="Terraform and infrastructure-as-code experience", category=Category.REQUIRED,
                source_quote="hands-on Terraform and infrastructure-as-code experience",
            ),
        ],
    )
    posting_text_cascade = (
        "Cascade Systems is looking for a Platform Engineer to own our internal deployment platform and "
        "reduce infrastructure costs across our staging and production environments. We require 5+ years "
        "of platform or infrastructure engineering experience, advanced Kubernetes operations at scale, "
        "and hands-on Terraform and infrastructure-as-code experience."
    )
    analysis_cascade = AnalysisResult(
        summary="A stretch — solid platform engineering fundamentals, but the Kubernetes and Terraform "
        "depth this role wants aren't demonstrated.",
        verdict=Verdict.STRETCH,
        insights=[
            Insight(
                id="insight-1", text="6 years of platform and infrastructure engineering experience.",
                kind=InsightKind.STRENGTH, supporting_ids=["req-1"],
            ),
            Insight(
                id="insight-2", text="Reduced cloud spend by 18% at a previous role through targeted right-sizing.",
                kind=InsightKind.STRENGTH, supporting_ids=["resp-2"],
            ),
            Insight(
                id="insight-3", text="No mention of advanced Kubernetes operations at scale.",
                kind=InsightKind.GAP, supporting_ids=["req-2"],
            ),
            Insight(
                id="insight-4", text="No hands-on Terraform or infrastructure-as-code experience listed.",
                kind=InsightKind.GAP, supporting_ids=["req-3"],
            ),
        ],
        dropped_count=0,
        search_actions=[],
    )
    extraction_cascade = ExtractionResult(posting=posting_cascade, dropped_ids=[])

    posting_ridgeline = Posting(
        title="DevOps Engineer",
        company="Ridgeline Cloud",
        location="Remote (US)",
        seniority="Mid-Senior",
        salary="$140,000 - $165,000",
        responsibilities=[
            Responsibility(
                id="resp-1", text="Own CI/CD pipelines across three product teams",
                source_quote="own CI/CD pipelines across three product teams",
            ),
            Responsibility(
                id="resp-2", text="Build self-service infrastructure tooling",
                source_quote="build self-service infrastructure tooling for other engineers",
            ),
        ],
        requirements=[
            Requirement(
                id="req-1", text="4+ years of DevOps or SRE experience", category=Category.REQUIRED,
                source_quote="4+ years of DevOps or SRE experience",
            ),
            Requirement(
                id="req-2", text="Experience running production Kubernetes clusters, including capacity "
                "planning and upgrades", category=Category.REQUIRED,
                source_quote="run production Kubernetes clusters and knows their way around capacity "
                "planning and upgrades",
            ),
            Requirement(
                id="req-3", text="Comfortable writing and maintaining Terraform modules", category=Category.REQUIRED,
                source_quote="comfortable writing and maintaining Terraform modules for our infrastructure",
            ),
            Requirement(
                id="req-4", text="Proficiency in Go for internal tooling", category=Category.PREFERRED,
                source_quote="Proficiency in Go for internal tooling is a plus",
            ),
        ],
    )
    posting_text_ridgeline = (
        "Ridgeline Cloud needs a DevOps Engineer to own CI/CD pipelines across three product teams. You'll "
        "build self-service infrastructure tooling for other engineers. We need someone with 4+ years of "
        "DevOps or SRE experience who has run production Kubernetes clusters and knows their way around "
        "capacity planning and upgrades. You should be comfortable writing and maintaining Terraform "
        "modules for our infrastructure. Proficiency in Go for internal tooling is a plus."
    )
    analysis_ridgeline = AnalysisResult(
        summary="A stretch — solid DevOps fundamentals, but the Kubernetes, Terraform, and Go experience "
        "this role wants aren't demonstrated.",
        verdict=Verdict.STRETCH,
        insights=[
            Insight(
                id="insight-1", text="5 years of DevOps experience, including owning CI/CD for two product teams.",
                kind=InsightKind.STRENGTH, supporting_ids=["req-1", "resp-1"],
            ),
            Insight(
                id="insight-2", text="Built internal tooling adopted by 30+ engineers.",
                kind=InsightKind.STRENGTH, supporting_ids=["resp-2"],
            ),
            Insight(
                id="insight-3", text="No mention of running production Kubernetes clusters or capacity planning.",
                kind=InsightKind.GAP, supporting_ids=["req-2"],
            ),
            Insight(
                id="insight-4", text="No experience writing or maintaining Terraform modules listed.",
                kind=InsightKind.GAP, supporting_ids=["req-3"],
            ),
            Insight(
                id="insight-5", text="No listed experience writing Go.",
                kind=InsightKind.GAP, supporting_ids=["req-4"],
            ),
        ],
        dropped_count=0,
        search_actions=[],
    )
    extraction_ridgeline = ExtractionResult(posting=posting_ridgeline, dropped_ids=[])

    posting_ironwood = Posting(
        title="Staff Site Reliability Engineer",
        company="Ironwood Labs",
        location="Seattle, WA (Hybrid)",
        seniority="Staff",
        salary="$185,000 - $220,000",
        responsibilities=[
            Responsibility(
                id="resp-1", text="Own production incident response",
                source_quote="own production incident response",
            ),
            Responsibility(
                id="resp-2", text="Set on-call standards across the org",
                source_quote="set on-call standards across the org",
            ),
        ],
        requirements=[
            Requirement(
                id="req-1", text="8+ years of SRE or infrastructure experience at scale", category=Category.REQUIRED,
                source_quote="8+ years of SRE or infrastructure experience at scale",
            ),
            Requirement(
                id="req-2", text="Deep Kubernetes expertise across large multi-cluster environments",
                category=Category.REQUIRED,
                source_quote="deep Kubernetes expertise across large multi-cluster environments",
            ),
            Requirement(
                id="req-3", text="Strong background in Terraform-based infrastructure automation",
                category=Category.REQUIRED,
                source_quote="strong background in Terraform-based infrastructure automation",
            ),
            Requirement(
                id="req-4", text="Solid Go skills for internal reliability tooling", category=Category.PREFERRED,
                source_quote="Solid Go skills for internal reliability tooling are a plus",
            ),
        ],
    )
    posting_text_ironwood = (
        "Ironwood Labs is looking for a Staff Site Reliability Engineer to own production incident "
        "response. You'll set on-call standards across the org. This role requires 8+ years of SRE or "
        "infrastructure experience at scale, including deep Kubernetes expertise across large "
        "multi-cluster environments. A strong background in Terraform-based infrastructure automation is "
        "required. Solid Go skills for internal reliability tooling are a plus."
    )
    analysis_ironwood = AnalysisResult(
        summary="Not a fit right now — the seniority bar and infrastructure depth this role wants aren't met.",
        verdict=Verdict.WEAK_FIT,
        insights=[
            Insight(
                id="insight-1",
                text="Owns production incident response today, including postmortems and on-call rotation design.",
                kind=InsightKind.STRENGTH, supporting_ids=["resp-1", "resp-2"],
            ),
            Insight(
                id="insight-2", text="6 years of experience, short of the 8+ years this role requires.",
                kind=InsightKind.GAP, supporting_ids=["req-1"],
            ),
            Insight(
                id="insight-3", text="No mention of Kubernetes experience at multi-cluster scale.",
                kind=InsightKind.GAP, supporting_ids=["req-2"],
            ),
            Insight(
                id="insight-4", text="No Terraform-based infrastructure automation experience listed.",
                kind=InsightKind.GAP, supporting_ids=["req-3"],
            ),
            Insight(
                id="insight-5", text="No listed Go experience.",
                kind=InsightKind.GAP, supporting_ids=["req-4"],
            ),
        ],
        dropped_count=0,
        search_actions=[],
    )
    extraction_ironwood = ExtractionResult(posting=posting_ironwood, dropped_ids=[])

    results = [
        {
            "posting_text": posting_text_anchorpoint,
            "extraction": extraction_anchorpoint,
            "analysis": analysis_anchorpoint,
        },
        {
            "posting_text": posting_text_meridian,
            "extraction": extraction_meridian,
            "analysis": analysis_meridian,
        },
        {
            "posting_text": posting_text_cascade,
            "extraction": extraction_cascade,
            "analysis": analysis_cascade,
        },
        {
            "posting_text": posting_text_ridgeline,
            "extraction": extraction_ridgeline,
            "analysis": analysis_ridgeline,
        },
        {
            "posting_text": posting_text_ironwood,
            "extraction": extraction_ironwood,
            "analysis": analysis_ironwood,
        },
    ]
    errors: list[tuple[int, str]] = []
    gap_patterns = [
        GapPattern(
            label="Advanced Kubernetes operations at scale",
            items=[
                GapPatternItem(posting_number=2, insight_id="insight-4"),
                GapPatternItem(posting_number=3, insight_id="insight-3"),
                GapPatternItem(posting_number=4, insight_id="insight-3"),
                GapPatternItem(posting_number=5, insight_id="insight-3"),
            ],
        ),
        GapPattern(
            label="Terraform and infrastructure-as-code",
            items=[
                GapPatternItem(posting_number=3, insight_id="insight-4"),
                GapPatternItem(posting_number=4, insight_id="insight-4"),
                GapPatternItem(posting_number=5, insight_id="insight-4"),
            ],
        ),
        GapPattern(
            label="Go programming language",
            items=[
                GapPatternItem(posting_number=4, insight_id="insight-5"),
                GapPatternItem(posting_number=5, insight_id="insight-5"),
            ],
        ),
    ]
    return results, errors, gap_patterns
