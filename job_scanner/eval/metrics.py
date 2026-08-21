"""Scoring: precision/recall, category accuracy, and grounding rate for Stage 1 extraction."""

from dataclasses import dataclass

from job_scanner.eval.matching import MatchResult, match_items
from job_scanner.models import Posting
from job_scanner.validation import find_ungrounded_quotes


@dataclass
class PrecisionRecall:
    precision: float
    recall: float
    true_positives: int
    false_positives: int
    false_negatives: int


def precision_recall(match: MatchResult) -> PrecisionRecall:
    tp = len(match.matched_pairs)
    fp = len(match.unmatched_predicted)
    fn = len(match.unmatched_reference)
    precision = tp / (tp + fp) if (tp + fp) else 1.0
    recall = tp / (tp + fn) if (tp + fn) else 1.0
    return PrecisionRecall(
        precision=precision, recall=recall,
        true_positives=tp, false_positives=fp, false_negatives=fn,
    )


def category_accuracy(
    match: MatchResult, predicted_categories: list[str], reference_categories: list[str]
) -> tuple[float, dict[tuple[str, str], int]]:
    confusion: dict[tuple[str, str], int] = {}
    correct = 0
    for pred_idx, ref_idx in match.matched_pairs:
        pred_cat = predicted_categories[pred_idx]
        ref_cat = reference_categories[ref_idx]
        confusion[(ref_cat, pred_cat)] = confusion.get((ref_cat, pred_cat), 0) + 1
        if pred_cat == ref_cat:
            correct += 1
    total = len(match.matched_pairs)
    accuracy = correct / total if total else 1.0
    return accuracy, confusion


def grounding_rate(posting: Posting, posting_text: str, dropped_count: int = 0) -> float:
    total_items = len(posting.requirements) + len(posting.responsibilities) + dropped_count
    if total_items == 0:
        return 1.0
    violations = len(find_ungrounded_quotes(posting, posting_text)) + dropped_count
    return 1 - (violations / total_items)


@dataclass
class PostingEvalResult:
    requirement_pr: PrecisionRecall
    responsibility_pr: PrecisionRecall
    category_accuracy_score: float
    category_confusion: dict[tuple[str, str], int]
    grounding_rate_score: float


def evaluate_posting(
    predicted: Posting, reference: dict, posting_text: str, dropped_count: int = 0
) -> PostingEvalResult:
    predicted_req_texts = [r.text for r in predicted.requirements]
    reference_req_texts = [r["text"] for r in reference["requirements"]]
    req_match = match_items(predicted_req_texts, reference_req_texts)
    requirement_pr = precision_recall(req_match)

    predicted_categories = [r.category.value for r in predicted.requirements]
    reference_categories = [r["category"] for r in reference["requirements"]]
    category_accuracy_score, category_confusion = category_accuracy(
        req_match, predicted_categories, reference_categories
    )

    predicted_resp_texts = [r.text for r in predicted.responsibilities]
    reference_resp_texts = [r["text"] for r in reference["responsibilities"]]
    resp_match = match_items(predicted_resp_texts, reference_resp_texts)
    responsibility_pr = precision_recall(resp_match)

    grounding_rate_score = grounding_rate(predicted, posting_text, dropped_count)

    return PostingEvalResult(
        requirement_pr=requirement_pr,
        responsibility_pr=responsibility_pr,
        category_accuracy_score=category_accuracy_score,
        category_confusion=category_confusion,
        grounding_rate_score=grounding_rate_score,
    )


@dataclass
class AggregateEvalResult:
    mean_requirement_precision: float
    mean_requirement_recall: float
    mean_responsibility_precision: float
    mean_responsibility_recall: float
    mean_category_accuracy: float
    category_confusion: dict[tuple[str, str], int]
    mean_grounding_rate: float


def aggregate_results(results: list[PostingEvalResult]) -> AggregateEvalResult:
    n = len(results)
    combined_confusion: dict[tuple[str, str], int] = {}
    for r in results:
        for key, count in r.category_confusion.items():
            combined_confusion[key] = combined_confusion.get(key, 0) + count

    return AggregateEvalResult(
        mean_requirement_precision=sum(r.requirement_pr.precision for r in results) / n,
        mean_requirement_recall=sum(r.requirement_pr.recall for r in results) / n,
        mean_responsibility_precision=sum(r.responsibility_pr.precision for r in results) / n,
        mean_responsibility_recall=sum(r.responsibility_pr.recall for r in results) / n,
        mean_category_accuracy=sum(r.category_accuracy_score for r in results) / n,
        category_confusion=combined_confusion,
        mean_grounding_rate=sum(r.grounding_rate_score for r in results) / n,
    )
