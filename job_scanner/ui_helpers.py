import html
import re

from job_scanner.models import Insight, InsightKind, Posting, SearchAction, Verdict

_SAFE_ID = re.compile(r"[^A-Za-z0-9_-]")


def _safe_id(raw_id: str) -> str:
    return _SAFE_ID.sub("", raw_id)

STRENGTH_COLOR = "#57B98C"
GAP_COLOR = "#D97757"
GAP_DEEP_COLOR = "#E5484D"
VERIFIED_COLOR = "#6C9CE8"
STRETCH_COLOR = "#E0B23C"

_VERDICT_LABELS = {
    Verdict.STRONG_MATCH: "Strong fit",
    Verdict.STRETCH: "Stretch",
    Verdict.WEAK_FIT: "Weak fit",
}
_VERDICT_RANK = {
    Verdict.STRONG_MATCH: 0,
    Verdict.STRETCH: 1,
    Verdict.WEAK_FIT: 2,
}


def fit_counts(insights: list[Insight]) -> tuple[int, int]:
    strengths = sum(1 for i in insights if i.kind == InsightKind.STRENGTH)
    gaps = sum(1 for i in insights if i.kind == InsightKind.GAP)
    return strengths, gaps


def ranking_key(verdict: Verdict, insights: list[Insight]) -> tuple[int, int]:
    strengths, gaps = fit_counts(insights)
    return (_VERDICT_RANK[verdict], -(strengths - gaps))


def verdict_label(verdict: Verdict) -> str:
    return _VERDICT_LABELS[verdict]


def build_id_lookup(posting: Posting) -> dict[str, str]:
    lookup = {r.id: r.source_quote for r in posting.responsibilities}
    lookup.update({r.id: r.source_quote for r in posting.requirements})
    return lookup


def highlight_quotes_with_ids(text: str, id_lookup: dict[str, str]) -> str:
    escaped = html.escape(text)
    ids_by_quote: dict[str, list[str]] = {}
    for cite_id, quote in id_lookup.items():
        if not quote:
            continue
        ids_by_quote.setdefault(quote, []).append(cite_id)

    # Find every occurrence of every quote in the pristine escaped text (no sequential
    # str.replace() mutation, which would re-match text already inside a just-inserted <mark>).
    # Then merge overlapping spans — full containment, partial overlap, or duplicates — into one
    # <mark> with the union of their citation ids, so no quote's citation is ever silently
    # dropped just because its span overlaps another quote's.
    raw_spans: list[tuple[int, int, list[str]]] = []
    for quote, cite_ids in ids_by_quote.items():
        escaped_quote = html.escape(quote)
        if not escaped_quote:
            continue
        search_from = 0
        while (idx := escaped.find(escaped_quote, search_from)) != -1:
            raw_spans.append((idx, idx + len(escaped_quote), cite_ids))
            search_from = idx + 1

    raw_spans.sort(key=lambda s: s[0])
    merged: list[list] = []  # each: [start, end, [cite_ids]]
    for start, end, cite_ids in raw_spans:
        if merged and start < merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
            merged[-1][2].extend(cite_ids)
        else:
            merged.append([start, end, list(cite_ids)])

    pieces = []
    cursor = 0
    for start, end, cite_ids in merged:
        safe_ids = " ".join(dict.fromkeys(_safe_id(cid) for cid in cite_ids))
        pieces.append(escaped[cursor:start])
        pieces.append(f'<mark data-cite-id="{safe_ids}">{escaped[start:end]}</mark>')
        cursor = end
    pieces.append(escaped[cursor:])
    return "".join(pieces)


def cite_targets(supporting_ids: list[str], id_lookup: dict[str, str]) -> str:
    return " ".join(_safe_id(sid) for sid in supporting_ids if sid in id_lookup)


def citation_hover_css(cite_ids: set[str]) -> str:
    if not cite_ids:
        return ""
    rules = [
        f'div[data-testid="stHorizontalBlock"]:has([data-cite-target~="{cid}"]:hover) mark[data-cite-id~="{cid}"],\n'
        f'div[data-testid="stHorizontalBlock"]:has([data-cite-target~="{cid}"]:focus-visible) mark[data-cite-id~="{cid}"] '
        "{ background: rgba(108, 156, 232, 0.28); color: var(--ink); }"
        for cid in sorted({_safe_id(cid) for cid in cite_ids} - {""})
    ]
    return "<style>\n" + "\n".join(rules) + "\n</style>"


