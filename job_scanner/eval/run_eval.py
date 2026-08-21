"""Standalone Stage 1 eval report. Makes real Claude API calls — run manually, not part of pytest.

Usage: python -m job_scanner.eval.run_eval
"""

import json
from pathlib import Path

from dotenv import load_dotenv

from job_scanner.eval.metrics import aggregate_results, evaluate_posting
from job_scanner.extractor import extract_posting
from job_scanner.llm_client import LLMClient

FIXTURES_DIR = Path(__file__).parent.parent.parent / "tests" / "fixtures" / "eval"


def _load_fixtures():
    posting_files = sorted(FIXTURES_DIR.glob("posting_*.txt"))
    for posting_file in posting_files:
        expected_file = FIXTURES_DIR / f"{posting_file.stem}.expected.json"
        posting_text = posting_file.read_text()
        reference = json.loads(expected_file.read_text())
        yield posting_file.stem, posting_text, reference


def main() -> None:
    load_dotenv()
    client = LLMClient()

    results = []
    for name, posting_text, reference in _load_fixtures():
        extraction = extract_posting(posting_text, client)
        result = evaluate_posting(
            extraction.posting, reference, posting_text, dropped_count=len(extraction.dropped_ids)
        )
        results.append(result)

        print(f"\n{name}")
        print(
            f"  requirements     precision={result.requirement_pr.precision:.2f}  "
            f"recall={result.requirement_pr.recall:.2f}"
        )
        print(
            f"  responsibilities precision={result.responsibility_pr.precision:.2f}  "
            f"recall={result.responsibility_pr.recall:.2f}"
        )
        print(f"  category accuracy: {result.category_accuracy_score:.2f}")
        print(f"  grounding rate: {result.grounding_rate_score:.2f}")

    aggregate = aggregate_results(results)
    print("\n=== Aggregate (mean across postings) ===")
    print(
        f"Requirement    precision={aggregate.mean_requirement_precision:.2f}  "
        f"recall={aggregate.mean_requirement_recall:.2f}"
    )
    print(
        f"Responsibility precision={aggregate.mean_responsibility_precision:.2f}  "
        f"recall={aggregate.mean_responsibility_recall:.2f}"
    )
    print(f"Category accuracy: {aggregate.mean_category_accuracy:.2f}")
    print(f"Grounding rate: {aggregate.mean_grounding_rate:.2f}")
    print(f"Category confusion matrix: {aggregate.category_confusion}")


if __name__ == "__main__":
    main()
