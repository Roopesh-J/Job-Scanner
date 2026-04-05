"""
pipeline.py — All pipeline stages: ingest, capture, validate, analyze.

Stages:
  1. ingest   — normalize raw text (in memory only, not saved)
  2. capture  — extract structured data from JD text (LLM) → saved
  3. validate — check structure, attempt repair if needed (LLM)
  4. analyze  — generate insights from capture artifact only (LLM) → saved
"""

import re
import json
from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, ValidationError
from llm import generate


# ─────────────────────────────────────────────
# SCHEMAS
# ─────────────────────────────────────────────

class CaptureMeta(BaseModel):
    title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    remote_policy: Optional[str] = None
    role_level: Optional[str] = None

class Responsibility(BaseModel):
    id: str
    text: str

class Requirement(BaseModel):
    id: str
    text: str
    modality: Literal["required", "preferred", "unknown"] = "unknown"

class Skill(BaseModel):
    id: str
    name: str
    modality: Literal["required", "preferred", "unknown"] = "unknown"

class CaptureOutput(BaseModel):
    meta: CaptureMeta
    responsibilities: list[Responsibility]
    requirements: list[Requirement]
    skills: list[Skill]
    other_notes: Optional[str] = None


class MustHave(BaseModel):
    text: str
    source_ids: list[str] = []

class NiceToHave(BaseModel):
    text: str
    source_ids: list[str] = []

class SkillMap(BaseModel):
    technical: list[str] = []
    soft: list[str] = []
    domain: list[str] = []
    tools: list[str] = []

class InterviewTopic(BaseModel):
    topic: str
    rationale: str
    source_ids: list[str] = []

class AnalysisOutput(BaseModel):
    summary: str
    must_haves: list[MustHave]
    nice_to_haves: list[NiceToHave]
    skill_map: SkillMap
    interview_topics: list[InterviewTopic]
    prep_questions: list[str]
    questions_to_ask: list[str]
    what_to_emphasize: list[str]
    # Populated only when a candidate profile is provided
    fit_summary: Optional[str] = None
    strengths: list[str] = []
    gaps: list[str] = []


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def _strip_fences(text: str) -> str:
    """Strip markdown code fences if present (e.g. ```json ... ```)."""
    text = text.strip()
    match = re.match(r'^```(?:json)?\s*\n(.*)\n```\s*$', text, re.DOTALL)
    return match.group(1) if match else text


# ─────────────────────────────────────────────
# STAGE 1: INGEST (in memory only)
# ─────────────────────────────────────────────

def ingest(raw_text: str) -> str:
    """Normalize raw JD text. Returns cleaned string."""
    if not raw_text or not raw_text.strip():
        raise ValueError("Job description text is empty.")
    normalized = re.sub(r'\n{3,}', '\n\n', raw_text.strip())
    return "\n".join(line.rstrip() for line in normalized.splitlines())


# ─────────────────────────────────────────────
# STAGE 2: CAPTURE
# ─────────────────────────────────────────────

CAPTURE_SYSTEM = """
You are a precise job description extraction engine.

Your job is to extract structured information from a job description with maximum faithfulness.

Rules:
- Do NOT invent, infer, or add anything not present in the text.
- Use exact or near-exact phrasing from the source for all fields.
- If something is ambiguous or missing, use null or "unknown".
- Modality: classify each requirement as "required", "preferred", or "unknown".

Respond ONLY with valid JSON. No explanation, no markdown fences.
""".strip()

CAPTURE_PROMPT = """
Extract the following from this job description and return as JSON matching the schema below.

JOB DESCRIPTION:
{jd_text}

JSON SCHEMA:
{{
  "meta": {{
    "title": "string or null",
    "company": "string or null",
    "location": "string or null",
    "remote_policy": "string or null",
    "role_level": "e.g. Entry, Mid, Senior, Staff, Principal, Manager, Director, or null"
  }},
  "responsibilities": [
    {{
      "id": "R01",
      "text": "exact or near-exact text from JD"
    }}
  ],
  "requirements": [
    {{
      "id": "REQ01",
      "text": "exact or near-exact text from JD",
      "modality": "required | preferred | unknown"
    }}
  ],
  "skills": [
    {{
      "id": "S01",
      "name": "skill or tool name",
      "modality": "required | preferred | unknown"
    }}
  ],
  "other_notes": "any important details that don't fit above, or null"
}}

Return only valid JSON.
""".strip()

