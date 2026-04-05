# Job Intelligence Engine

A Python tool that transforms raw job descriptions into structured, traceable, actionable insights using a multi-stage LLM pipeline. Optionally personalizes analysis against your resume.

## What it does

Paste a job description and get back:

- **Structured extraction** — title, company, location, role level, responsibilities, requirements, skills (all with IDs for traceability)
- **Analysis** — summary, must-haves, nice-to-haves, skill map, interview topics, prep questions, questions to ask, what to emphasize
- **Personalized fit** *(optional)* — paste your resume and get a fit assessment, strengths, and gaps specific to you

All outputs are saved as timestamped JSON artifacts for review.

---

## Setup

**Requirements:** Python 3.9+, an [Anthropic API key](https://console.anthropic.com/)

```bash
# 1. Clone and install dependencies
git clone <your-repo-url>
cd job-intel
pip install -r requirements.txt

# 2. Configure your API key
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

**.env format:**
```
ANTHROPIC_API_KEY=your_key_here
ANTHROPIC_MODEL=claude-sonnet-4-6
```

---

## Usage

### Web UI (recommended)

```bash
python app.py
```

Open `http://localhost:5000`. Paste a job description on the left, optionally paste your resume on the right, and click Analyze. Your profile is remembered for the session.

### CLI

```bash
# JD pasted into run.py (edit JD_TEXT variable at top of file)
python run.py

# JD from file
python run.py --file path/to/jd.txt

# With personalized analysis
python run.py --file path/to/jd.txt --profile path/to/resume.txt
```

---

## How it works

Four pipeline stages run in sequence:

| Stage | What it does | Saved? |
|---|---|---|
| **Ingest** | Normalize whitespace | No |
| **Capture** | LLM extracts structured JSON from JD | Yes |
| **Validate / Repair** | Pydantic validation, LLM repair if needed | On failure |
| **Analyze** | LLM generates insights from capture artifact + raw JD | Yes |

Artifacts are saved to `outputs/` as `{run_id}_capture.json` and `{run_id}_analysis.json`.

### Capture schema

```json
{
  "meta": { "title", "company", "location", "remote_policy", "role_level" },
  "responsibilities": [{ "id": "R01", "text": "..." }],
  "requirements": [{ "id": "REQ01", "text": "...", "modality": "required|preferred|unknown" }],
  "skills": [{ "id": "S01", "name": "...", "modality": "required|preferred|unknown" }],
  "other_notes": "..."
}
```

### Analysis schema

```json
{
  "summary": "...",
  "must_haves": [{ "text": "...", "source_ids": ["REQ01"] }],
  "nice_to_haves": [...],
  "skill_map": { "technical": [], "soft": [], "domain": [], "tools": [] },
  "interview_topics": [{ "topic": "...", "rationale": "...", "source_ids": ["R02"] }],
  "prep_questions": [...],
  "questions_to_ask": [...],
  "what_to_emphasize": [...],
  "fit_summary": "...",   // only when profile provided
  "strengths": [...],     // only when profile provided
  "gaps": [...]           // only when profile provided
}
```

---

## File structure

```
├── run.py              # CLI entry point
├── app.py              # Flask web interface
├── pipeline.py         # All pipeline stages + Pydantic schemas
├── llm.py              # LLM provider abstraction (swap providers here)
├── templates/
│   └── index.html      # Web UI template
├── outputs/            # Timestamped JSON artifacts (gitignored)
├── .env                # API key config (gitignored)
├── .env.example        # Template for .env
└── requirements.txt
```

**To switch LLM providers**, only `llm.py` needs to change.

---

## Design principles

- **Traceable** — every insight references the capture item ID it came from (REQ01, R03, etc.)
- **Auditable** — raw LLM outputs and parsed artifacts are both saved to disk
- **Deterministic** — temperature 0.0 on all passes for reproducibility
- **Minimal** — 3 core files, no agent frameworks, no databases

---

## Roadmap

- [x] Structured JD extraction with role level
- [x] Pydantic validation with LLM repair fallback
- [x] Personalized analysis against candidate profile
- [x] Flask web UI
- [ ] Batch mode — process multiple JDs, surface cross-JD patterns
