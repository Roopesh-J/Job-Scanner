"""Embedding-based matching between predicted and reference extraction items."""

from dataclasses import dataclass

_model = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


@dataclass
class MatchResult:
    matched_pairs: list[tuple[int, int]]
    unmatched_predicted: list[int]
    unmatched_reference: list[int]


def match_items(predicted: list[str], reference: list[str], threshold: float = 0.75) -> MatchResult:
    if not predicted or not reference:
        return MatchResult(
            matched_pairs=[],
            unmatched_predicted=list(range(len(predicted))),
            unmatched_reference=list(range(len(reference))),
        )

    import numpy as np

    model = _get_model()
    pred_embeddings = np.asarray(model.encode(predicted))
    ref_embeddings = np.asarray(model.encode(reference))

    pred_norm = pred_embeddings / np.linalg.norm(pred_embeddings, axis=1, keepdims=True)
    ref_norm = ref_embeddings / np.linalg.norm(ref_embeddings, axis=1, keepdims=True)
    similarity = pred_norm @ ref_norm.T

    candidates = []
    for i in range(len(predicted)):
        for j in range(len(reference)):
            if similarity[i][j] >= threshold:
                candidates.append((similarity[i][j], i, j))
    candidates.sort(key=lambda c: c[0], reverse=True)

    matched_pairs = []
    used_predicted = set()
    used_reference = set()
    for _, i, j in candidates:
        if i in used_predicted or j in used_reference:
            continue
        matched_pairs.append((i, j))
        used_predicted.add(i)
        used_reference.add(j)

    matched_pairs.sort()
    unmatched_predicted = [i for i in range(len(predicted)) if i not in used_predicted]
    unmatched_reference = [j for j in range(len(reference)) if j not in used_reference]

    return MatchResult(matched_pairs, unmatched_predicted, unmatched_reference)
