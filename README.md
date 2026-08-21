# JobScan

**[Try it live →](https://job-scanner-roopj.streamlit.app/)**

![JobScan — paste a posting and your background, get back a traceable read on the fit](docs/images/hero.png)

Paste a job posting and your background (resume, notes, anything — plain text), and get back a structured, traceable read on the fit: what the posting actually requires vs. prefers, and honest strengths and gaps against your background — each claim linked back to the exact line in the posting that supports it.

The core idea: no plausible-sounding summaries. Every insight has to point at real text, not a guess.

No time to paste your own? Click **"See a sample analysis"** on the input page for an instant, pre-loaded example — it makes no API calls and costs nothing to load.

## Recurring gaps — the part a one-off chat can't do

![Recurring gaps: the same gap grouped across multiple postings, with how many postings it shows up in](docs/images/recurring-gaps.png)

Paste more than one posting and JobScan doesn't just rank them by fit — it looks across the whole batch for gaps that show up more than once, and groups them together. A chat conversation only ever sees one posting at a time, so it can't tell you which gap is actually worth closing first because it keeps costing you the same roles. Each recurring gap expands to show exactly what every affected posting asked for, in that posting's own words.

## Every claim is traceable

![A posting's strengths and gaps next to the source text, with every cited line underlined](docs/images/citations.png)

Click a posting and every strength or gap sits next to the source text it came from, with the exact cited lines underlined. If a piece of extracted or generated data can't be verified against the source text, it's dropped rather than shown — with a visible note, not silently.

## How it works

1. **Extraction** — the posting is broken down into structured facts (title, company, seniority, responsibilities, requirements), each tagged required/preferred/unclear and backed by a verbatim quote from the posting.
2. **Analysis** — your background is compared against that structured breakdown to produce strengths and gaps, each citing the specific requirement or responsibility it's based on.
3. **Batch mode** — analyze up to 5 postings in one run, ranked by fit, instead of one at a time.
4. **Recurring gaps** — across that batch, the gaps that show up in more than one posting get grouped together and surfaced first.

## Using it

**The live demo** is the fastest way to try it — no setup, nothing to install. It's a single shared deployment, though, so postings analyzed per day are capped and split across everyone visiting the link (`usage_guard.DAILY_POSTING_LIMIT`).

**Run it yourself** if you want no shared limit, or want to read/change the code:

```bash
git clone https://github.com/Roopesh-J/Job-Scanner.git
cd Job-Scanner
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"

export ANTHROPIC_API_KEY=your-key-here
streamlit run job_scanner/app.py
```

You'll need your own [Anthropic API key](https://console.anthropic.com/) — API usage is billed to that key, not shared with anyone else.

## Evaluation

`job_scanner/eval/` measures how well Stage 1 (extraction) actually performs, against a hand-labeled
reference set of 5 postings in `tests/fixtures/eval/`: requirement/responsibility precision and recall,
category (required/preferred/unclear) accuracy, and grounding rate (the fraction of extracted items whose
quote is verifiably real). Matching predicted items to reference items uses local sentence embeddings
(`sentence-transformers`, `all-MiniLM-L6-v2`) rather than exact-string comparison, so a differently-worded
but equivalent extraction still counts as correct.

Latest run against the reference set (2026-08-21):

| Metric | Score |
|---|---|
| Requirement precision | 1.00 |
| Requirement recall | 1.00 |
| Responsibility precision | 0.95 |
| Responsibility recall | 1.00 |
| Category accuracy | 0.85 |
| Grounding rate | 1.00 |

The one recurring miss: the model tends to call an ambiguous requirement "required" or "preferred" rather
than correctly flagging it "unclear" — every category error in this run was exactly that pattern (0 errors
in the other direction).

Run it yourself with a real `ANTHROPIC_API_KEY` set (this makes real, billed API calls):

```bash
python -m job_scanner.eval.run_eval
```

`matching.py` and `metrics.py` have their own fast, free unit tests (`pytest tests/test_eval_matching.py
tests/test_eval_metrics.py`) using the local embedding model against synthetic examples — no API calls
involved. `run_eval.py` itself is intentionally not part of the `pytest` suite.

## Deploying your own copy (Streamlit Community Cloud)

1. Fork this repo. On [share.streamlit.io](https://share.streamlit.io), connect your fork and set the main file path to `job_scanner/app.py`.
2. In the app's Secrets panel, add:
   ```toml
   ANTHROPIC_API_KEY = "your-key-here"
   ```
3. Deploy. `requirements.txt` (`-e .`) installs the package and its dependencies from `pyproject.toml`.

A deployed copy has no login/passcode by design — anyone with the URL can use it. To keep API spend bounded, there's a shared, in-process daily cap on postings analyzed (`usage_guard.DAILY_POSTING_LIMIT`), plus per-batch (`MAX_POSTINGS_PER_BATCH`) and per-field character limits. The daily counter lives in memory, so it resets if the process restarts (a redeploy, or Streamlit Community Cloud waking from inactivity) — it's a best-effort budget, not a hard guarantee. Also note that the character limits (`max_chars` on the input widgets) are client-side widget enforcement only, with no server-side re-validation — they stop accidental oversized pastes, not a client that speaks Streamlit's protocol directly.

## Tech stack

Python, the Anthropic API (direct SDK, no agent framework), Pydantic, Streamlit. Tests via `pytest` — run with `pytest -v`.