def capture(jd_text: str) -> dict:
    """Run the extraction pass on normalized JD text."""
    prompt = CAPTURE_PROMPT.format(jd_text=jd_text)
    raw_output = generate(prompt=prompt, system=CAPTURE_SYSTEM, temperature=0.0)

    parsed, parse_error = None, None
    try:
        parsed = json.loads(_strip_fences(raw_output))
    except json.JSONDecodeError as e:
        parse_error = str(e)

    return {
        "stage": "capture",
        "raw_output": raw_output,
        "parsed": parsed,
        "parse_error": parse_error,
        "parse_success": parsed is not None,
    }


# ─────────────────────────────────────────────
# STAGE 3: VALIDATE + REPAIR
# ─────────────────────────────────────────────

def validate(capture_artifact: dict) -> dict:
    """Validate the parsed capture output against the CaptureOutput schema."""
    errors = []

    if not capture_artifact.get("parse_success"):
        errors.append(f"JSON parse failed: {capture_artifact.get('parse_error')}")
        return {**capture_artifact, "valid": False, "validation_errors": errors}

    try:
        CaptureOutput.model_validate(capture_artifact["parsed"])
    except ValidationError as e:
        for err in e.errors():
            loc = " -> ".join(str(l) for l in err["loc"])
            errors.append(f"{loc}: {err['msg']}")

    return {**capture_artifact, "valid": len(errors) == 0, "validation_errors": errors}


REPAIR_SYSTEM = """
You are a JSON repair assistant. Fix the broken JSON so it is valid and matches the original schema.
Return ONLY valid JSON, no explanation.
""".strip()

def repair(capture_artifact: dict) -> dict:
    """Attempt to repair an invalid capture artifact via LLM."""
    print("  [validate] Attempting repair...")
    repair_prompt = f"""
Fix this broken JSON and return only valid JSON.

BROKEN JSON:
{capture_artifact.get('raw_output', '')}

Errors:
{chr(10).join(capture_artifact.get('validation_errors', []))}
""".strip()

    repaired_raw = generate(prompt=repair_prompt, system=REPAIR_SYSTEM, temperature=0.0)

    repaired_parsed, repair_error = None, None
    try:
        repaired_parsed = json.loads(_strip_fences(repaired_raw))
    except json.JSONDecodeError as e:
        repair_error = str(e)

    repaired = {
        **capture_artifact,
        "raw_output": repaired_raw,
        "parsed": repaired_parsed,
        "parse_error": repair_error,
        "parse_success": repaired_parsed is not None,
        "was_repaired": True,
    }
    return validate(repaired)


# ─────────────────────────────────────────────
# STAGE 4: ANALYZE
# ─────────────────────────────────────────────

ANALYZE_SYSTEM = """
You are a career coach and job analysis expert.

You will be given a job description and a structured capture artifact extracted from it.
The capture artifact is your primary backbone — it contains pre-extracted, structured data you should build from.
The raw job description is your reference — use it to catch nuance, context, or detail the capture may have missed.

Rules:
- Do NOT invent anything not present in either the capture or the raw JD.
- Ground every insight in the source material. Think of it like citation — you've read the full document, but every claim should be traceable back to it.
- Reference capture item IDs (e.g. REQ01, R03, S02) where possible. If drawing directly from the raw JD instead, use a short quote.
- Be concise and practical — this is for a job seeker preparing to apply.
- When a candidate profile is provided, all personalized fields (fit_summary, strengths, gaps, what_to_emphasize) must be grounded in both the profile and the JD — not generic advice.

Respond ONLY with valid JSON. No explanation, no markdown fences.
""".strip()