_SALARY_NUMBER = re.compile(r"\$?\s?(\d[\d,]*(?:\.\d+)?)\s?([kK])?")
_SALARY_RATE = re.compile(r"(?:/|\bper)\s?(hr|hour|yr|year|wk|week|mo|month)\b", re.IGNORECASE)


def format_salary(raw: str) -> str:
    numbers = []
    for digits, k_suffix in _SALARY_NUMBER.findall(raw):
        cleaned = digits.replace(",", "")
        if not cleaned:
            continue
        value = float(cleaned)
        if k_suffix:
            value *= 1000
        numbers.append(value)

    if not numbers:
        return raw

    formatted = " - ".join(f"${value:,.0f}" for value in numbers[:2])

    rate_match = _SALARY_RATE.search(raw)
    if rate_match:
        formatted += f"/{rate_match.group(1).lower()}"

    return formatted


def build_meta_line(posting: Posting) -> str:
    parts = [
        posting.location or "Location not listed",
        format_salary(posting.salary) if posting.salary else "Salary not listed",
        posting.seniority or "Level not listed",
    ]
    return "".join(f"<span>{html.escape(p)}</span>" for p in parts)


_MD_SPECIAL = re.compile(r"([\\`*_~\[\]$])")


def _escape_markdown_text(text: str) -> str:
    """Neutralize Streamlit markdown syntax (bold/code/color directives) so LLM- or web-sourced
    text renders literally — Streamlit renders through its own markdown parser, not raw HTML, so
    html.escape() would be the wrong kind of escaping here."""
    return _MD_SPECIAL.sub(r"\\\1", text.replace("\n", " "))


def _escape_code_text(text: str) -> str:
    """Backslash escapes don't apply inside markdown code spans, so the only character that can
    break out is a literal backtick (it would prematurely close the span) — drop it instead."""
    return text.replace("\n", " ").replace("`", "'")


def build_tab_label(posting: Posting) -> str:
    title = _escape_markdown_text(posting.title)
    company = _escape_code_text(posting.company)
    return f"**{title}**`{company}`"


def format_search_actions(search_actions: list[SearchAction]) -> list[str]:
    lines = []
    for action in search_actions:
        query = _escape_markdown_text(action.query)
        titles = ", ".join(_escape_markdown_text(r.title) for r in action.results) or "no results"
        lines.append(f"Searched “{query}” — found: {titles}")
    return lines


FONT_IMPORT = (
    "@import url('https://fonts.googleapis.com/css2?"
    "family=Spectral:wght@400;500;600&family=Public+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@500;600"
    "&display=swap');"
)

