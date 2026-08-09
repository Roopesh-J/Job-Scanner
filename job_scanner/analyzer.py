from dataclasses import dataclass

from job_scanner.llm_client import LLMClient
from job_scanner.models import Insight, InsightKind, Posting, SearchAction, Verdict
from job_scanner.validation import find_invalid_references

ANALYZE_TOOL_NAME = "analyze_fit"

ANALYZE_TOOL_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "verdict": {"type": "string", "enum": ["strong_match", "stretch", "weak_fit"]},
        "insights": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "kind": {"type": "string", "enum": ["strength", "gap"]},
                    "supporting_ids": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["text", "kind", "supporting_ids"],
            },
        },
    },
    "required": ["summary", "verdict", "insights"],
}

SYSTEM_PROMPT = (
    "You are assessing how well a candidate's background fits a specific job "
    "posting, using only the structured posting breakdown provided plus the "
    "candidate's background text. For each requirement or responsibility the "
    "candidate's background clearly supports, produce a 'strength' insight. For "
    "each requirement or responsibility the background does not support or "
    "contradicts, produce a 'gap' insight. Every insight must cite the "
    "requirement or responsibility ids it is based on, using only ids that "
    "appear in the breakdown you were given, in the 'supporting_ids' field. "
    "Those ids (like 'req-1' or 'resp-2') are for internal linking only — "
    "never write them into the insight's 'text', even in passing. Be honest "
    "about real gaps, not just flattering.\n\n"
    "These are read as a fast scan-list, not prose, so every insight must be "
    "as short as possible: a clipped phrase or fragment, not a full sentence "
    "with a subject and verb wrapped around it. Name the actual skill, tool, "
    "or experience and stop there. Cut every word that doesn't add new "
    "information.\n\n"
    "For strengths: being in the 'strengths' list already says it's a match, "
    "so don't editorialize on top of that. Never write 'you have', 'you've "
    "got', 'you match this well', 'this lines up with', 'already handled', "
    "or any other framing that just restates 'this is a strength' in more "
    "words — that's implied, so cut it. State the qualification itself and "
    "nothing else. Good: '7 years of backend engineering.' 'Led a "
    "monolith-to-Kubernetes migration.' 'Multi-region active-active "
    "deployment experience.' 'Mentored a team of 4 engineers.' Bad (restates "
    "the obvious, too long): 'You've got 7 years of backend experience, "
    "well past the 5 year bar.' 'You led a monolith to Kubernetes "
    "migration, which is basically this job's main task.'\n\n"
    "For gaps: use a short, consistent template like 'No listed experience "
    "with X' or 'No mention of X' — name the specific missing thing and "
    "stop. Good: 'No listed experience with Rust.' 'No mention of "
    "Terraform.' Bad (roundabout, too long): 'Data governance and lineage "
    "initiatives aren't something your resume touches on.'\n\n"
    "Never use an em dash or a hyphenated 'X — Y' construction, and avoid "
    "semicolons and subordinate clauses ('which', 'that', 'since') tacked "
    "onto the end. If an insight is longer than about 8 words, it's almost "
    "certainly still saying too much — cut it down further.\n\n"
    "If a requirement or responsibility names a specific skill, tool, or "
    "acronym you are not confident you understand correctly, and getting it "
    "wrong would change a strength/gap judgment, search the web for it before "
    "judging that item — at most twice total. If a search errors or returns "
    "nothing useful, proceed with your best understanding rather than getting "
    "stuck.\n\n"
    "Every call to analyze_fit is REQUIRED to include all three: 'summary' "
    "(1-2 short, plain sentences giving an honest overall read on this "
    "posting and the main reason why — same casual, direct voice as the "
    "insights, not corporate-sounding; this is the first thing the candidate "
    "reads, so make it count on its own), 'verdict' (one of 'strong_match', "
    "'stretch', or 'weak_fit' — your own honest categorical judgment, "
    "consistent with the summary and the balance of strengths vs. gaps), and "
    "'insights' (the strength/gap list). A call missing any of these is "
    "invalid — always finish by calling analyze_fit with all three."
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
    summary: str
    verdict: Verdict
    insights: list[Insight]
    dropped_count: int
    search_actions: list[SearchAction]


_VALID_VERDICTS = {v.value for v in Verdict}


def _is_complete_response(raw: dict) -> bool:
    return (
        isinstance(raw.get("summary"), str)
        and bool(raw["summary"].strip())
        and raw.get("verdict") in _VALID_VERDICTS
        and isinstance(raw.get("insights"), list)
    )


def analyze_fit(posting: Posting, candidate_text: str, client: LLMClient) -> AnalysisResult:
    user_message = format_posting_for_prompt(posting) + "\n\nCandidate background:\n" + candidate_text

    raw: dict = {}
    raw_search_actions: list = []
    for attempt in range(2):
        raw, raw_search_actions = client.call_tool_with_search(
            system=SYSTEM_PROMPT,
            user=user_message,
            tool_name=ANALYZE_TOOL_NAME,
            tool_schema=ANALYZE_TOOL_SCHEMA,
            tool_description=(
                "Record the strength and gap insights comparing the candidate's background to the posting."
            ),
        )
        if _is_complete_response(raw):
            break
        if attempt == 1:
            raise RuntimeError("The model's analysis response was incomplete. Try analyzing this posting again.")

    valid_ids = posting.all_ids()
    insights: list[Insight] = []
    dropped_count = 0

    for item in raw["insights"]:
        if not isinstance(item, dict) or not all(k in item for k in ("text", "kind", "supporting_ids")):
            dropped_count += 1
            continue
        violations = find_invalid_references(item["supporting_ids"], valid_ids)
        if violations:
            dropped_count += 1
            continue
        insights.append(
            Insight(
                id=f"insight-{len(insights) + 1}",
                text=item["text"],
                kind=InsightKind(item["kind"]),
                supporting_ids=item["supporting_ids"],
            )
        )

    search_actions = [SearchAction(**action) for action in raw_search_actions]

    return AnalysisResult(
        summary=raw["summary"],
        verdict=Verdict(raw["verdict"]),
        insights=insights,
        dropped_count=dropped_count,
        search_actions=search_actions,
    )