_ANALYZE_PROMPT_BASE = """
Produce an analysis of this job description in JSON format.

RAW JOB DESCRIPTION:
{{jd_text}}

CAPTURE ARTIFACT (structured extraction — use as your primary backbone):
{{capture_json}}
{profile_block}
JSON SCHEMA:
{{{{
  "summary": "2-4 sentence plain-English summary of the role",
  "must_haves": [
    {{{{"text": "concise must-have", "source_ids": ["REQ01", "S02"]}}}}
  ],
  "nice_to_haves": [
    {{{{"text": "concise nice-to-have", "source_ids": ["REQ05"]}}}}
  ],
  "skill_map": {{{{
    "technical": ["skill1"],
    "soft": ["skill1"],
    "domain": ["skill1"],
    "tools": ["tool1"]
  }}}},
  "interview_topics": [
    {{{{"topic": "topic name", "rationale": "why it'll come up", "source_ids": ["R02"]}}}}
  ],
  "prep_questions": ["Question to prepare an answer for..."],
  "questions_to_ask": ["Question to ask the recruiter or HM..."],
  "what_to_emphasize": ["Key thing to highlight{emphasis_note}"]{profile_schema}
}}}}

Return only valid JSON.
""".strip()

_PROFILE_BLOCK = """
CANDIDATE PROFILE (resume / background — use for personalized fields):
{profile}
"""

_PROFILE_SCHEMA = """,
  "fit_summary": "2-3 sentence assessment of how well this candidate fits the role",
  "strengths": ["Specific strength from the candidate's background that maps to a role requirement"],
  "gaps": ["A requirement or skill the candidate appears to lack based on their profile"]"""

def _build_analyze_prompt(jd_text: str, capture_json: str, profile: Optional[str]) -> str:
    if profile and profile.strip():
        prompt_template = _ANALYZE_PROMPT_BASE.format(
            profile_block=_PROFILE_BLOCK.format(profile=profile.strip()),
            profile_schema=_PROFILE_SCHEMA,
            emphasis_note=" — make this specific to the candidate's background",
        )
    else:
        prompt_template = _ANALYZE_PROMPT_BASE.format(
            profile_block="",
            profile_schema="",
            emphasis_note="",
        )
    return prompt_template.format(jd_text=jd_text, capture_json=capture_json)


def analyze(validated_capture: dict, jd_text: str, profile: Optional[str] = None) -> dict:
    """Run the analysis pass using the capture artifact, raw JD, and optional candidate profile."""
    if not validated_capture.get("valid"):
        raise ValueError(f"Cannot analyze invalid capture. Errors: {validated_capture.get('validation_errors')}")

    capture_json = json.dumps(validated_capture["parsed"], indent=2)
    prompt = _build_analyze_prompt(jd_text, capture_json, profile)
    raw_output = generate(prompt=prompt, system=ANALYZE_SYSTEM, temperature=0.0)

    parsed, parse_error = None, None
    try:
        parsed = json.loads(_strip_fences(raw_output))
    except json.JSONDecodeError as e:
        parse_error = str(e)

    return {
        "stage": "analyze",
        "raw_output": raw_output,
        "parsed": parsed,
        "parse_error": parse_error,
        "parse_success": parsed is not None,
    }


def validate_analysis(analysis_artifact: dict) -> dict:
    """Validate the parsed analysis output against the AnalysisOutput schema."""
    errors = []

    if not analysis_artifact.get("parse_success"):
        errors.append(f"JSON parse failed: {analysis_artifact.get('parse_error')}")
        return {**analysis_artifact, "valid": False, "validation_errors": errors}

    try:
        AnalysisOutput.model_validate(analysis_artifact["parsed"])
    except ValidationError as e:
        for err in e.errors():
            loc = " -> ".join(str(l) for l in err["loc"])
            errors.append(f"{loc}: {err['msg']}")

    return {**analysis_artifact, "valid": len(errors) == 0, "validation_errors": errors}


def repair_analysis(analysis_artifact: dict) -> dict:
    """Attempt to repair a failed analysis artifact via LLM."""
    print("  [analyze] Attempting repair...")
    repair_prompt = f"""
Fix this broken JSON and return only valid JSON.

BROKEN JSON:
{analysis_artifact.get('raw_output', '')}

Error: {analysis_artifact.get('parse_error', 'Unknown error')}
""".strip()

    repaired_raw = generate(prompt=repair_prompt, system=REPAIR_SYSTEM, temperature=0.0)

    repaired_parsed, repair_error = None, None
    try:
        repaired_parsed = json.loads(_strip_fences(repaired_raw))
    except json.JSONDecodeError as e:
        repair_error = str(e)

    repaired = {
        **analysis_artifact,
        "raw_output": repaired_raw,
        "parsed": repaired_parsed,
        "parse_error": repair_error,
        "parse_success": repaired_parsed is not None,
        "was_repaired": True,
    }
    return validate_analysis(repaired)