GLOBAL_CSS = f"""
<style>
{FONT_IMPORT}

:root {{
    --ground: #1E2227;
    --panel: #262B31;
    --panel-hi: #2C323A;
    --ink: #EDEBE3;
    --ink-soft: #C3C8CD;
    --ink-faint: #868C93;
    --line: #3A4048;
    --verified: {VERIFIED_COLOR};
    --strength: {STRENGTH_COLOR};
    --gap: {GAP_COLOR};
    --gap-deep: {GAP_DEEP_COLOR};
    --stretch: {STRETCH_COLOR};
    --focus: {VERIFIED_COLOR};
}}

html, body, [class*="st-key-"], .stApp {{
    font-family: 'Public Sans', -apple-system, sans-serif;
}}
.stApp {{ background: var(--ground); font-size: 17px; line-height: 1.6; }}
h1, h2, h3, h4, h5 {{ font-family: 'Spectral', Georgia, serif; font-weight: 600; text-wrap: balance; }}

::selection {{ background: var(--verified); color: var(--ground); }}
.stApp :focus-visible {{ outline: 2px solid var(--focus); outline-offset: 2px; }}
[data-testid="stHeaderActionElements"] {{ display: none !important; }}

.wordmark {{ font-family: 'Spectral', serif; font-weight: 600; font-size: 1.75rem; color: var(--ink); letter-spacing: -0.01em; }}
.brand {{ display: flex; align-items: baseline; gap: 0.8rem; }}
.credit {{ font-family: 'IBM Plex Mono', monospace; font-size: 0.88rem; letter-spacing: 0.03em; color: var(--ink-faint); }}
.brand-link {{ display: inline-flex; align-items: center; align-self: center; color: var(--ink-faint) !important;
    text-decoration: none !important; transition: color 0.15s ease; }}
.brand-link:hover, .brand-link:focus-visible {{ color: var(--verified) !important; }}
.brand-link svg {{ display: block; }}
div[class*="st-key-results_topbar"] {{ margin-bottom: -35px; }}
.field-label {{ font-family: 'Public Sans', sans-serif; font-weight: 600; font-size: 1.15rem; color: var(--ink); margin-bottom: 0.5rem; }}

.divider-rule {{ border: none; border-top: 1px solid var(--line); margin: 1.5rem 0; }}
.ribbon-divider {{ margin: 0.35rem 0 !important; }}

.hero {{ display: flex; gap: 2.75rem; align-items: center; flex-wrap: wrap; padding: 0.5rem 0 1.5rem; }}
.hero-copy {{ flex: 0.78 1 380px; }}
.hero-copy h1 {{ font-size: clamp(2.1rem, 4vw, 3.15rem); line-height: 1.08; letter-spacing: -0.01em; color: var(--ink); margin: 0.75rem 0 0.75rem; }}
.hero-copy p {{ font-size: 1.12rem; color: var(--ink); max-width: 48ch; margin: 0; }}

.thread-demo {{ flex: 1.22 1 420px; background: var(--panel); border: 1px solid var(--line); padding: 1.4rem 1.3rem; }}
.demo-label {{ font-size: 1.1rem; font-weight: 700; color: var(--ink); line-height: 1.4; margin-bottom: 1.1rem; }}
.demo-examples {{ display: grid; grid-template-columns: 1fr 1fr; column-gap: 1.5rem; row-gap: 0; align-items: start; }}
.demo-tag {{ display: block; font-family: 'IBM Plex Mono', monospace; font-size: 0.7rem; font-weight: 600;
    letter-spacing: 0.06em; text-transform: uppercase; padding: 0.4rem 0.6rem; margin-bottom: 0.7rem; }}
.demo-tag.strength {{ background: var(--strength); color: var(--ground); }}
.demo-tag.gap {{ background: var(--gap); color: var(--ground); }}
.demo-examples .claim {{ font-size: 0.98rem; color: var(--ink); margin-bottom: 0.2rem; }}
.demo-examples .svg-link {{ display: block; width: 20px; height: 24px; margin: 0.4rem auto; }}
.demo-examples .svg-link path {{ fill: none; stroke: var(--verified); stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; }}
.demo-examples .link-line {{ stroke-dasharray: 14; stroke-dashoffset: 14; animation: draw-line 0.5s 0.2s ease forwards; }}
.demo-examples .link-head {{ stroke-dasharray: 16; stroke-dashoffset: 16; opacity: 0; animation: draw-head 0.3s 0.7s ease forwards; }}
@media (prefers-reduced-motion: reduce) {{
    .demo-examples .link-line, .demo-examples .link-head {{ animation: none; stroke-dashoffset: 0; opacity: 1; }}
}}
@keyframes draw-line {{ to {{ stroke-dashoffset: 0; }} }}
@keyframes draw-head {{ to {{ stroke-dashoffset: 0; opacity: 1; }} }}
.demo-examples .quote {{ font-size: 0.94rem; color: var(--ink); margin-top: 0.2rem; }}
.demo-examples .quote mark {{ background: none; color: var(--verified); font-weight: 500; }}

.how-to {{ padding-top: 0.25rem; }}
.how-steps {{ list-style: none; margin: 1rem 0 0; padding: 0; display: flex; flex-direction: column; gap: 1.4rem; counter-reset: step; }}
.how-steps li {{ position: relative; padding-left: 1.9rem; font-size: 1.12rem; font-weight: 400; color: var(--ink); line-height: 1.5; counter-increment: step; }}
.how-steps li::before {{ content: counter(step); position: absolute; left: 0; top: 0.15rem; font-family: 'IBM Plex Mono', monospace;
    font-weight: 600; font-size: 0.85rem; color: var(--ink-faint); }}
.how-steps li strong {{ color: var(--ink); font-weight: 700; display: block; margin-bottom: 0.15rem; }}

div[class*="st-key-analyze_btn"] button {{
    font-family: 'Public Sans', sans-serif; font-weight: 700; font-size: 1.4rem; letter-spacing: 0.01em;
    background: #FFFFFF; color: var(--ground); border: none; padding: 1.2rem 2.4rem;
}}
div[class*="st-key-analyze_btn"] button:hover:not(:disabled) {{ background: var(--verified); color: var(--ground); }}
div[class*="st-key-analyze_btn"] button:disabled {{
    background: var(--panel); color: var(--ink-faint); border: 1px solid var(--line); cursor: not-allowed;
}}
div[class*="st-key-sample_btn"] {{ margin-top: 0.6rem; }}
div[class*="st-key-sample_btn"] button {{
    background: none; border: none; color: var(--verified); font-family: 'IBM Plex Mono', monospace;
    font-size: 0.85rem; padding: 0.3rem 0; text-decoration: underline;
    text-decoration-color: rgba(108, 156, 232, 0.35); text-underline-offset: 3px;
}}
div[class*="st-key-sample_btn"] button:hover {{ color: var(--ink); text-decoration-color: var(--ink); }}
div[class*="st-key-add_posting"] button {{
    font-family: 'IBM Plex Mono', monospace; font-size: 0.88rem;
    background: none; color: var(--verified); border: 1px dashed var(--line); width: 100%; text-align: left; padding: 0.55rem 0.9rem;
}}
div[class*="st-key-add_posting"] button:hover {{ border-color: var(--verified); }}
div[class*="st-key-posting_wrap_"] {{ position: relative; }}
div[class*="st-key-posting_wrap_"] div[class*="st-key-remove_"] {{
    position: absolute; top: 0.5rem; right: 0.5rem; z-index: 2; width: auto;
}}
div[class*="st-key-remove_"] button {{
    background: none; color: var(--ink-faint); border: none; font-size: 1.3rem; padding: 0.15rem 0.5rem;
}}
div[class*="st-key-remove_"] button:hover {{ color: var(--gap); }}
div[class*="st-key-back_btn"] {{ display: flex; justify-content: flex-end; width: 100%; }}
div[class*="st-key-back_btn"] button {{
    font-family: 'Public Sans', sans-serif; font-weight: 700; font-size: 1.4rem; letter-spacing: 0.01em;
    background: #FFFFFF; color: var(--ground); border: none; padding: 1.15rem 2.2rem; margin-left: auto;
}}
div[class*="st-key-back_btn"] button:hover {{ background: var(--verified); color: var(--ground); }}

.stTextArea textarea {{ background: var(--panel); color: var(--ink); border: 1px solid var(--line); font-size: 1.05rem; padding: 0.9rem 1rem; line-height: 1.55; }}
.stTextArea textarea:focus {{ border-color: var(--verified); }}

.results-intro {{ padding: 0.5rem 0 1.75rem; }}
.results-intro h2 {{ font-size: clamp(1.9rem, 3.2vw, 2.5rem); color: var(--ink); margin: 0.5rem 0 1rem;
    line-height: 1.12; max-width: 62ch; }}
.stat-row {{ display: flex; flex-wrap: wrap; gap: 1.75rem 2.25rem; margin-top: 1.5rem; }}
.stat-tile .num {{ font-family: 'IBM Plex Mono', monospace; font-weight: 600; font-size: 1.85rem; font-variant-numeric: tabular-nums; line-height: 1; }}
.stat-tile.strong .num {{ color: var(--strength); }}
.stat-tile.stretch .num {{ color: var(--stretch); }}
.stat-tile.weak .num {{ color: var(--gap); }}
.stat-tile.gaps .num {{ color: var(--gap-deep); }}
.stat-tile .cap {{ display: block; margin-top: 0.35rem; font-family: 'IBM Plex Mono', monospace; font-size: 0.72rem;
    letter-spacing: 0.06em; text-transform: uppercase; color: var(--ink-faint); }}

.recurring-gaps {{ padding: 0.5rem 0; margin-bottom: 0.5rem; }}
.recurring-gaps-heading {{ font-size: 2.3rem; color: var(--ink); margin: 0 0 0.5rem; }}
.recurring-gaps-blurb {{ color: var(--ink-soft); font-size: 1.05rem; margin: 0 0 1.5rem; max-width: 56ch; }}

.gap-pattern-row {{ padding: 0.9rem 0; }}
.gap-pattern-row:first-of-type {{ padding-top: 0; }}
.gap-pattern-row summary {{ cursor: pointer; list-style: none; }}
.gap-pattern-row summary::-webkit-details-marker {{ display: none; }}

.gap-pattern-heading {{ display: flex; align-items: baseline; gap: 0.65rem; flex-wrap: wrap; }}
.gap-pattern-heading::before {{
    content: "▸"; font-family: 'IBM Plex Mono', monospace; font-size: 0.68rem; color: var(--ink-faint);
    display: inline-block; transition: transform 0.15s ease, color 0.15s ease;
}}
.gap-pattern-row[open] .gap-pattern-heading::before {{ transform: rotate(90deg); }}
.gap-pattern-row:hover .gap-pattern-heading::before {{ color: var(--ink); }}
.gap-pattern-label {{ font-family: 'Spectral', Georgia, serif; font-weight: 600; font-size: 1.25rem; color: var(--ink); }}
.gap-pattern-count {{ font-style: italic; color: var(--ink-faint); font-size: 0.92rem; }}

.gap-detail-body {{ margin-top: 1rem; padding-left: 1.1rem; border-left: 1px solid var(--line); }}

.gap-posting-name {{ font-family: 'Spectral', Georgia, serif; font-weight: 600; font-size: 1rem; color: var(--ink);
    margin: 0 0 0.35rem; }}
.gap-posting-name:not(:first-child) {{ margin-top: 1.1rem; }}
.gap-posting-name .company {{ font-family: 'IBM Plex Mono', monospace; font-weight: 500; font-size: 0.8rem;
    color: var(--ink-faint); margin-left: 0.6rem; }}
.gap-quote {{ font-size: 0.98rem; color: var(--ink-soft); font-style: italic; line-height: 1.55; margin: 0; }}
.gap-quote.muted {{ font-style: normal; color: var(--ink-faint); }}

.select-prompt {{ border: 1px dashed var(--line); color: var(--ink-faint); font-size: 1.05rem;
    text-align: center; padding: 2.5rem 1rem; margin-bottom: 1.5rem; }}

div[class*="st-key-posting_tabs"] {{ margin-bottom: 0.5rem; }}
div[class*="st-key-posting_tabs"] div[data-testid="stHorizontalBlock"] {{
    flex-wrap: wrap; justify-content: flex-start; gap: 0.85rem;
}}
div[class*="st-key-posting_tabs"] div[data-testid="stColumn"] {{
    flex: 0 0 auto !important; width: auto !important;
}}

/* Title and company are each forced onto a single line (no wrap) and the chip's
   width auto-fits whichever is longer — since every chip has the exact same 3-row
   shape, they line up naturally without needing a height hack. overflow:hidden on
   the button is a hard backstop: nothing ever renders outside the chip's border. */
div[class*="st-key-tab_"] button {{
    width: fit-content; max-width: 26rem; overflow: hidden;
    text-align: left; white-space: pre; line-height: 1.45;
    background: var(--panel); border: 1px solid var(--line); border-top: 3px solid var(--line);
    border-radius: 0; padding: 0.9rem 1.15rem;
    font-family: 'IBM Plex Mono', monospace; font-size: 0.8rem; color: var(--ink-soft);
    transition: border-color 0.12s ease, background 0.12s ease;
}}
div[class*="st-key-tab_"] button strong {{
    display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
    margin-bottom: 0.1rem;
    font-family: 'Spectral', Georgia, serif; font-weight: 600; font-size: 1.1rem; color: var(--ink);
}}
div[class*="st-key-tab_"] button:hover {{
    border-left-color: var(--ink-soft); border-right-color: var(--ink-soft); border-bottom-color: var(--ink-soft);
}}
div[class*="st-key-tab_"] button[kind="primary"] {{ background: var(--panel-hi); }}

div[class*="st-key-tab_strong_match_"] button {{ border-top-color: var(--strength); }}
div[class*="st-key-tab_stretch_"] button {{ border-top-color: var(--stretch); }}
div[class*="st-key-tab_weak_fit_"] button {{ border-top-color: var(--gap); }}

/* Company name (`code` span in the label) — bigger, plain weight, sits tight under the title. */
div[class*="st-key-tab_"] button code {{
    display: inline-block; max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
    vertical-align: bottom; color: var(--ink-soft) !important; background: none !important; padding: 0 !important;
    border-radius: 0 !important; font-family: 'IBM Plex Mono', monospace; font-size: 0.92rem; font-weight: 500;
}}

.title-row {{ display: flex; align-items: baseline; justify-content: flex-start; flex-wrap: wrap; margin-bottom: 0.15rem; }}
.detail-head h2 {{ color: var(--ink); font-size: 2.3rem; margin: 0; }}
.company-name {{ font-weight: 400; font-size: 2.3rem; color: var(--ink-soft); }}
.company-name::before {{ content: "·"; margin: 0 0.6rem; color: var(--ink-faint); font-weight: 400; }}
.posting-meta {{ display: flex; flex-wrap: wrap; align-items: center; font-family: 'IBM Plex Mono', monospace;
    font-size: 0.92rem; color: var(--ink-soft); gap: 0.4rem 0; padding-top: 0.2rem; margin-bottom: 1rem; }}
.posting-meta span {{ padding-right: 1.1rem; margin-right: 1.1rem; border-right: 1px solid var(--line); }}
.posting-meta span:last-child {{ padding-right: 0; margin-right: 0; border-right: none; }}
.posting-summary {{ color: var(--ink); font-size: 1rem; line-height: 1.55; margin-bottom: 1rem; }}

.insight-cols {{ display: flex; gap: 2.5rem; flex-wrap: wrap; }}
.insight-group {{ flex: 1 1 260px; }}
.insight-group h4 {{ font-size: 1rem; font-family: 'IBM Plex Mono', monospace; text-transform: uppercase;
    letter-spacing: 0.06em; font-weight: 600; padding: 0.55rem 0.7rem; margin: 0 0 1rem; }}
.insight-group.strengths h4 {{ background: var(--strength); color: var(--ground); }}
.insight-group.gaps h4 {{ background: var(--gap); color: var(--ground); }}
.insight-list {{ list-style: none; margin: 0; padding: 0; }}
.insight-list .insight-card {{ font-size: 1.05rem; color: var(--ink); padding: 0.3rem 0.6rem; margin: 0 -0.6rem;
    border-bottom: 1px solid rgba(237, 235, 227, 0.08); line-height: 1.65; }}
.insight-card:last-child {{ border-bottom: none; }}
.insight-card.muted {{ color: var(--ink-faint); }}
.insight-card[data-cite-target] {{ cursor: pointer; }}
.insight-card[data-cite-target]:hover,
.insight-card[data-cite-target]:focus-visible {{ background: var(--panel); }}

.extras-divider {{ border: none; border-top: 1px solid var(--line); margin: 2rem 0 1.5rem; }}
div[data-testid="stExpander"] summary p,
div[data-testid="stExpander"] summary span {{ font-size: 1rem; }}

.evidence-rail {{
    position: sticky; top: 2rem; background: var(--panel); border: 1px solid var(--line);
    max-height: calc(100vh - 4rem); display: flex; flex-direction: column; overflow: hidden;
}}
.rail-header {{ padding: 0.9rem 1.15rem; border-bottom: 1px solid var(--line); background: var(--panel-hi);
    font-family: 'IBM Plex Mono', monospace; font-size: 0.88rem; font-weight: 700; letter-spacing: 0.08em;
    text-transform: uppercase; color: var(--ink); }}
.rail-scroll {{ padding: 1.1rem 1.15rem 1.5rem; overflow-y: auto; font-size: 1rem; color: var(--ink);
    line-height: 1.65; white-space: pre-wrap; }}
.rail-scroll mark {{
    background: none; color: inherit; font-weight: 500;
    text-decoration: underline; text-decoration-color: rgba(108, 156, 232, 0.35); text-underline-offset: 2px;
    transition: color 0.15s ease, background 0.15s ease, text-decoration-color 0.15s ease;
}}

.verdict-badge {{ display: inline-block; font-family: 'IBM Plex Mono', monospace; font-size: 0.8rem; font-weight: 700;
    letter-spacing: 0.06em; text-transform: uppercase; padding: 0.3rem 0.6rem; margin-bottom: 0.8rem; }}
.verdict-badge.strong_match {{ background: var(--strength); color: var(--ground); }}
.verdict-badge.stretch {{ background: var(--stretch); color: var(--ground); }}
.verdict-badge.weak_fit {{ background: var(--gap); color: var(--ground); }}

@media (max-width: 900px) {{
    .hero {{ flex-direction: column; }}
    .evidence-rail {{ position: static; max-height: none; }}
}}
</style>
"""

