from __future__ import annotations


def aggregate_page_scores(page_scores: list[int]) -> int:
    """Document-level score from page scores.

    formula: round(0.75 * max(pages) + 0.25 * mean(pages))

    The strongest page dominates so a manipulated page is not washed out by
    clean pages. The mean term keeps a single weak spike from equaling
    multi-page evidence.
    """
    if not page_scores:
        return 0
    strongest = max(page_scores)
    mean = sum(page_scores) / len(page_scores)
    return int(round(min(100, 0.75 * strongest + 0.25 * mean)))


def aggregate_confidence(page_confidences: list[float]) -> float:
    if not page_confidences:
        return 0.0
    strongest = max(page_confidences)
    mean = sum(page_confidences) / len(page_confidences)
    return round(min(1.0, 0.7 * strongest + 0.3 * mean), 2)
