import streamlit as st
from dotenv import load_dotenv

from job_scanner.analyzer import analyze_fit
from job_scanner.extractor import extract_posting, is_url
from job_scanner.llm_client import LLMClient
from job_scanner.models import InsightKind
from job_scanner.ui_helpers import (
    CHECK_ICON_SVG,
    GAP_COLOR,
    GLOBAL_CSS,
    STRENGTH_COLOR,
    WARNING_ICON_SVG,
    build_id_lookup,
    format_badge_counts,
    format_search_actions,
    format_sources,
    section_heading,
)

load_dotenv()

st.set_page_config(page_title="Job Scanner", layout="wide")
st.markdown(GLOBAL_CSS, unsafe_allow_html=True)
st.title("Job Scanner")
st.caption("See exactly how your background matches a posting — and where it falls short.")

candidate_text = st.text_area("Your background (resume, experience, notes — any plain text)", height=200)

if "posting_count" not in st.session_state:
    st.session_state.posting_count = 1

st.subheader("Job postings")
posting_inputs_raw = [
    st.text_area(f"Posting {i + 1} (paste text or a URL)", key=f"posting_{i}", height=150)
    for i in range(st.session_state.posting_count)
]

if st.button("+ Add another posting"):
    st.session_state.posting_count += 1
    st.rerun()

posting_inputs = [p.strip() for p in posting_inputs_raw if p.strip()]
can_analyze = bool(posting_inputs) and bool(candidate_text.strip())


def render_insight_row(insight, id_lookup, kind_prefix: str) -> None:
    with st.container(key=f"{kind_prefix}_{insight.id}"):
        text_col, source_col = st.columns([6, 1])
        with text_col:
            st.markdown(insight.text)
        with source_col:
            sources = format_sources(insight.supporting_ids, id_lookup)
            if sources:
                with st.popover("source", use_container_width=False, key=f"source_{insight.id}"):
                    st.markdown(sources)


def render_posting_detail(extraction, analysis) -> None:
    posting = extraction.posting
    id_lookup = build_id_lookup(posting)

    location_line = f"{posting.location} · {posting.seniority}"
    if posting.salary:
        escaped_salary = posting.salary.replace("$", "\\$")
        location_line += f" · {escaped_salary}"
    st.caption(location_line)

    strengths = [i for i in analysis.insights if i.kind == InsightKind.STRENGTH]
    gaps = [i for i in analysis.insights if i.kind == InsightKind.GAP]

    strength_col, gap_col = st.columns(2)
    with strength_col:
        st.markdown(section_heading("Strengths", CHECK_ICON_SVG, STRENGTH_COLOR), unsafe_allow_html=True)
        if not strengths:
            st.caption("None identified.")
        for insight in strengths:
            render_insight_row(insight, id_lookup, "strength")

    with gap_col:
        st.markdown(section_heading("Gaps", WARNING_ICON_SVG, GAP_COLOR), unsafe_allow_html=True)
        if not gaps:
            st.caption("None identified.")
        for insight in gaps:
            render_insight_row(insight, id_lookup, "gap")

    if extraction.dropped_ids:
        st.caption(f"Note: {len(extraction.dropped_ids)} extracted item(s) couldn't be verified and were excluded.")
    if analysis.dropped_count:
        st.caption(f"Note: {analysis.dropped_count} insight(s) couldn't be verified and were excluded.")

    if analysis.search_actions:
        with st.expander("Claude looked something up while analyzing"):
            for line in format_search_actions(analysis.search_actions):
                st.markdown(f"- {line}")

    with st.expander("View extracted posting details"):
        st.markdown("**Responsibilities**")
        for resp in posting.responsibilities:
            st.markdown(f"- {resp.text}")
            st.caption(f"Source: {format_sources([resp.id], id_lookup)}")

        st.markdown("**Requirements**")
        for req in posting.requirements:
            st.markdown(f"**[{req.category.value}]** {req.text}")
            st.caption(f"Source: {format_sources([req.id], id_lookup)}")


if st.button("Analyze", disabled=not can_analyze):
    try:
        client = LLMClient()
    except Exception as e:
        st.error(f"Couldn't set up the Claude client: {e}")
        st.stop()

    results = []
    errors = []

    for i, raw_input in enumerate(posting_inputs):
        try:
            with st.spinner(f"Processing posting {i + 1} of {len(posting_inputs)}..."):
                posting_text = client.fetch_url_text(raw_input) if is_url(raw_input) else raw_input
                extraction = extract_posting(posting_text, client)
                analysis = analyze_fit(extraction.posting, candidate_text, client)
            strength_count = sum(1 for insight in analysis.insights if insight.kind == InsightKind.STRENGTH)
            gap_count = sum(1 for insight in analysis.insights if insight.kind == InsightKind.GAP)
            fit_score = strength_count - gap_count
            results.append((fit_score, strength_count, gap_count, extraction, analysis))
        except Exception as e:
            errors.append((i + 1, str(e)))

    results.sort(key=lambda r: r[0], reverse=True)

    for fit_score, strength_count, gap_count, extraction, analysis in results:
        posting = extraction.posting
        label = f"{posting.title} — {posting.company} · {format_badge_counts(strength_count, gap_count)}"
        with st.expander(label, expanded=len(results) == 1):
            render_posting_detail(extraction, analysis)

    for posting_number, error in errors:
        st.error(f"Posting {posting_number}: something went wrong — {error}")
