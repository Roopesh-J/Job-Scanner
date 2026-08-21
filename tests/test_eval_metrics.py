from job_scanner.eval.matching import MatchResult
from job_scanner.eval.metrics import (
    AggregateEvalResult,
    PostingEvalResult,
    PrecisionRecall,
    aggregate_results,
    category_accuracy,
    evaluate_posting,
    grounding_rate,
    precision_recall,
)
from job_scanner.models import Category, Posting, Requirement, Responsibility


def test_precision_recall_counts_true_false_positives_and_negatives():
    match = MatchResult(matched_pairs=[(0, 0), (1, 1)], unmatched_predicted=[2], unmatched_reference=[3])
    result = precision_recall(match)
    assert result.true_positives == 2
    assert result.false_positives == 1
    assert result.false_negatives == 1
    assert result.precision == 2 / 3
    assert result.recall == 2 / 3


def test_precision_recall_perfect_match_is_one():
    match = MatchResult(matched_pairs=[(0, 0)], unmatched_predicted=[], unmatched_reference=[])
    result = precision_recall(match)
    assert result.precision == 1.0
    assert result.recall == 1.0


def test_precision_recall_handles_empty_match_without_division_by_zero():
    match = MatchResult(matched_pairs=[], unmatched_predicted=[], unmatched_reference=[])
    result = precision_recall(match)
    assert result.precision == 1.0
    assert result.recall == 1.0


def test_category_accuracy_counts_matches_and_builds_confusion_matrix():
    match = MatchResult(matched_pairs=[(0, 0), (1, 1), (2, 2)], unmatched_predicted=[], unmatched_reference=[])
    predicted_categories = ["required", "preferred", "required"]
    reference_categories = ["required", "preferred", "preferred"]
    accuracy, confusion = category_accuracy(match, predicted_categories, reference_categories)
    assert accuracy == 2 / 3
    assert confusion == {("required", "required"): 1, ("preferred", "preferred"): 1, ("preferred", "required"): 1}


def test_category_accuracy_with_no_matches_is_one_with_empty_confusion():
    match = MatchResult(matched_pairs=[], unmatched_predicted=[0], unmatched_reference=[0])
    accuracy, confusion = category_accuracy(match, ["required"], ["required"])
    assert accuracy == 1.0
    assert confusion == {}


def _posting(requirements, responsibilities):
    return Posting(
        title="Example Role",
        company="Example Co",
        responsibilities=responsibilities,
        requirements=requirements,
    )


def test_grounding_rate_is_one_when_all_quotes_are_verbatim():
    posting = _posting(
        requirements=[
            Requirement(id="req-1", text="Python", category=Category.REQUIRED, source_quote="5+ years of Python"),
        ],
        responsibilities=[
            Responsibility(id="resp-1", text="Own the API", source_quote="own the public API"),
        ],
    )
    posting_text = "Requires 5+ years of Python. You'll own the public API."
    assert grounding_rate(posting, posting_text) == 1.0


def test_grounding_rate_drops_for_each_ungrounded_quote():
    posting = _posting(
        requirements=[
            Requirement(id="req-1", text="Python", category=Category.REQUIRED, source_quote="5+ years of Python"),
            Requirement(
                id="req-2", text="Rust", category=Category.PREFERRED,
                source_quote="this quote is not in the text",
            ),
        ],
        responsibilities=[],
    )
    posting_text = "Requires 5+ years of Python."
    assert grounding_rate(posting, posting_text) == 0.5


def test_grounding_rate_is_one_for_a_posting_with_no_items():
    posting = _posting(requirements=[], responsibilities=[])
    assert grounding_rate(posting, "any text") == 1.0


def test_evaluate_posting_combines_all_metrics():
    posting_text = "Requires 5+ years of Python experience. You'll own the public API."
    predicted = _posting(
        requirements=[
            Requirement(
                id="req-1", text="5+ years of Python experience",
                category=Category.REQUIRED, source_quote="5+ years of Python experience",
            ),
        ],
        responsibilities=[
            Responsibility(id="resp-1", text="Own the public API", source_quote="own the public API"),
        ],
    )
    reference = {
        "requirements": [
            {
                "text": "5+ years of Python experience",
                "category": "required",
                "source_quote": "5+ years of Python experience",
            },
        ],
        "responsibilities": [
            {"text": "Own the public API", "source_quote": "own the public API"},
        ],
    }

    result = evaluate_posting(predicted, reference, posting_text)

    assert isinstance(result, PostingEvalResult)
    assert result.requirement_pr.precision == 1.0
    assert result.requirement_pr.recall == 1.0
    assert result.responsibility_pr.precision == 1.0
    assert result.responsibility_pr.recall == 1.0
    assert result.category_accuracy_score == 1.0
    assert result.grounding_rate_score == 1.0


def test_aggregate_results_averages_across_postings():
    result_a = PostingEvalResult(
        requirement_pr=PrecisionRecall(precision=1.0, recall=1.0, true_positives=1, false_positives=0, false_negatives=0),
        responsibility_pr=PrecisionRecall(precision=1.0, recall=1.0, true_positives=1, false_positives=0, false_negatives=0),
        category_accuracy_score=1.0,
        category_confusion={("required", "required"): 1},
        grounding_rate_score=1.0,
    )
    result_b = PostingEvalResult(
        requirement_pr=PrecisionRecall(precision=0.0, recall=0.0, true_positives=0, false_positives=1, false_negatives=1),
        responsibility_pr=PrecisionRecall(precision=0.5, recall=0.5, true_positives=1, false_positives=1, false_negatives=1),
        category_accuracy_score=0.0,
        category_confusion={("required", "preferred"): 1},
        grounding_rate_score=0.5,
    )

    aggregate = aggregate_results([result_a, result_b])

    assert isinstance(aggregate, AggregateEvalResult)
    assert aggregate.mean_requirement_precision == 0.5
    assert aggregate.mean_requirement_recall == 0.5
    assert aggregate.mean_responsibility_precision == 0.75
    assert aggregate.mean_category_accuracy == 0.5
    assert aggregate.mean_grounding_rate == 0.75
    assert aggregate.category_confusion == {("required", "required"): 1, ("required", "preferred"): 1}
