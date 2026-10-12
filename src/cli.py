"""Command-line interface for the RAG pipeline (Python Fire)."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

import fire
from tqdm import tqdm

from .evaluator import evaluate as compute_recall
from .generator import generate_answer
from .indexer import build_bm25_index, build_chunks, save_bm25_index
from .models import (
    MinimalAnswer,
    MinimalSearchResults,
    MinimalSource,
    StudentSearchResults,
    StudentSearchResultsAndAnswer,
)
from .retriever import (
    build_chunk_lookup,
    chunks_to_sources,
    find_matching_chunk,
    load_bm25_index,
    search_bm25,
)


def index(
    max_chunk_size: int = 2000,
    input_directory: str = "data/raw/vllm-0.10.1",
    output_directory: str = "data/processed/bm25",
) -> None:
    """Ingest a corpus, chunk it, and persist a BM25 index."""
    try:
        max_chunk_size = int(max_chunk_size)
        if max_chunk_size <= 0:
            print("Error: max_chunk_size must be greater than 0.")
            return

        root = Path(input_directory)
        output_path = Path(output_directory)

        print(f"Corpus: {root}")
        print(f"Output: {output_path}")
        print(f"Max chunk size: {max_chunk_size}")

        chunks = build_chunks(root=root, max_chunk_size=max_chunk_size)
        print(f"Created {len(chunks)} chunks.")

        retriever = build_bm25_index(chunks)
        save_bm25_index(retriever, chunks, output_path, max_chunk_size)

        print(f"Ingestion complete! Indexed {len(chunks)} chunks.")
        print(f"Indices saved under {output_path}/")

    except (FileNotFoundError, NotADirectoryError, ValueError) as exc:
        print(f"Error: {exc}")
    except Exception as exc:  # noqa: BLE001
        print(f"Indexing failed: {exc}")


def search(
    query: str,
    k: int = 5,
    output_directory: str = "data/processed/bm25",
) -> None:
    """Return the top-k sources for a single query."""
    try:
        query = query.strip()
        if not query:
            print("Error: query cannot be empty.")
            return
        if k <= 0:
            print("Error: k must be greater than 0.")
            return

        retriever, chunks = load_bm25_index(Path(output_directory))
        result = search_bm25(retriever, query, chunks, k)
        sources = chunks_to_sources(result)

        search_result = MinimalSearchResults(
            question_id=str(uuid.uuid4()),
            question=query,
            retrieved_sources=sources,
        )
        student_results = StudentSearchResults(search_results=[search_result], k=k)
        print(student_results.model_dump_json(indent=4))

    except (FileNotFoundError, NotADirectoryError, ValueError) as exc:
        print(f"Error: {exc}")
    except Exception as exc:  # noqa: BLE001
        print(f"Search failed: {exc}")


def search_dataset(
    dataset_path: str = "data/datasets/UnansweredQuestions/dataset_code_public.json",
    k: int = 5,
    save_directory: str = "data/output/search_results/UnansweredQuestions",
    output_directory: str = "data/processed/bm25",
) -> None:
    """Run search over a whole dataset and write a StudentSearchResults file."""
    try:
        if k <= 0:
            print("Error: k must be greater than 0.")
            return

        path = Path(dataset_path)
        if not path.exists():
            print(f"Error: dataset not found: {path}")
            return

        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        retriever, chunks = load_bm25_index(Path(output_directory))

        search_results = []
        for item in tqdm(data.get("rag_questions", []), desc="Searching dataset"):
            question_id = item.get("question_id", str(uuid.uuid4()))
            question = item["question"]

            result = search_bm25(retriever, question, chunks, k)
            search_results.append(
                MinimalSearchResults(
                    question_id=question_id,
                    question=question,
                    retrieved_sources=chunks_to_sources(result),
                )
            )

        student_results = StudentSearchResults(search_results=search_results, k=k)

        output_dir = Path(save_directory)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / path.name

        with output_file.open("w", encoding="utf-8") as file:
            file.write(student_results.model_dump_json(indent=4))

        print(f"Saved student_search_results to {output_file}")

    except json.JSONDecodeError as exc:
        print(f"Error: malformed JSON dataset: {exc}")
    except (FileNotFoundError, KeyError, ValueError) as exc:
        print(f"Error: {exc}")
    except Exception as exc:  # noqa: BLE001
        print(f"Search dataset failed: {exc}")


def answer(
    query: str,
    k: int = 5,
    output_directory: str = "data/processed/bm25",
) -> None:
    """Answer a single query using retrieved context and a local LLM."""
    try:
        query = query.strip()
        if not query:
            print("Error: query cannot be empty.")
            return
        if k <= 0:
            print("Error: k must be greater than 0.")
            return

        retriever, chunks = load_bm25_index(Path(output_directory))
        result = search_bm25(retriever, query, chunks, k)

        generated_answer = generate_answer(query, result)
        sources = chunks_to_sources(result)

        student_answer = MinimalAnswer(
            question_id=str(uuid.uuid4()),
            question=query,
            retrieved_sources=sources,
            answer=generated_answer,
        )
        print(student_answer.model_dump_json(indent=4))

    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}")
    except Exception as exc:  # noqa: BLE001
        print(f"Answer generation failed: {exc}")


def answer_dataset(
    student_search_results_path: str,
    save_directory: str,
    output_directory: str = "data/processed/bm25",
) -> None:
    """Generate answers for every question of a search-results dataset."""
    try:
        input_path = Path(student_search_results_path)
        if not input_path.exists():
            print(f"Error: search results not found: {input_path}")
            return

        with input_path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        _, chunks = load_bm25_index(Path(output_directory))
        lookup = build_chunk_lookup(chunks)

        answers = []
        for question in tqdm(data.get("search_results", []), desc="Answering"):
            retrieved_sources = [
                MinimalSource(**source) for source in question["retrieved_sources"]
            ]
            context_chunks = [
                chunk
                for source in retrieved_sources
                if (chunk := find_matching_chunk(lookup, source)) is not None
            ]

            generated_answer = generate_answer(question["question"], context_chunks)

            answers.append(
                MinimalAnswer(
                    question_id=question["question_id"],
                    question=question["question"],
                    retrieved_sources=retrieved_sources,
                    answer=generated_answer,
                )
            )

        student_results = StudentSearchResultsAndAnswer(
            search_results=answers, k=data.get("k", 5)
        )

        output_dir = Path(save_directory)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / input_path.name

        with output_file.open("w", encoding="utf-8") as file:
            file.write(student_results.model_dump_json(indent=4))

        print(f"Saved student_search_results_and_answer to {output_file}")

    except json.JSONDecodeError as exc:
        print(f"Error: malformed JSON input: {exc}")
    except (FileNotFoundError, KeyError, ValueError) as exc:
        print(f"Error: {exc}")
    except Exception as exc:  # noqa: BLE001
        print(f"Answer generation failed: {exc}")


def evaluate(
    student_search_results_path: str = (
        "data/output/search_results/UnansweredQuestions/dataset_code_public.json"
    ),
    dataset_path: str = "data/datasets/AnsweredQuestions/dataset_code_public.json",
) -> None:
    """Report recall@k of student search results against a ground-truth dataset."""
    try:
        score = compute_recall(student_search_results_path, dataset_path)
        print(f"Recall: {score}")
    except (FileNotFoundError, json.JSONDecodeError, KeyError, ValueError) as exc:
        print(f"Error: {exc}")
    except Exception as exc:
        print(f"Evaluation failed: {exc}")


def main() -> None:
    """Register all CLI commands with Fire."""
    fire.Fire(
        {
            "index": index,
            "search": search,
            "search_dataset": search_dataset,
            "answer": answer,
            "answer_dataset": answer_dataset,
            "evaluate": evaluate,
        }
    )
