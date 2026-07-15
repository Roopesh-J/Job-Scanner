# Job Scanner v2 — MVP Design

## Context

`job-scanner-v2-build-plan.md` describes a past project the user wants to rebuild, better. It lays out 8 goals (extraction, evaluation, an agentic capability, batch mode, interface, automated checks, deployment, writeup) and a suggested priority order. Per direct user instruction, **this document is a goals reference, not a spec to follow literally** — design decisions below deviate from or reorganize the doc's suggestions where it made sense.

The user wants a real MVP first: functional, evaluated, and honest about what it does — not a demo. The MVP must be architected with clean extension points for the deferred goals (agentic capability, batch mode, deployment), without over-engineering for them now ("no code design that would be too limiting, however also no code design that is too loose").

**MVP scope** (decided with user):
- IN: core extraction + analysis (goal 1), candidate fit read (part of goal 1), evaluation harness (goal 2), automated tests (goal 6, via TDD practice), minimal local-only Streamlit UI (goal 5).
- DEFERRED to v1.1+: agentic capability (goal 3 — doesn't make sense before extraction is proven reliable), batch mode (goal 4), public deployment (goal 7), writeup (goal 8).

This plan covers designing the MVP's architecture and framework. Each deferred goal gets its own design pass later, built on this foundation.

There is no GitHub remote for this project yet. A remote repo and initial push will be created once the MVP is complete and working — until then, work happens on local commits only.

---

## 1. Architecture & tech stack

- **Language/runtime:** Python (existing venv in this repo).
- **LLM:** Anthropic Claude API via the raw Anthropic SDK — no LangChain/LangGraph. Every prompt, decision, and response stays visible and directly testable, which matters given the project's core value is traceability. This also keeps the door open for goal 3 (agentic tool-use) later without fighting a framework's abstractions.
- **UI:** Streamlit, run locally only for the MVP (`streamlit run app.py`). No hosting/auth/rate-limiting work yet — that's real effort that only matters once strangers can reach it (goal 7, deferred).
- **Package layout** — organized around pipeline stages so each is independently testable/swappable:

```
job_scanner/
  llm/            # Anthropic client wrapper, prompt templates
  extraction/     # Stage 1: fact-finding (posting text -> structured facts)
  analysis/       # Stage 2: reasoning (facts -> insights, gaps, prep topics)
  fit/            # Stage 3: candidate fit read (facts + profile -> strengths/gaps)
  eval/           # Goal 2: reference set, metrics, report generation
  app.py          # Streamlit entrypoint
tests/
  fixtures/       # golden postings + expected extractions for regression tests
.github/workflows/ci.yml
pyproject.toml
```

---

## 2. Core pipeline & traceability

Every extracted fact and every downstream insight must carry an ID and be verifiable against source text — this is the mechanism, not just a principle.

**Stage 1 — Extraction** (fact-finding only; the only judgment made here is required/preferred/unclear classification):
- Claude call using a **forced tool call** (`tool_choice`) against a strict schema — not a "please output JSON" prompt — to guarantee valid structure every call.
- Output: `Posting` object with `title`, `company`, `location`, `seniority`, and lists of `Requirement`/`Responsibility` items, each with:
  - `id` (e.g. `req-1`)
  - `text` (model's paraphrase)
  - `category`: `required` / `preferred` / `unclear`
  - `source_quote`: an **exact verbatim substring** copied from the posting
- `source_quote` is the traceability mechanism: code checks `source_quote in posting_text` after every call. A non-matching quote is a deterministic, caught hallucination — this check doubles as a goal-6 regression test.

**Stage 2 — Analysis** (reasoning on top of Stage 1's structured output only, never on raw posting text):
- Second Claude call takes the `Posting` object (not raw text) and produces `Insight` objects (what to emphasize, expected interview gaps, prep topics), each carrying `supporting_requirement_ids` referencing Stage 1 IDs.
- Because Stage 2 never sees raw text, it cannot invent a requirement — it can only reference IDs that already exist, which code validates.

**Stage 3 — Fit read** (optional; only runs if a candidate profile is provided):
- Third call takes `Posting` + pasted profile text, produces `FitRead` (`strengths`/`gaps`), each with `supporting_requirement_ids`.
- Candidate profile is provided as **pasted plain text** (not file upload) — same textarea pattern as the posting input, no file-parsing dependency to build/maintain for MVP.

**Result:** a pure-function pipeline, `posting_text → Posting → [Insight] → FitRead`, independently testable per stage. This is also the seam batch mode (v1.1) will map over, and where Stage 1 would later gain a `confidence` field to trigger an agentic lookup (goal 3, later) — no rewrite needed for either.

---

## 3. Evaluation harness (goal 2)

User has real saved postings but no labels yet — this designs the labeling schema and metrics.

**Reference set:**
- A folder of raw posting text files + one hand-labeled JSON file per posting, using the **same `Posting` schema** Stage 1 produces — no separate schema to invent, and predictions/labels are directly comparable.
- Start with ~15–25 postings for real, defensible numbers without labeling becoming its own project; grow over time.

**Matching predicted requirements to reference requirements:**
- Model wording won't exactly match hand-labeled wording, so exact string match would undercount. Use **embedding similarity matching**: embed both sets of requirement texts with a local `sentence-transformers` model (no extra API cost), compute cosine similarity, and take each prediction's best-scoring reference match.
- If the best score clears a threshold (e.g. 0.7) → match (true positive). Unmatched predictions = false positives (invented). Unmatched reference items = false negatives (missed).
- This is a one-shot embedding comparison (nearest-neighbor / semantic-search style), not autoregressive generation — no sequence or next-token prediction involved.

**The three metrics the source doc calls for, made concrete:**
1. **Requirement-finding accuracy** — precision/recall from the matching step above.
2. **Required/preferred/unclear accuracy** — for each matched pair, compare `category` directly → confusion matrix.
3. **Grounding accuracy** — two deterministic, non-LLM checks: (a) every `source_quote` is a verbatim substring of the posting text, (b) every `supporting_requirement_ids` reference points to an ID that actually exists in Stage 1's output. Reportable as pass/fail percentages.

**Output:** `eval/runner.py` runs the full pipeline against the reference set and produces a report (JSON + a visualization using the dataviz skill for the confusion matrix / precision-recall bars) — real numbers, not a claim that evaluation exists.

---

## 4. Automated checks (goal 6) & CI

Built alongside the code via the TDD skill, not retrofitted:
- **Unit tests** per pipeline stage against fixed input/output fixtures.
- **Schema validation tests** — Pydantic models reject malformed output at the boundary (bad category value, missing field, etc.) so a broken structured-output call fails loudly.
- **Grounding regression tests** — the two deterministic eval checks (verbatim quote match, valid ID references) run against fixture postings on every test run, catching a prompt change that breaks traceability immediately.
- **CI** — GitHub Actions runs `pytest` on every push/PR. Unit tests run against **mocked/recorded Claude API responses** (fast, deterministic, no per-commit API cost); live-API smoke tests run separately/manually, not on every push. Note: CI wiring will only take effect once a GitHub remote exists (see Context) — the workflow file can be written now, but won't run until the repo is pushed.

---

## 5. UI (goal 5, minimal, local)

Single-page Streamlit app:
- Two text areas: **posting** (required), **candidate profile** (optional — filling it runs Stage 3).
- "Analyze" button runs the pipeline synchronously (postings are short; a few seconds of latency is fine locally).
- Results rendered with **visible** traceability: each insight/gap/prep-topic shown next to the `source_quote`(s) grounding it (e.g. an expandable "why" showing the exact posting line). This is the one place the source doc is explicit that traceability must be visible, not just present in the underlying data.

---

## 6. Extensibility seams for deferred goals (no code now, design only)

- **Batch mode (v1.1):** pipeline is already a pure function over one posting — batch mode is "call it N times + add an aggregation module," no core rewrite.
- **Agentic capability (later):** Stage 1's `Requirement` schema can grow a `confidence` field later; low confidence triggers a tool-use loop before finalizing. Additive, not a schema break.
- **Deployment (later):** leading option is **Streamlit Community Cloud** (or Hugging Face Spaces) — purpose-built for a Streamlit app + secrets-managed API key. A static-frontend/GitHub-Pages split was considered and rejected: GitHub Pages only serves static files, this app needs a live server-side process for real-time Claude API calls, and exposing the API key client-side would be a security risk. Rate-limiting/cost caps get designed at this stage, not before.

---

## Verification (end of MVP implementation)

- `pytest` passes locally and in CI, including schema-validation and grounding-regression tests.
- `eval/runner.py` runs against the labeled reference set and produces a real report (precision/recall, category confusion matrix, grounding pass rate) — reviewed manually for plausibility, not just "it ran."
- Manual smoke test: run `streamlit run app.py`, paste a real posting (+ a profile), confirm structured output renders with visible source-quote traceability for at least one insight and one fit-read item.

---

## Next step

Turn this into a step-by-step implementation plan via the `writing-plans` skill, starting with Stage 1 extraction + its schema, per the priority order: extraction foundation before evaluation before anything else.