BRAND_LINKS_HTML = (
    '<a class="brand-link" href="https://github.com/Roopesh-J/Job-Scanner" target="_blank" '
    'rel="noopener noreferrer" aria-label="GitHub repository">'
    '<svg viewBox="0 0 16 16" width="18" height="18" fill="currentColor"><path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 '
    "2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-"
    "1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-"
    "3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27."
    "68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 "
    "3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0016 8c0-4.42-"
    '3.58-8-8-8z"/></svg></a>'
    '<a class="brand-link" href="https://www.linkedin.com/in/roopesh-jampala/" target="_blank" '
    'rel="noopener noreferrer" aria-label="LinkedIn profile">'
    '<svg viewBox="0 0 16 16" width="18" height="18" fill="currentColor"><path d="M14.82 0H1.18C.53 0 0 .53 0 '
    "1.18v13.64C0 15.47.53 16 1.18 16h13.64c.65 0 1.18-.53 1.18-1.18V1.18C16 .53 15.47 0 14.82 0zM4.75 13.4H2.4V"
    "6.1h2.35v7.3zM3.58 5.1a1.36 1.36 0 110-2.72 1.36 1.36 0 010 2.72zM13.6 13.4h-2.35V9.85c0-.85-.02-1.94-1.18-"
    "1.94-1.18 0-1.36.92-1.36 1.88v3.61H6.36V6.1h2.26v1h.03c.32-.6 1.09-1.23 2.24-1.23 2.4 0 2.84 1.58 2.84 3.63"
    'v3.9z"/></svg></a>'
)

