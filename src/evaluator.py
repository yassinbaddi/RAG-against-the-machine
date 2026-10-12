"""Local recall@k evaluation (for your own iteration only — not the grader)."""

from __future__ import annotations

import json
from pathlib import Path

from .models import AnsweredQuestion, MinimalSearchResults, MinimalSource

IOU_THRESHOLD = 0.05


def check_overlap(src1: MinimalSource, src2: MinimalSource) -> bool:
    """Return True if two sources are in the same file and overlap enough."""
    if src1.file_path != src2.file_path:
        return False

    start1, end1 = src1.first_character_index, src1.last_character_index
    start2, end2 = src2.first_character_index, src2.last_character_index

    intersection = max(0, min(end1, end2) - max(start1, start2) + 1)
    union = max(end1, end2) - min(start1, start2) + 1
    if union == 0:
        return False

    return (intersection / union) >= IOU_THRESHOLD


def load_answered_questions(dataset_path: Path) -> list[AnsweredQuestion]:
    """Load a ground-truth AnsweredQuestions dataset."""
    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset not found: {dataset_path}")

    with dataset_path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    return [
        AnsweredQuestion(
            question_id=item["question_id"],
            question=item["question"],
            sources=[MinimalSource(**s) for s in item["sources"]],
            answer=item.get("answer", ""),
        )
        for item in data.get("rag_questions", [])
    ]


def load_search_results(path: Path) -> list[MinimalSearchResults]:
    """Load a StudentSearchResults JSON file."""
    if not path.exists():
        raise FileNotFoundError(f"Search results not found: {path}")

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    return [
        MinimalSearchResults(
            question_id=item["question_id"],
            question=item["question"],
            retrieved_sources=item["retrieved_sources"],
        )
        for item in data.get("search_results", [])
    ]


def recall_at_k(
    student_results: list[MinimalSearchResults],
    ground_truth: dict[str, list[MinimalSource]],
) -> float:
    """Average, over all questions, the share of correct sources retrieved."""
    per_question_recall: list[float] = []

    for result in student_results:
        gt_sources = ground_truth.get(result.question_id, [])
        if not gt_sources:
            continue

        found = sum(
            1
            for gt in gt_sources
            if any(check_overlap(ret, gt) for ret in result.retrieved_sources)
        )
        per_question_recall.append(found / len(gt_sources))

    if not per_question_recall:
        return 0.0
    return sum(per_question_recall) / len(per_question_recall)


def evaluate(student_search_results_path: str, dataset_path: str) -> str:
    """Compute recall@k of a student search-results file against ground truth."""
    student_results = load_search_results(Path(student_search_results_path))
    questions = load_answered_questions(Path(dataset_path))
    ground_truth = {q.question_id: q.sources for q in questions}

    score = recall_at_k(student_results, ground_truth)
    return f"{score * 100:.2f}%"
