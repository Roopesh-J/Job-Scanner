import html
import os
import sys

import anthropic
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

from job_scanner.analyzer import analyze_fit
from job_scanner.extractor import extract_posting, is_url
from job_scanner.llm_client import LLMClient
from job_scanner.models import Category, InsightKind, Verdict
from job_scanner.ui_helpers import (
    CITATION_SCROLL_JS,
    GLOBAL_CSS,
    HERO_HTML,
    HOW_TO_HTML,
    build_id_lookup,
    build_meta_line,
    build_tab_label,
    cite_targets,
    citation_hover_css,
    format_search_actions,
    highlight_quotes_with_ids,
    ranking_key,
    verdict_label,
)

load_dotenv()

st.set_page_config(page_title="JobScan", layout="wide")
st.markdown(GLOBAL_CSS, unsafe_allow_html=True)
components.html(CITATION_SCROLL_JS, height=0)

if "stage" not in st.session_state:
    st.session_state.stage = "input"
if "posting_ids" not in st.session_state:
    st.session_state.posting_ids = [0]
    st.session_state.next_posting_id = 1
if "results" not in st.session_state:
    st.session_state.results = []
if "errors" not in st.session_state:
    st.session_state.errors = []
if "active_tab" not in st.session_state:
    st.session_state.active_tab = 0
if "analyzing" not in st.session_state:
    st.session_state.analyzing = False


def render_input_stage() -> None:
    if os.environ.get("JOBSCAN_DEV_DATA") == "1" and st.button("⚡ Load sample results (dev)", key="dev_load_sample"):
        from job_scanner.dev_data import sample_results

        results, errors = sample_results()
        st.session_state.results = results
        st.session_state.errors = errors
        st.session_state.active_tab = 0
        st.session_state.stage = "results"
        st.rerun()

    st.markdown(HERO_HTML, unsafe_allow_html=True)
    st.markdown('<hr class="divider-rule">', unsafe_allow_html=True)

    how_to_col, form_col = st.columns([1, 2.2], gap="large")

    with how_to_col:
        st.markdown(HOW_TO_HTML, unsafe_allow_html=True)

    with form_col:
        st.markdown('<span class="field-label">Your background</span>', unsafe_allow_html=True)
        candidate_text = st.text_area(
            "Your background", height=110, label_visibility="collapsed", key="candidate_text"
        )

        st.markdown('<span class="field-label">Postings</span>', unsafe_allow_html=True)
        posting_inputs_raw = []
        posting_ids = st.session_state.posting_ids
        for display_index, pid in enumerate(list(posting_ids)):
            with st.container(key=f"posting_wrap_{pid}"):
                posting_inputs_raw.append(
                    st.text_area(
                        f"Posting {display_index + 1}",
                        height=90,
                        label_visibility="collapsed",
                        key=f"posting_{pid}",
                    )
                )
                if len(posting_ids) > 1 and st.button(
                    "×", key=f"remove_{pid}", help=f"Remove posting {display_index + 1}"
                ):
                    posting_ids.remove(pid)
                    st.rerun()

        if st.button("+ Add another posting", key="add_posting"):
            posting_ids.append(st.session_state.next_posting_id)
            st.session_state.next_posting_id += 1
            st.rerun()

        posting_inputs = [
            (display_index + 1, p.strip()) for display_index, p in enumerate(posting_inputs_raw) if p.strip()
        ]
        can_analyze = bool(posting_inputs) and bool(candidate_text.strip())

        analyze_clicked = st.button(
            "Analyze", key="analyze_btn", disabled=not can_analyze or st.session_state.analyzing
        )
        if analyze_clicked:
            st.session_state.analyzing = True
            st.rerun()

        if st.session_state.analyzing:
            run_analysis(candidate_text, posting_inputs)


# Unambiguous account/connection-level failures — retrying identically for every remaining
# posting just burns time and quota, so these abort the rest of the batch instead. Excludes
# APITimeoutError even though it subclasses APIConnectionError: a single slow request timing
# out says nothing about whether the rest of the batch would fail too, unlike an auth/rate-limit/
# connection problem.
_SYSTEMIC_ERRORS = (anthropic.AuthenticationError, anthropic.RateLimitError, anthropic.APIConnectionError)


