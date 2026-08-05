import streamlit as st
from dotenv import load_dotenv

from job_scanner.analyzer import analyze_fit
from job_scanner.extractor import extract_posting, is_url
from job_scanner.llm_client import LLMClient
from job_scanner.models import InsightKind
from job_scanner.ui_helpers import build_id_lookup, format_search_actions, format_sources

load_dotenv()

st.set_page_config(page_title="Job Scanner", layout="wide")
st.title("Job Scanner")

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


def render_posting_detail(extraction, analysis) -> None:
    posting = extraction.posting
    id_lookup = build_id_lookup(posting)

    location_line = f"{posting.location} · {posting.seniority}"
    if posting.salary:
        escaped_salary = posting.salary.replace("$", "\\$")
        location_line += f" · {escaped_salary}"
    st.caption(location_line)

    if extraction.dropped_ids:
        st.warning(
            f"{len(extraction.dropped_ids)} item(s) couldn't be verified against the posting and were excluded."
        )

    st.markdown("**Responsibilities**")
    for resp in posting.responsibilities:
        st.markdown(f"- {resp.text}")
        st.caption(f"Source: {format_sources([resp.id], id_lookup)}")

    st.markdown("**Requirements**")
    for req in posting.requirements:
        st.markdown(f"**[{req.category.value}]** {req.text}")
        st.caption(f"Source: {format_sources([req.id], id_lookup)}")

    if analysis.dropped_count:
        st.warning(f"{analysis.dropped_count} insight(s) couldn't be verified and were excluded.")

    if analysis.search_actions:
        with st.expander("Claude looked something up while analyzing"):
            for line in format_search_actions(analysis.search_actions):
                st.markdown(f"- {line}")

    strengths = [i for i in analysis.insights if i.kind == InsightKind.STRENGTH]
    gaps = [i for i in analysis.insights if i.kind == InsightKind.GAP]

    st.markdown("**Strengths**")
    for insight in strengths:
        st.markdown(f"- {insight.text}")
        sources = format_sources(insight.supporting_ids, id_lookup)
        if sources:
            st.caption(f"Why: {sources}")

    st.markdown("**Gaps**")
    for insight in gaps:
        st.markdown(f"- {insight.text}")
        sources = format_sources(insight.supporting_ids, id_lookup)
        if sources:
            st.caption(f"Why: {sources}")


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
            results.append((fit_score, extraction, analysis))
        except Exception as e:
            errors.append((i + 1, str(e)))

    results.sort(key=lambda r: r[0], reverse=True)

    for fit_score, extraction, analysis in results:
        posting = extraction.posting
        with st.expander(f"{posting.title} — {posting.company} (fit: {fit_score:+d})", expanded=len(results) == 1):
            render_posting_detail(extraction, analysis)

    for posting_number, error in errors:
        st.error(f"Posting {posting_number}: something went wrong — {error}")
