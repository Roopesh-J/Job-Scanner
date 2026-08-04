from job_scanner.models import Posting, SearchAction


def build_id_lookup(posting: Posting) -> dict[str, str]:
    lookup = {r.id: r.source_quote for r in posting.requirements}
    lookup.update({r.id: r.source_quote for r in posting.responsibilities})
    return lookup


def format_sources(supporting_ids: list[str], id_lookup: dict[str, str]) -> str:
    quotes = [id_lookup[rid] for rid in supporting_ids if rid in id_lookup]
    return ", ".join(f"“{q}”" for q in quotes)


def format_search_actions(search_actions: list[SearchAction]) -> list[str]:
    lines = []
    for action in search_actions:
        titles = ", ".join(r.title for r in action.results) or "no results"
        lines.append(f"Searched “{action.query}” — found: {titles}")
    return lines
