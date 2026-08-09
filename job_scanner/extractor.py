import re
from dataclasses import dataclass

from job_scanner.llm_client import LLMClient
from job_scanner.models import Category, Posting, Requirement, Responsibility
from job_scanner.validation import find_ungrounded_quotes

EXTRACT_TOOL_NAME = "extract_posting"

EXTRACT_TOOL_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "company": {"type": "string"},
        "location": {
            "type": "string",
            "description": "The work location exactly as stated in the posting. Use an empty string if "
            "the posting does not state one — never write a placeholder like 'unknown' or 'not specified'.",
        },
        "seniority": {
            "type": "string",
            "description": "The seniority level exactly as stated or clearly implied by the posting (e.g. "
            "from the job title). Use an empty string if it truly cannot be determined — never write a "
            "placeholder like 'unknown' or 'not specified'.",
        },
        "salary": {
            "type": "string",
            "description": "ONLY the number or numeric range for compensation, copied verbatim from the "
            "posting (e.g. '$120,000 - $150,000' or '$45/hr'). If the posting states salary inside a "
            "longer sentence, extract just the figure(s) — never the surrounding words or the full "
            "sentence. Use an empty string if the posting does not mention salary or compensation.",
        },
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
    "required": ["title", "company", "location", "seniority", "salary", "responsibilities", "requirements"],
}

SYSTEM_PROMPT = (
    "You are a precise job posting analyst. Extract only what the posting literally "
    "states. Do not infer, assume, or add anything not directly supported by the "
    "text. For every requirement and responsibility, copy an exact verbatim "
    "substring from the posting into source_quote. For salary, copy ONLY the number "
    "or numeric range exactly as written in the posting — if it's stated inside a "
    "sentence like 'the salary for this role is between $65,000 and $80,000 "
    "depending on experience', extract just '$65,000 and $80,000' or similar, never "
    "the full sentence. Use an empty string if none is mentioned — never estimate "
    "or infer a salary that isn't stated. The same rule applies to location and "
    "seniority: if the posting doesn't state one, leave it as an empty string "
    "rather than writing 'unknown' or any other placeholder."
)

_UNKNOWN_PLACEHOLDERS = {"unknown", "n/a", "na", "not specified", "not stated", "none", "tbd"}

_MONEY_RANGE_PATTERN = re.compile(
    r"\$\s?[\d,]+(?:\.\d+)?\s?[kK]?"
    r"(?:\s*(?:-|to|–|—|\band\b)\s*\$?\s?[\d,]+(?:\.\d+)?\s?[kK]?)?"
    r"(?:\s*(?:/|per)\s*(?:hr|hour|yr|year|wk|week|mo|month))?"
)


def _clean_optional_field(value: str) -> str | None:
    cleaned = value.strip().strip("<>").strip()
    if not cleaned or cleaned.lower() in _UNKNOWN_PLACEHOLDERS:
        return None
    return cleaned


def _clean_salary(value: str) -> str | None:
    cleaned = value.strip()
    if not cleaned:
        return None
    match = _MONEY_RANGE_PATTERN.search(cleaned)
    return match.group(0).strip() if match else cleaned


@dataclass
class ExtractionResult:
    posting: Posting
    dropped_ids: list[str]


def is_url(text: str) -> bool:
    return text.strip().lower().startswith(("http://", "https://"))


def extract_posting(posting_text: str, client: LLMClient) -> ExtractionResult:
    raw = client.call_tool(
        system=SYSTEM_PROMPT,
        user=posting_text,
        tool_name=EXTRACT_TOOL_NAME,
        tool_schema=EXTRACT_TOOL_SCHEMA,
        tool_description="Record the structured breakdown of a job posting extracted from its text.",
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

    salary = _clean_salary(raw["salary"]) if raw["salary"] else None
    if salary is not None and salary not in posting_text:
        salary = None

    posting = Posting(
        title=raw["title"],
        company=raw["company"],
        location=_clean_optional_field(raw["location"]),
        seniority=_clean_optional_field(raw["seniority"]),
        salary=salary,
        responsibilities=responsibilities,
        requirements=requirements,
    )

    dropped_ids = find_ungrounded_quotes(posting, posting_text)
    if dropped_ids:
        posting = posting.model_copy(
            update={
                "responsibilities": [r for r in posting.responsibilities if r.id not in dropped_ids],
                "requirements": [r for r in posting.requirements if r.id not in dropped_ids],
            }
        )

    return ExtractionResult(posting=posting, dropped_ids=dropped_ids)
