from job_scanner.models import Posting, SearchAction

STRENGTH_COLOR = "#2F6B4F"
GAP_COLOR = "#B5772E"
CARD_BACKGROUND = "#F0E9DC"

CHECK_ICON_SVG = (
    '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" '
    'style="vertical-align:-3px;"><polyline points="20 6 9 17 4 12"></polyline></svg>'
)

WARNING_ICON_SVG = (
    '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" '
    'style="vertical-align:-3px;">'
    '<path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>'
    '<path d="M12 9v4"></path><path d="M12 17h.01"></path></svg>'
)

GLOBAL_CSS = f"""
<style>
div[class*="st-key-strength_"] {{
    border-left: 3px solid {STRENGTH_COLOR};
    background: {CARD_BACKGROUND};
    border-radius: 4px;
    padding: 10px 14px;
    margin-bottom: 8px;
}}
div[class*="st-key-gap_"] {{
    border-left: 3px solid {GAP_COLOR};
    background: {CARD_BACKGROUND};
    border-radius: 4px;
    padding: 10px 14px;
    margin-bottom: 8px;
}}
div[data-testid="stPopover"] button {{
    padding: 2px 10px;
    font-size: 0.8rem;
    min-height: 0;
}}
</style>
"""


def section_heading(label: str, icon_svg: str, color: str) -> str:
    return (
        f'<h4 style="color:{color}; display:flex; align-items:center; gap:6px; margin-bottom:0.6rem;">'
        f"{icon_svg} {label}</h4>"
    )


def build_id_lookup(posting: Posting) -> dict[str, str]:
    lookup = {r.id: r.source_quote for r in posting.requirements}
    lookup.update({r.id: r.source_quote for r in posting.responsibilities})
    return lookup


def format_sources(supporting_ids: list[str], id_lookup: dict[str, str]) -> str:
    quotes = [id_lookup[rid] for rid in supporting_ids if rid in id_lookup]
    return ", ".join(f"“{q}”" for q in quotes)


def format_badge_counts(strength_count: int, gap_count: int) -> str:
    strength_label = "strength" if strength_count == 1 else "strengths"
    gap_label = "gap" if gap_count == 1 else "gaps"
    return f"✓ {strength_count} {strength_label} · ⚠ {gap_count} {gap_label}"


def format_search_actions(search_actions: list[SearchAction]) -> list[str]:
    lines = []
    for action in search_actions:
        titles = ", ".join(r.title for r in action.results) or "no results"
        lines.append(f"Searched “{action.query}” — found: {titles}")
    return lines
