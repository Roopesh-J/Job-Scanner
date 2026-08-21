from job_scanner.eval.matching import match_items


def test_identical_text_matches_with_perfect_similarity():
    result = match_items(["5+ years of Python experience"], ["5+ years of Python experience"])
    assert result.matched_pairs == [(0, 0)]
    assert result.unmatched_predicted == []
    assert result.unmatched_reference == []


def test_paraphrased_text_still_matches_above_default_threshold():
    result = match_items(["5+ years of Python experience"], ["five years of Python programming"])
    assert result.matched_pairs == [(0, 0)]


def test_unrelated_text_does_not_match():
    result = match_items(["5+ years of Python experience"], ["experience with customer service"])
    assert result.matched_pairs == []
    assert result.unmatched_predicted == [0]
    assert result.unmatched_reference == [0]


def test_extra_predicted_item_counts_as_unmatched_predicted():
    result = match_items(
        ["5+ years of Python experience", "familiar with unrelated topic entirely"],
        ["5+ years of Python experience"],
    )
    assert result.matched_pairs == [(0, 0)]
    assert result.unmatched_predicted == [1]
    assert result.unmatched_reference == []


def test_missing_reference_item_counts_as_unmatched_reference():
    result = match_items(
        ["5+ years of Python experience"],
        ["5+ years of Python experience", "completely unrelated requirement about something else"],
    )
    assert result.matched_pairs == [(0, 0)]
    assert result.unmatched_predicted == []
    assert result.unmatched_reference == [1]


def test_empty_predicted_list_leaves_all_reference_items_unmatched():
    result = match_items([], ["5+ years of Python experience"])
    assert result.matched_pairs == []
    assert result.unmatched_predicted == []
    assert result.unmatched_reference == [0]


def test_empty_reference_list_leaves_all_predicted_items_unmatched():
    result = match_items(["5+ years of Python experience"], [])
    assert result.matched_pairs == []
    assert result.unmatched_predicted == [0]
    assert result.unmatched_reference == []


def test_numeric_detail_changes_are_not_reliably_caught_by_semantic_matching():
    # Known, verified limitation: general-purpose sentence embeddings score "5+ years" and "10+ years"
    # of the same skill as highly similar (~0.97 with this model) because the surrounding text
    # dominates the embedding. This matcher decides *whether the same requirement is being talked
    # about*, not whether the predicted text is factually faithful to it — numeric/factual drift
    # within a matched pair is not caught here. Documented, not fixed, in this phase.
    result = match_items(["5+ years of Python experience"], ["10+ years of Python experience"])
    assert result.matched_pairs == [(0, 0)]