HERO_HTML = f"""
<div class="hero">
  <div class="hero-copy">
    <div class="brand">
      <span class="wordmark">JobScan</span>
      <span class="credit">Made by RoopeshJ</span>
      {BRAND_LINKS_HTML}
    </div>
    <h1>See exactly where you stand.</h1>
    <p>Paste a posting and your background. Every strength and gap comes back tied to the line it's drawn from,
    so nothing's guessed. Do this for every posting you actually want, and the gaps that keep repeating are what
    to learn next.</p>
  </div>
  <div class="thread-demo">
    <div class="demo-label">A worked example. Every claim points to the exact line it's drawn from.</div>
    <div class="demo-examples">
      <span class="demo-tag strength">Strength</span>
      <span class="demo-tag gap">Gap</span>
      <div class="claim">You've shipped production Kubernetes migrations before.</div>
      <div class="claim">No experience running multi-region failover.</div>
      <svg class="svg-link" viewBox="0 0 20 24">
        <path class="link-line" d="M10 2 L10 16" />
        <path class="link-head" d="M5 11 L10 17 L15 11" />
      </svg>
      <svg class="svg-link" viewBox="0 0 20 24">
        <path class="link-line" d="M10 2 L10 16" />
        <path class="link-head" d="M5 11 L10 17 L15 11" />
      </svg>
      <div class="quote">"Own the <mark>migration off our legacy orchestration</mark> onto a managed
      Kubernetes platform."</div>
      <div class="quote">"Must have run <mark>active-active deployments across regions</mark>."</div>
    </div>
  </div>
</div>
"""