def _is_systemic(e: Exception) -> bool:
    return isinstance(e, _SYSTEMIC_ERRORS) and not isinstance(e, anthropic.APITimeoutError)


_PROCESSING_ERROR_MESSAGE = "There was an error while running one or more of the postings. Please try again in some time."


def _fail_remaining(posting_inputs: list[tuple[int, str]], from_index: int, errors: list[tuple[int, str]]) -> None:
    for display_number, _ in posting_inputs[from_index:]:
        errors.append((display_number, _PROCESSING_ERROR_MESSAGE))


def run_analysis(candidate_text: str, posting_inputs: list[tuple[int, str]]) -> None:
    try:
        client = LLMClient()
    except Exception as e:
        st.session_state.analyzing = False
        st.error(f"Couldn't set up the Claude client: {e}")
        return

    results = []
    errors = []

    for progress_index, (display_number, raw_input) in enumerate(posting_inputs, start=1):
        with st.spinner(f"Processing posting {display_number} ({progress_index} of {len(posting_inputs)})..."):
            try:
                posting_text = client.fetch_url_text(raw_input) if is_url(raw_input) else raw_input
            except Exception as e:
                if _is_systemic(e):
                    print(f"Posting {display_number} fetch failed (systemic, aborting batch): {e!r}", file=sys.stderr)
                    _fail_remaining(posting_inputs, progress_index - 1, errors)
                    break
                print(f"Posting {display_number} fetch failed: {e!r}", file=sys.stderr)
                errors.append((display_number, "Could not fetch URL. Try pasting in the posting text directly instead."))
                continue

            try:
                extraction = extract_posting(posting_text, client)
                analysis = analyze_fit(extraction.posting, candidate_text, client)
            except Exception as e:
                if _is_systemic(e):
                    print(f"Posting {display_number} failed (systemic, aborting batch): {e!r}", file=sys.stderr)
                    _fail_remaining(posting_inputs, progress_index - 1, errors)
                    break
                print(f"Posting {display_number} failed: {e!r}", file=sys.stderr)
                errors.append((display_number, _PROCESSING_ERROR_MESSAGE))
                continue

            results.append({"posting_text": posting_text, "extraction": extraction, "analysis": analysis})

    results.sort(key=lambda r: ranking_key(r["analysis"].verdict, r["analysis"].insights))

    st.session_state.results = results
    st.session_state.errors = errors
    st.session_state.active_tab = 0
    st.session_state.stage = "results"
    st.session_state.analyzing = False
    st.rerun()


