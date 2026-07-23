from dataclasses import dataclass

from job_scanner.llm_client import LLMClient
from job_scanner.models import Insight, InsightKind, Posting
from job_scanner.validation import find_invalid_references

ANALYZE_TOOL_NAME = "analyze_fit"

ANALYZE_TOOL_SCHEMA = {
    "type": "object",
    "properties": {
        "insights": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "kind": {"type": "string", "enum": ["strength", "gap"]},
                    "supporting_requirement_ids": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["text", "kind", "supporting_requirement_ids"],
            },
        }
    },
    "required": ["insights"],
}

SYSTEM_PROMPT = (
    "You are assessing how well a candidate's background fits a specific job "
    "posting, using only the structured posting breakdown provided plus the "
    "candidate's background text. For each requirement or responsibility the "
    "candidate's background clearly supports, produce a 'strength' insight. For "
    "each requirement or responsibility the background does not support or "
    "contradicts, produce a 'gap' insight. Every insight must cite the "
    "requirement or responsibility ids it is based on, using only ids that "
    "appear in the breakdown you were given. Be honest about real gaps, not "
    "just flattering."
)


def format_posting_for_prompt(posting: Posting) -> str:
    lines = [
        f"Title: {posting.title}",
        f"Company: {posting.company}",
        f"Seniority: {posting.seniority}",
        "",
        "Responsibilities:",
    ]
    for r in posting.responsibilities:
        lines.append(f"- [{r.id}] {r.text}")
    lines.append("")
    lines.append("Requirements:")
    for r in posting.requirements:
        lines.append(f"- [{r.id}] ({r.category.value}) {r.text}")
    return "\n".join(lines)


@dataclass
class AnalysisResult:
    insights: list[Insight]
    dropped_count: int


def analyze_fit(posting: Posting, candidate_text: str, client: LLMClient) -> AnalysisResult:
    user_message = format_posting_for_prompt(posting) + "\n\nCandidate background:\n" + candidate_text
    raw = client.call_tool(
        system=SYSTEM_PROMPT,
        user=user_message,
        tool_name=ANALYZE_TOOL_NAME,
        tool_schema=ANALYZE_TOOL_SCHEMA,
    )

    valid_ids = posting.all_ids()
    insights: list[Insight] = []
    dropped_count = 0

    for item in raw["insights"]:
        violations = find_invalid_references(item["supporting_requirement_ids"], valid_ids)
        if violations:
            dropped_count += 1
            continue
        insights.append(
            Insight(
                id=f"insight-{len(insights) + 1}",
                text=item["text"],
                kind=InsightKind(item["kind"]),
                supporting_requirement_ids=item["supporting_requirement_ids"],
            )
        )

    return AnalysisResult(insights=insights, dropped_count=dropped_count)
