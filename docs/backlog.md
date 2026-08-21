# Backlog

Ideas discussed but not yet spec'd or built. Not a commitment, just a running list so nothing gets lost between sessions.

## Impact-ranked gap list

Extend recurring gaps into a prioritized "fix this first" ranking — score each recurring gap by how many postings closing it would flip to a better verdict (stretch/weak → strong), computed across the whole batch. Builds directly on `job_scanner/patterns.py`. No new infrastructure needed.

Discussed 2026-08-21.

## Posting clustering (embeddings)

Group the batch's postings into role-flavor buckets (e.g. "backend-heavy" vs "full-stack") so results show where the candidate's strength actually concentrates, not just per-posting fit.

Explicitly deferred in `docs/superpowers/specs/2026-08-19-gap-patterns-design.md` — needs new infrastructure (LLM categorization or embeddings) and has a weaker traceability story than the rest of the app (no clean source-quote citation for "this posting is backend-heavy").

## Evaluation harness (embeddings-based matching)

Fully designed but never built: `docs/superpowers/specs/2026-07-23-job-scanner-phase1-eval-design.md`. Scores Stage 1 extraction (requirements/responsibilities found vs. missed vs. hallucinated) against a hand-labeled reference set of 5 real postings, matching predicted vs. reference items via local `sentence-transformers` (`all-MiniLM-L6-v2`) cosine similarity rather than exact-string matching.

This is likely "the semantic embeddings idea" from a prior session — the design doc even specifies the model and matching approach in detail. The project's own build plan (`job-scanner-build-plan.md`, goal 2) calls evaluation the single highest-leverage next step, worth doing before anything flashy. It was fully designed before the recurring-gaps feature, but the feature work happened first instead.
