# JobScan

Paste a job posting and your background (resume, notes, anything — plain text), and get back a structured, traceable read on the fit: what the posting actually requires vs. prefers, and honest strengths and gaps against your background — each claim linked back to the exact line in the posting that supports it.

The core idea: no plausible-sounding summaries. Every insight has to point at real text, not a guess.

## How it works

1. **Extraction** — the posting is broken down into structured facts (title, company, seniority, responsibilities, requirements), each tagged required/preferred/unclear and backed by a verbatim quote from the posting.
2. **Analysis** — your background is compared against that structured breakdown to produce strengths and gaps, each citing the specific requirement or responsibility it's based on.

If a piece of extracted or generated data can't be verified against the source text, it's dropped rather than shown — with a visible note, not silently.

## Running it locally

```bash
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"

export ANTHROPIC_API_KEY=your-key-here
streamlit run job_scanner/app.py
```

## Deploying (Streamlit Community Cloud)

1. On [share.streamlit.io](https://share.streamlit.io), connect this GitHub repo and set the main file path to `job_scanner/app.py`.
2. In the app's Secrets panel, add:
   ```toml
   ANTHROPIC_API_KEY = "your-key-here"
   ```
3. Deploy. `requirements.txt` (`-e .`) installs the package and its dependencies from `pyproject.toml`.

The app has no login/passcode by design — anyone with the URL can use it. To keep API spend bounded, there's a shared, in-process daily cap on postings analyzed (`usage_guard.DAILY_POSTING_LIMIT`), plus per-batch (`MAX_POSTINGS_PER_BATCH`) and per-field character limits. The daily counter lives in memory, so it resets if the process restarts (a redeploy, or Streamlit Community Cloud waking from inactivity) — it's a best-effort budget, not a hard guarantee. Also note that the character limits (`max_chars` on the input widgets) are client-side widget enforcement only, with no server-side re-validation — they stop accidental oversized pastes, not a client that speaks Streamlit's protocol directly.

## Tech stack

Python, the Anthropic API (direct SDK, no agent framework), Pydantic, Streamlit. Tests via `pytest` — run with `pytest -v`.
