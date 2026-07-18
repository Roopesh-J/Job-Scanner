# Job Scanner

Paste a job posting and your background (resume, notes, anything — plain text), and get back a structured, traceable read on the fit: what the posting actually requires vs. prefers, and honest strengths and gaps against your background — each claim linked back to the exact line in the posting that supports it.

The core idea: no plausible-sounding summaries. Every insight has to point at real text, not a guess.

## How it works

1. **Extraction** — the posting is broken down into structured facts (title, company, seniority, responsibilities, requirements), each tagged required/preferred/unclear and backed by a verbatim quote from the posting.
2. **Analysis** — your background is compared against that structured breakdown to produce strengths and gaps, each citing the specific requirement or responsibility it's based on.

If a piece of extracted or generated data can't be verified against the source text, it's dropped rather than shown — with a visible note, not silently.

## Status

This is Phase 0: a working local MVP, not the full vision. Evaluation tooling (measuring how accurate the extraction actually is, with real numbers), batch processing, and a hosted deployment are planned for later phases.

## Running it locally

```bash
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"

export ANTHROPIC_API_KEY=your-key-here
streamlit run job_scanner/app.py
```

## Tech stack

Python, the Anthropic API (direct SDK, no agent framework), Pydantic, Streamlit. Tests via `pytest` — run with `pytest -v`.
