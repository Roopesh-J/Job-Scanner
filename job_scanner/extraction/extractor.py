from dataclasses import dataclass

from job_scanner.llm.client import LLMClient
from job_scanner.models import Category, Posting, Requirement, Responsibility
from job_scanner.validation import find_ungrounded_quotes

EXTRACT_TOOL_NAME = "extract_posting"

EXTRACT_TOOL_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "company": {"type": "string"},
        "location": {"type": "string"},
        "seniority": {"type": "string"},
        "responsibilities": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "source_quote": {
                        "type": "string",
                        "description": "Exact verbatim substring copied from the posting text that supports this responsibility.",
                    },
                },
                "required": ["text", "source_quote"],
            },
        },
        "requirements": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "category": {"type": "string", "enum": ["required", "preferred", "unclear"]},
                    "source_quote": {
                        "type": "string",
                        "description": "Exact verbatim substring copied from the posting text that supports this requirement.",
                    },
                },
                "required": ["text", "category", "source_quote"],
            },
        },
    },
    "required": ["title", "company", "location", "seniority", "responsibilities", "requirements"],
}

SYSTEM_PROMPT = (
    "You are a precise job posting analyst. Extract only what the posting literally "
    "states. Do not infer, assume, or add anything not directly supported by the "
    "text. For every requirement and responsibility, copy an exact verbatim "
    "substring from the posting into source_quote."
)


@dataclass
class ExtractionResult:
    posting: Posting
    dropped_ids: list[str]


def extract_posting(posting_text: str, client: LLMClient) -> ExtractionResult:
    raw = client.call_tool(
        system=SYSTEM_PROMPT,
        user=posting_text,
        tool_name=EXTRACT_TOOL_NAME,
        tool_schema=EXTRACT_TOOL_SCHEMA,
    )

    responsibilities = [
        Responsibility(id=f"resp-{i + 1}", text=r["text"], source_quote=r["source_quote"])
        for i, r in enumerate(raw["responsibilities"])
    ]
    requirements = [
        Requirement(
            id=f"req-{i + 1}",
            text=r["text"],
            category=Category(r["category"]),
            source_quote=r["source_quote"],
        )
        for i, r in enumerate(raw["requirements"])
    ]

    posting = Posting(
        title=raw["title"],
        company=raw["company"],
        location=raw["location"],
        seniority=raw["seniority"],
        responsibilities=responsibilities,
        requirements=requirements,
    )

    dropped_ids = find_ungrounded_quotes(posting, posting_text)
    if dropped_ids:
        posting = Posting(
            title=posting.title,
            company=posting.company,
            location=posting.location,
            seniority=posting.seniority,
            responsibilities=[r for r in posting.responsibilities if r.id not in dropped_ids],
            requirements=[r for r in posting.requirements if r.id not in dropped_ids],
        )

    return ExtractionResult(posting=posting, dropped_ids=dropped_ids)