def render_results_stage() -> None:
    results = st.session_state.results

    with st.container(key="results_topbar"):
        top_bar_col, back_col = st.columns([5, 1])
        with top_bar_col:
            st.markdown(
                '<div class="brand"><span class="wordmark">JobScan</span>'
                '<span class="credit">Made by RoopeshJ</span></div>',
                unsafe_allow_html=True,
            )
        with back_col:
            if st.button("← New analysis", key="back_btn"):
                st.session_state.stage = "input"
                st.session_state.analyzing = False
                st.rerun()

    for posting_number, error in st.session_state.errors:
        st.error(f"Posting {posting_number}: {error}")

    if not results:
        st.info("No postings could be analyzed. Go back and try again.")
        return

    strong_count = sum(1 for r in results if r["analysis"].verdict == Verdict.STRONG_MATCH)
    stretch_count = sum(1 for r in results if r["analysis"].verdict == Verdict.STRETCH)
    weak_count = sum(1 for r in results if r["analysis"].verdict == Verdict.WEAK_FIT)

    st.markdown(
        f"""
        <div class="results-intro">
          <h2>Results ranked by fit</h2>
          <div class="stat-row">
            <div class="stat-tile strong"><span class="num">{strong_count}</span><span class="cap">Strong fits</span></div>
            <div class="stat-tile stretch"><span class="num">{stretch_count}</span><span class="cap">Stretches</span></div>
            <div class="stat-tile weak"><span class="num">{weak_count}</span><span class="cap">Weak fits</span></div>
            <div class="stat-tile"><span class="num">{len(results)}</span><span class="cap">Postings analyzed</span></div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.container(key="posting_tabs"):
        tab_cols = st.columns(len(results), gap="small")
        for i, (col, r) in enumerate(zip(tab_cols, results)):
            posting = r["extraction"].posting
            verdict = r["analysis"].verdict
            is_active = i == st.session_state.active_tab
            label = build_tab_label(posting)
            key = f"tab_{verdict.value}_{i}"
            with col:
                if st.button(label, key=key, type="primary" if is_active else "secondary"):
                    st.session_state.active_tab = i
                    st.rerun()

    st.markdown('<hr class="divider-rule ribbon-divider">', unsafe_allow_html=True)

    active = results[st.session_state.active_tab]
    render_posting_detail(active)


def render_posting_detail(result: dict) -> None:
    extraction = result["extraction"]
    analysis = result["analysis"]
    posting = extraction.posting

    strengths = [i for i in analysis.insights if i.kind == InsightKind.STRENGTH]
    gaps = [i for i in analysis.insights if i.kind == InsightKind.GAP]
    id_lookup = build_id_lookup(posting)

    def render_insight(insight, kind: str) -> str:
        targets = cite_targets(insight.supporting_ids, id_lookup)
        cite_attr = f' data-cite-target="{targets}" tabindex="0"' if targets else ""
        return f'<li class="insight-card {kind}"{cite_attr}>{html.escape(insight.text)}</li>'

    strength_items = "".join(render_insight(s, "strength") for s in strengths)
    if not strength_items:
        strength_items = '<li class="insight-card muted">None identified.</li>'
    gap_items = "".join(render_insight(g, "gap") for g in gaps)
    if not gap_items:
        gap_items = '<li class="insight-card muted">None identified.</li>'

    cite_ids = {sid for insight in analysis.insights for sid in insight.supporting_ids if sid in id_lookup}
    hover_css = citation_hover_css(cite_ids)
    rail_html = highlight_quotes_with_ids(result["posting_text"], id_lookup)

    if hover_css:
        st.markdown(hover_css, unsafe_allow_html=True)

    st.markdown(
        f"""
        <div class="detail-head">
          <span class="verdict-badge {analysis.verdict.value}">{verdict_label(analysis.verdict)}</span>
          <div class="title-row">
            <h2>{html.escape(posting.title)}</h2>
            <span class="company-name">{html.escape(posting.company)}</span>
          </div>
          <div class="posting-meta">{build_meta_line(posting)}</div>
        </div>
        <p class="posting-summary"><strong>Summary:</strong> {html.escape(analysis.summary)}</p>
        """,
        unsafe_allow_html=True,
    )

    detail_col, rail_col = st.columns([1.5, 1])
    with detail_col:
        st.markdown(
            f"""
            <div class="insight-cols">
              <div class="insight-group strengths"><h4>Strengths</h4><ul class="insight-list">{strength_items}</ul></div>
              <div class="insight-group gaps"><h4>Gaps</h4><ul class="insight-list">{gap_items}</ul></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown('<hr class="extras-divider">', unsafe_allow_html=True)

        if extraction.dropped_ids:
            st.caption(f"Note: {len(extraction.dropped_ids)} extracted item(s) couldn't be verified and were excluded.")
        if analysis.dropped_count:
            st.caption(f"Note: {analysis.dropped_count} insight(s) couldn't be verified and were excluded.")

        if analysis.search_actions:
            with st.expander("Verified externally"):
                for line in format_search_actions(analysis.search_actions):
                    st.markdown(f"- {line}")

        with st.expander("View extracted posting details"):
            st.markdown("**Responsibilities**")
            st.markdown("\n".join(f"- {resp.text}" for resp in posting.responsibilities))
            for category in Category:
                items = [req for req in posting.requirements if req.category == category]
                if not items:
                    continue
                st.markdown(f"**{category.value.capitalize()}**")
                st.markdown("\n".join(f"- {req.text}" for req in items))

    with rail_col:
        st.markdown(
            f"""
            <div class="evidence-rail">
              <div class="rail-header">Source posting</div>
              <div class="rail-scroll">{rail_html}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


if st.session_state.stage == "input":
    render_input_stage()
else:
    render_results_stage()
