# Job Scanner — MVP Design

## Context

`job-scanner-build-plan.md` is a goals document inspired by a past project the user built before, but this is being treated as the first version of Job Scanner, not a "v2" rebuild. It lays out 8 goals (extraction, evaluation, an agentic capability, batch mode, interface, automated checks, deployment, writeup) and a suggested priority order. Per direct user instruction, **this document is a goals reference, not a spec to follow literally** — design decisions below deviate from or reorganize the doc's suggestions where it made sense.

This design went through two rounds. The first pass scoped a full MVP: three-stage pipeline (extract → generic insights → optional candidate fit read), an embedding-based evaluation harness, and CI. Before implementation started, discussion surfaced that this front-loaded rigor (evaluation, exception-raising validation) ahead of a working demo, and that the pipeline split generic insights and candidate fit into two features when they're really the same thing. This document reflects the corrected, phased design.

**Core hypothesis:** the product helps someone applying for jobs by identifying whether a resume/background is a good fit for a posting (or a posting a good fit for a background — same comparison, either direction). Generic insights independent of a candidate's actual background aren't the real value; extraction alone is just summarization. Insights only become real value once evaluated against something concrete — so candidate background text is a required input to the core loop, not an optional add-on.

---

## Phase model

- **Phase 0 (this document's scope):** posting + candidate background text in → grounded structured extraction + resume-aware strengths/gaps out. No eval harness, no CI.
- **Phase 1 (next):** evaluation harness — reference set, matching, precision/recall, grounding-rate metrics. Deferred because it only makes sense once Phase 0 produces something real to measure.
- **Phase 2+:** generic posting-only insights (interview prep topics not tied to a resume), batch mode, agentic capability (goal 3 from the source doc), CI, public deployment, writeup.

---

## 1. Architecture & tech stack

- **Language/runtime:** Python 3.12 (existing venv in this repo).
- **LLM:** Anthropic Claude API via the raw Anthropic SDK — no LangChain/LangGraph. Every prompt, decision, and response stays visible and directly testable, which matters given the project's core value is traceability.
- **UI:** Streamlit, run locally only for Phase 0 (`streamlit run job_scanner/app.py`). No hosting/auth/rate-limiting work yet.
- **Dependencies:** `anthropic`, `pydantic`, `streamlit`, `pytest` (dev). No `sentence-transformers`/`numpy` in Phase 0 — those are Phase 1's, for eval matching.
- **Package layout:**

```
job_scanner/
  llm/client.py            # Anthropic client wrapper, forced tool calls
  models.py                 # Posting, Requirement, Responsibility, Insight, etc.
  validation.py              # find_ungrounded_quotes, find_invalid_references (pure functions)
  extraction/extractor.py    # Stage 1: posting text -> ExtractionResult
  analysis/analyzer.py       # Stage 2: posting + candidate text -> AnalysisResult
  ui_helpers.py              # pure rendering helpers (id lookup, source formatting)
  app.py                     # Streamlit entrypoint
tests/
  fixtures/                  # golden postings + expected extractions for regression tests
pyproject.toml
```

There is no GitHub remote for this project yet. A remote repo and initial push will be created once Phase 0 is complete and working — until then, work happens on local commits only.

---

## 2. Core pipeline & traceability

Two stages, not three — generic insights and candidate fit were split in the first design pass, but they're the same comparison from different angles, and generic insights without a candidate background aren't the actual product.

**Stage 1 — Extraction** (fact-finding only; the only judgment made here is required/preferred/unclear classification):
- Claude call using a **forced tool call** (`tool_choice`) against a strict schema — not a "please output JSON" prompt — to guarantee valid structure every call.
- Raw model output has `title`, `company`, `location`, `seniority`, and lists of responsibility/requirement items with `text` (+ `category` for requirements) and `source_quote`. **IDs are assigned by code** (`req-1`, `resp-1`, ... via enumeration) — never by the model, which is unreliable at bookkeeping like unique sequential IDs.
- `source_quote` must be an **exact verbatim substring** of the posting text — checked with a plain deterministic substring check (`quote in posting_text`), never an LLM judge.
- Returns `ExtractionResult(posting: Posting, dropped_ids: list[str])`. See §3 for what happens to items that fail the grounding check.

**Stage 2 — Analysis** (reasoning over Stage 1's structured output only, never raw posting text, plus the candidate's background text):
- Second Claude call takes the `Posting` object + the candidate's pasted background text, and produces `Insight` items, each with a `kind` of `strength` or `gap` and `supporting_requirement_ids` referencing Stage 1 IDs.
- Because this stage never sees raw posting text, it cannot invent a requirement — it can only reference IDs that already exist in Stage 1's output, which code validates.
- Candidate background is provided as **pasted plain text** (not file upload) — no PDF/DOCX parsing dependency to build/maintain, and it doesn't need to be a formatted resume: any text works (informal notes, a LinkedIn About section, etc.).
- Returns `AnalysisResult(insights: list[Insight], dropped_count: int)`. See §3 for filtering behavior.

**Result:** a pure-function pipeline, `posting_text → ExtractionResult`, then `(Posting, candidate_text) → AnalysisResult`. Both stages are independently testable. This is also the seam batch mode (Phase 2+) will map over, and where an agentic lookup (goal 3, later) would slot into Stage 1 — no rewrite needed for either.

---

## 3. Validation behavior: item-level filtering, not blocking or silent

This was the one real design mistake caught and corrected during planning, worth documenting so it doesn't get re-litigated. The instinct was to make validation non-blocking so one bad extraction doesn't crash the whole request — reasonable goal, wrong first mechanism.

**What was considered and rejected:**
- **Hard-raise on any violation** (the original Phase-0-planning-round design): one ungrounded quote or one bad reference id kills the entire request. Correct in principle but bad UX — a single shaky item shouldn't nuke an otherwise-good extraction.
- **Silent pass-through** (briefly proposed, then rejected): don't check at all, or check but don't act on it. This doesn't save any implementation effort — `find_ungrounded_quotes`/`find_invalid_references` are the same pure functions either way — and it lets unverifiable data flow straight into the fit judgment, which is the actual product. That defeats the entire traceability premise the project is built on.

**What Phase 0 actually does — item-level filtering:**
- Stage 1: any requirement/responsibility whose `source_quote` isn't a verbatim substring of the posting text is **dropped from the returned `Posting`**, not raised as an exception. Its id is collected in `ExtractionResult.dropped_ids`.
- Stage 2: any insight citing a `supporting_requirement_ids` value that doesn't exist in Stage 1's output is **dropped from the returned insight list**, not raised. The count is collected in `AnalysisResult.dropped_count`.
- The UI (§5) surfaces these as a visible caveat ("2 items couldn't be verified and were excluded") — nothing ungrounded is ever silently shown as trustworthy, but one bad item never blocks the rest of a useful result.

---

## 4. UI (Phase 0, minimal, local)

Single-page Streamlit app:
- Two **required** text areas: **posting** and **candidate background**. Both are required — the Analyze button stays disabled until both are filled, since Stage 2 (the actual insight-generation) needs both to produce anything meaningful. Extraction alone isn't the deliverable.
- "Analyze" button runs the pipeline synchronously.
- Results rendered with **visible** traceability: each requirement shows its `source_quote`; each strength/gap shows the `source_quote`(s) it's grounded in (e.g. a "Why:" caption). Any dropped items from §3 are shown as a warning banner, not hidden.

---

## 5. Deferred: evaluation harness (Phase 1)

Not built in Phase 0, but the design is settled so Phase 1 is a straightforward next step, not a fresh design exercise:
- Reference set: raw posting text files + hand-labeled JSON using the same `Posting` schema Stage 1 produces.
- Matching predicted vs. reference requirements: embedding similarity (local `sentence-transformers` model) with a similarity threshold, since exact wording won't match.
- Metrics: requirement-finding precision/recall, required/preferred/unclear category accuracy (confusion matrix), grounding accuracy (the same substring check from §3, now measured as a percentage across the reference set instead of used to filter live results).
- This is deferred specifically because it only produces meaningful numbers once there's a working Stage 1/Stage 2 baseline to measure — building it first would mean measuring an unproven pipeline.

---

## 6. Deferred: everything else (Phase 2+)

- **Generic posting-only insights** (what to emphasize, interview-gap topics, prep topics — independent of a candidate's background): this was Phase 0's original "Stage 2" in the first design pass. Demoted because, per the core hypothesis above, insights without a candidate background to compare against aren't the real value.
- **Batch mode:** the pipeline is already pure functions over one posting — batch mode is "call it N times + add an aggregation module," no core rewrite.
- **Agentic capability (goal 3 from the source doc):** doesn't make sense before the extraction pipeline is proven reliable (needs Phase 1's numbers first). Stage 1's `Requirement` schema can grow a `confidence` field later; low confidence would trigger a tool-use loop before finalizing — additive, not a schema break.
- **Automated checks / CI:** unit tests already exist per-task via TDD practice (this is how the code gets built, not a separate feature) — but the *CI workflow file* is deferred since it's inert with no GitHub remote to run against yet.
- **Deployment:** leading option is Streamlit Community Cloud (or Hugging Face Spaces) — purpose-built for a Streamlit app + secrets-managed API key. A static-frontend/GitHub-Pages split was considered and rejected: GitHub Pages only serves static files, this app needs a live server-side process for real-time Claude API calls, and exposing the API key client-side would be a security risk.
- **Writeup:** last, once there's something real (working app + Phase 1's numbers) to write about.

---

## Verification (Phase 0)

- `pytest` passes locally, including a test that an ungrounded requirement is dropped (not raised) and the rest of extraction still succeeds, and a test that an insight citing an unknown id is dropped (not raised) and the rest of analysis still succeeds.
- Manual smoke test: run `streamlit run job_scanner/app.py`, paste a real posting and real (or informal) background text, confirm strengths/gaps render with visible source-quote traceability, and confirm the app still renders a usable result even if one item fails verification (a warning shown, not a crash).

---

## Next step

Turn this into a step-by-step implementation plan via the `writing-plans` skill: scaffolding → shared models → validation utilities → LLM client → Stage 1 extraction (with item-level filtering) → Stage 2 analysis (with item-level filtering) → Streamlit UI.
