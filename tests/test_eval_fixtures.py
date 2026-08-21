import json
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "eval"


def _fixture_pairs():
    posting_files = sorted(FIXTURES_DIR.glob("posting_*.txt"))
    for posting_file in posting_files:
        expected_file = FIXTURES_DIR / f"{posting_file.stem}.expected.json"
        yield posting_file, expected_file


def test_five_reference_postings_exist():
    posting_files = sorted(FIXTURES_DIR.glob("posting_*.txt"))
    assert len(posting_files) == 5


def test_every_reference_quote_is_grounded_in_its_posting_text():
    for posting_file, expected_file in _fixture_pairs():
        posting_text = posting_file.read_text()
        reference = json.loads(expected_file.read_text())
        for item in reference["requirements"] + reference["responsibilities"]:
            assert item["source_quote"] in posting_text, (
                f"{posting_file.name}: quote not found verbatim: {item['source_quote']!r}"
            )


def test_every_requirement_has_a_valid_category():
    for posting_file, expected_file in _fixture_pairs():
        reference = json.loads(expected_file.read_text())
        for req in reference["requirements"]:
            assert req["category"] in ("required", "preferred", "unclear"), (
                f"{posting_file.name}: invalid category {req['category']!r}"
            )
