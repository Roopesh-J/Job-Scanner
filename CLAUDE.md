# Job Intelligence Engine (JIE) — Project Context for Claude Code

## What this project is

JIE is a Python CLI tool that transforms raw job descriptions into structured, traceable, and actionable insights using a multi-stage LLM pipeline.

It serves two purposes:
1. A personal job search tool for the developer
2. A portfolio project demonstrating production-grade LLM system design
3. Eventually, a simple online tool others can use

It is deliberately **not** a chatbot or AI wrapper. It is an auditable, deterministic pipeline.

---

## The vision (layered)

### Layer 1 — Current: Understand a single JD deeply
Extract structured data from a job description and generate useful analysis: summary, must-haves, skill map, interview prep, questions to ask.

### Layer 2 — Next: Personalized analysis
The user provides their background and job search preferences once at the start of a session. Every JD analysis is then run against that profile — surfacing fit, gaps, and what to emphasize specific to that person.

### Layer 3 — Later: Market intelligence
Batch process multiple JDs to identify patterns — skills that keep appearing, role level trends, alignment between what the user wants and what the market is asking for.

---

## Session model (important)

There is **no user system, no login, no persistent database of users**. The tool is session-based:
- User provides their profile (experience, preferences, goals) once at the start of a session
- That profile lives in memory for the duration of the session
- All JD analyses in that session are personalized against the profile
- Session ends when the tool closes

This keeps things simple now and doesn't prevent adding accounts later.

---

## Current file structure

```
jie/
├── .env                  # OPENAI_API_KEY, OPENAI_MODEL
├── .gitignore
├── requirements.txt      # openai, python-dotenv
├── CLAUDE.md             # this file
├── run.py                # CLI entry point
├── llm.py                # LLM provider abstraction (swap providers here only)
├── pipeline.py           # all pipeline stages: ingest, capture, validate, repair, analyze
└── outputs/              # timestamped JSON artifacts saved here
```

---

## How it works

### run.py
- Thin CLI entry point
- Job description is pasted into `JD_TEXT` variable at the top of the file
- Supports `--file path/to/jd.txt` as an alternative
- Saves 2 artifacts to `outputs/`: `{run_id}_capture.json` and `{run_id}_analysis.json`
- Prints formatted results to terminal

### llm.py
- Single `generate(prompt, system, model, temperature) -> str` function
- Currently backed by OpenAI API
- **This is the only file that changes when switching LLM providers**
- All pipeline stages call this and nothing else

### pipeline.py
Four stages, all in one file:

1. **ingest** — normalizes whitespace, returns clean string. In memory only, never saved.
2. **capture** — prompts LLM to extract structured JSON from JD text. Schema below.
3. **validate + repair** — checks required fields, attempts LLM repair if invalid.
4. **analyze** — feeds capture artifact (not raw JD) to LLM, generates insights. Schema below.

---

## Capture schema

```json
{
  "meta": {
    "title": "string or null",
    "company": "string or null",
    "location": "string or null",
    "remote_policy": "string or null"
  },
  "responsibilities": [
    { "id": "R01", "text": "exact or near-exact text from JD" }
  ],
  "requirements": [
    { "id": "REQ01", "text": "exact or near-exact text from JD", "modality": "required | preferred | unknown" }
  ],
  "skills": [
    { "id": "S01", "name": "skill or tool name", "modality": "required | preferred | unknown" }
  ],
  "other_notes": "string or null"
}
```

**Known gap:** Role level (senior IC, manager, entry level, etc.) is not currently extracted. This should be added to `meta`.

---

## Analysis schema

```json
{
  "summary": "2-4 sentence plain-English summary",
  "must_haves": [{ "text": "...", "source_ids": ["REQ01"] }],
  "nice_to_haves": [{ "text": "...", "source_ids": ["REQ05"] }],
  "skill_map": {
    "technical": [],
    "soft": [],
    "domain": [],
    "tools": []
  },
  "interview_topics": [{ "topic": "...", "rationale": "...", "source_ids": ["R02"] }],
  "prep_questions": ["..."],
  "questions_to_ask": ["..."],
  "what_to_emphasize": ["..."]
}
```

---

## Key design decisions (and why)

- **3 files not 7** — split where it matters (LLM provider in `llm.py`), consolidated where it doesn't (`pipeline.py` holds all stages)
- **Ingest is in-memory only** — normalizing whitespace doesn't deserve a saved artifact
- **No `evidence` field in capture** — testing showed it was always identical to `text`, so it was removed
- **`JD_TEXT` variable in run.py** — pasting into the terminal was too painful; paste directly into the file instead
- **Analysis sees both the raw JD and the capture artifact** — the capture artifact is the structured backbone, the raw JD is the reference. Think of it like citation: the analyst reads the full document, but every claim should be traceable back to it. This reduces hallucination without artificially limiting the analysis.
- **Analysis does not see the raw JD exclusively** — the capture artifact is always the primary structure. Raw JD is a fallback for nuance or detail capture may have missed.
- **Temperature 0.0** — reproducibility over creativity for both extraction and analysis passes

---

## What's next (priority order)

1. **Add role level to capture schema** — extract seniority/level from JD into `meta`
2. **Add Pydantic validation** — replace the manual key-checking in `validate()` with proper Pydantic models for both capture and analysis schemas
3. **Session profile (Layer 2)** — user provides experience + preferences once at session start; analysis becomes personalized against that profile
4. **Batch mode (Layer 3)** — run multiple JDs in one session, surface cross-JD patterns

---

## What to avoid

- Don't add a user login or auth system — session-based only for now
- Don't add agent frameworks or heavy orchestration
- Don't save ingest artifacts to disk
- Don't let analysis invent claims that can't be traced back to either the capture artifact or the raw JD
- Don't over-engineer validation before Pydantic is in place
- Keep `llm.py` as the single point of LLM access — no direct API calls elsewhere
