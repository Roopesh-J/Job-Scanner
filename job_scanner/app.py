import os

import streamlit as st

from job_scanner.analysis.analyzer import analyze_fit
from job_scanner.extraction.extractor import extract_posting
from job_scanner.llm.client import LLMClient
from job_scanner.models import InsightKind
from job_scanner.ui_helpers import build_id_lookup, format_sources

st.set_page_config(page_title="Job Scanner", layout="wide")
st.title("Job Scanner")

posting_text = st.text_area("Job posting", height=250)
candidate_text = st.text_area("Your background (resume, experience, notes — any plain text)", height=200)

can_analyze = bool(posting_text.strip()) and bool(candidate_text.strip())

if st.button("Analyze", disabled=not can_analyze):
    client = LLMClient(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    with st.spinner("Extracting posting..."):
        extraction = extract_posting(posting_text, client)

    posting = extraction.posting
    id_lookup = build_id_lookup(posting)

    st.subheader(f"{posting.title} — {posting.company}")
    st.caption(f"{posting.location} · {posting.seniority}")

    if extraction.dropped_ids:
        st.warning(f"{len(extraction.dropped_ids)} item(s) couldn't be verified against the posting and were excluded.")

    st.subheader("Responsibilities")
    for resp in posting.responsibilities:
        st.markdown(f"- {resp.text}")
        st.caption(f"Source: {format_sources([resp.id], id_lookup)}")

    st.subheader("Requirements")
    for req in posting.requirements:
        st.markdown(f"**[{req.category.value}]** {req.text}")
        st.caption(f"Source: {format_sources([req.id], id_lookup)}")

    with st.spinner("Analyzing fit..."):
        analysis = analyze_fit(posting, candidate_text, client)

    if analysis.dropped_count:
        st.warning(f"{analysis.dropped_count} insight(s) couldn't be verified and were excluded.")

    strengths = [i for i in analysis.insights if i.kind == InsightKind.STRENGTH]
    gaps = [i for i in analysis.insights if i.kind == InsightKind.GAP]

    st.subheader("Strengths")
    for insight in strengths:
        st.markdown(f"- {insight.text}")
        sources = format_sources(insight.supporting_requirement_ids, id_lookup)
        if sources:
            st.caption(f"Why: {sources}")

    st.subheader("Gaps")
    for insight in gaps:
        st.markdown(f"- {insight.text}")
        sources = format_sources(insight.supporting_requirement_ids, id_lookup)
        if sources:
            st.caption(f"Why: {sources}")
