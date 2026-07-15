from job_scanner.models import Posting


def find_ungrounded_quotes(posting: Posting, posting_text: str) -> list[str]:
    violations = []
    for req in posting.requirements:
        if req.source_quote not in posting_text:
            violations.append(req.id)
    for resp in posting.responsibilities:
        if resp.source_quote not in posting_text:
            violations.append(resp.id)
    return violations


def find_invalid_references(referenced_ids: list[str], valid_ids: set[str]) -> list[str]:
    return [rid for rid in referenced_ids if rid not in valid_ids]