HOW_TO_HTML = """
<div class="how-to">
  <span class="field-label">How it works</span>
  <ol class="how-steps">
    <li><strong>Paste your background.</strong> Resume, notes, anything in plain text.</li>
    <li><strong>Add a posting, or a link to it.</strong> Most sites work from a link. LinkedIn blocks outside
    fetching, so paste the text for those instead.</li>
    <li><strong>View your results.</strong> The gaps are worth as much attention as the strengths.</li>
  </ol>
</div>
"""

CITATION_SCROLL_JS = """
<script>
(function () {
  var doc = window.parent.document;
  if (doc.__jobscanCiteScrollBound) return;
  doc.__jobscanCiteScrollBound = true;

  function scrollToCitation(target) {
    var card = target.closest && target.closest('.insight-card[data-cite-target]');
    if (!card) return;
    var ids = (card.getAttribute('data-cite-target') || '').split(' ').filter(Boolean);
    if (!ids.length) return;
    var mark = doc.querySelector('mark[data-cite-id~="' + ids[0] + '"]');
    if (!mark) return;
    var rail = mark.closest('.rail-scroll');
    if (!rail) return;
    var markRect = mark.getBoundingClientRect();
    var railRect = rail.getBoundingClientRect();
    var delta = (markRect.top + markRect.height / 2) - (railRect.top + railRect.height / 2);
    rail.scrollBy({top: delta, behavior: 'smooth'});
  }

  doc.addEventListener('mouseover', function (e) { scrollToCitation(e.target); });
  doc.addEventListener('focusin', function (e) { scrollToCitation(e.target); });
})();
</script>
"""
