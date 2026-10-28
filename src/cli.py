"""Command-line interface for the RAG pipeline."""
import json
from pathlib import Path
import types
import uuid
import fire
from tqdm import tqdm

from src.models import (
    Chunk,
    StudentSearchResults,
    StudentSearchResultsAndAnswer,
    RagDataset,
    MinimalSearchResults,
    MinimalAnswer,
)
from src.chunkers import chunk_file
from src.indexer import (
    SUPPORTED_EXTENSIONS,
    build_chunks,
    build_bm25_index,
    save_bm25_index,
)
from src.retriever import (
    load_bm25_index,
    search_bm25,
    chunks_to_sources,
    build_chunk_lookup,
    find_matching_chunk,
)
from src.generator import generate_answer
from src.evaluator import evaluate as run_evaluate
from src.embeddings import embed_chunks, save_embeddings, load_embeddings
from src.hybrid import search_hybrid
from src.incremental import load_manifest, save_manifest, has_changed, file_hash
from src.cache import load_cache, save_cache, cache_key
import typing
import uuid


DEFAULT_INPUT_DIR = "data/raw/vllm-0.10.1"
DEFAULT_INDEX_DIR = "data/processed/bm25"


def index(
    max_chunk_size: int = 2000,
    input_directory: str = DEFAULT_INPUT_DIR,
    output_directory: str = DEFAULT_INDEX_DIR,
    incremental: bool = False,
    with_embeddings: bool = False,
) -> None:
    """Build the BM25 index (and optionally embeddings) over the corpus."""
    try:
        root = Path(input_directory)
        if not root.exists():
            print(f"Error: input directory '{input_directory}' not found")
            return

        output_path = Path(output_directory)
        output_path.mkdir(parents=True, exist_ok=True)

        if incremental:
            manifest = load_manifest(output_directory)
            all_files = [
                p for p in root.rglob("*")
                if p.is_file() and p.suffix in SUPPORTED_EXTENSIONS
            ]
            changed_files = [f for f in all_files if has_changed(f, manifest)]
            print(f"{len(changed_files)}/{len(all_files)} files changed, reindexing those only")

            chunks_path = output_path / "chunks.json"
            chunks_path = Path(chunks_path)
            previous_chunks = json.loads(chunks_path.read_text()) if chunks_path.exists() else []
            changed_paths = {str(f) for f in changed_files}
            kept = [c for c in previous_chunks if c["file_path"] not in changed_paths]

            new_chunks = []
            for f in tqdm(changed_files, desc="Chunking changed files"):
                new_chunks.extend(chunk_file(f, max_chunk_size))

            merged = kept + [c.model_dump() for c in new_chunks]
            chunks = [Chunk(**c) for c in merged]

            for f in changed_files:
                manifest[str(f)] = file_hash(f)
            save_manifest(manifest, output_directory)
        else:
            chunks = build_chunks(root, max_chunk_size)

        retriever = build_bm25_index(chunks)
        save_bm25_index(retriever, chunks, output_path, max_chunk_size)

        if with_embeddings:
            vectors = embed_chunks(chunks)
            save_embeddings(vectors, output_directory)

        print(f"Indexed {len(chunks)} chunks into '{output_directory}'")

    except (FileNotFoundError, NotADirectoryError, ValueError) as exc:
        print(f"Error: {exc}")
    except Exception as exc:
        print(f"Indexing failed: {exc}")


def search(
    query: str,
    k: int = 5,
    output_directory: str = DEFAULT_INDEX_DIR,
    mode: str = "bm25",
) -> None:
    """Search the index for the top-k most relevant chunks for a query."""
    try:
        if not query.strip():
            print("Error: query must not be empty")
            return
        if k <= 0:
            print("Error: k must be a positive integer")
            return
        path = Path(output_directory)
        retriever, chunks = load_bm25_index(path)

        cache = load_cache(output_directory)
        key = cache_key(f"{mode}:{query}", k)

        if key in cache:
            print("(cache hit)")
            sources = cache[key]
        else:
            if mode == "hybrid":
                vectors = load_embeddings(output_directory)
                results = search_hybrid(retriever, vectors, chunks, query, k=k)
            else:
                results = search_bm25(retriever, query, chunks, k=k)

            sources = [s.model_dump() for s in chunks_to_sources(results)]
            cache[key] = sources
            save_cache(cache, output_directory)

        result = StudentSearchResults(
            search_results=[
                {
                    "question_id": str(uuid.uuid4()),
                    "question": query,
                    "retrieved_sources": sources,
                }
            ],
            k=k,
        )
        print(result.model_dump_json(indent=2))

    except FileNotFoundError as exc:
        print(f"Error: {exc}")
    except Exception as exc:
        print(f"Search failed: {exc}")


def search_dataset(
    dataset_path: str,
    k: int = 5,
    save_directory: str = "data/output/search_results/default",
    index_directory: str = DEFAULT_INDEX_DIR,
    mode: str = "bm25",
) -> None:
    """Run search for every question in a dataset file and save results."""
    # try:
    dataset_file = Path(dataset_path)
    if not dataset_file.exists():
        print(f"Error: dataset file '{dataset_path}' not found")
        return

    data = json.loads(dataset_file.read_text())
    dataset = RagDataset(**data)

    retriever, chunks = load_bm25_index(index_directory)
    vectors = load_embeddings(index_directory) if mode == "hybrid" else None

    Path(save_directory).mkdir(parents=True, exist_ok=True)

    search_results = []
    for question in tqdm(dataset.rag_questions, desc="Searching dataset"):
        if mode == "hybrid" and vectors is not None:
            results = search_hybrid(retriever, vectors, chunks, question.question, k=k)
        else:
            results = search_bm25(retriever, question.question, chunks, k=k)

        sources = chunks_to_sources(results)
        search_results.append(
            MinimalSearchResults(
                question_id=question.question_id,
                question=question.question,
                retrieved_sources=sources,
            )
        )

    output = StudentSearchResults(search_results=search_results, k=k)
    output_file = Path(save_directory) / dataset_file.name
    output_file.write_text(output.model_dump_json(indent=2))
    print(f"Saved student_search_results to '{output_file}'")

    # except json.JSONDecodeError as exc:
    #     print(f"Error: invalid JSON in dataset file: {exc}")
    # except FileNotFoundError as exc:
    #     print(f"Error: {exc}")
    # except Exception as exc:
    #     print(f"search_dataset failed: {exc}")


def answer(
    query: str,
    k: int = 5,
    output_directory: str = DEFAULT_INDEX_DIR,
    mode: str = "bm25",
) -> None:
    """Search for relevant context and generate an answer for a query."""
    try:
        if not query.strip():
            print("Error: query must not be empty")
            return
        if k <= 0:
            print("Error: k must be a positive integer")
            return

        retriever, chunks = load_bm25_index(output_directory)

        if mode == "hybrid":
            vectors = load_embeddings(output_directory)
            results = search_hybrid(retriever, vectors, chunks, query, k=k)
        else:
            results = search_bm25(retriever, query, chunks, k=k)

        answer_text = generate_answer(query, results)
        sources = chunks_to_sources(results)

        result = StudentSearchResultsAndAnswer(
            search_results=[
                MinimalAnswer(
                    question_id=str(uuid.uuid4()),
                    question=query,
                    retrieved_sources=sources,
                    answer=answer_text,
                )
            ],
            k=k,
        )
        print(result.model_dump_json(indent=2))

    except FileNotFoundError as exc:
        print(f"Error: {exc}")
    except Exception as exc:
        print(f"Answer failed: {exc}")


def answer_dataset(
    student_search_results_path: str,
    save_directory: str = "data/output/search_results_and_answer/default",
    index_directory: str = DEFAULT_INDEX_DIR,
) -> None:
    """Generate answers for previously computed search results."""
    # try:
    results_path = Path(student_search_results_path)
    if not results_path.exists():
        print(f"Error: '{student_search_results_path}' not found")
        return
    if results_path.is_file():
        result_files = [results_path]
    elif results_path.is_dir():
        result_files = sorted(results_path.glob("*.json"))
    else:
        print(f"Error: '{student_search_results_path}' is not a file or directory")
        return

    _, chunks = load_bm25_index(index_directory)
    lookup = build_chunk_lookup(chunks)

    Path(save_directory).mkdir(parents=True, exist_ok=True)
    for file in tqdm(result_files, desc="Generating answers"):
        data = json.loads(file.read_text())
        search_result = StudentSearchResults(**data)

        answered_results = []
        for item in search_result.search_results:
            matched_chunks = []
            for source in item.retrieved_sources:
                chunk = find_matching_chunk(lookup, source)
                if chunk is not None:
                    matched_chunks.append(chunk)

            answer_text = generate_answer(item.question, matched_chunks)
            answered_results.append(
                MinimalAnswer(
                    question_id=item.question_id,
                    question=item.question,
                    retrieved_sources=item.retrieved_sources,
                    answer=answer_text,
                )
            )

        output = StudentSearchResultsAndAnswer(
            search_results=answered_results, k=search_result.k
        )
        (Path(save_directory) / file.name).write_text(output.model_dump_json(indent=2))

    print(f"Saved {len(result_files)} answers to '{save_directory}'")

    # except json.JSONDecodeError as exc:
    #     print(f"Error: invalid JSON: {exc}")
    # except FileNotFoundError as exc:
    #     print(f"Error: {exc}")
    # except Exception as exc:
    #     print(f"answer_dataset failed: {exc}")


def evaluate(student_search_results_path: str, dataset_path: str) -> None:
    """Compute recall@k locally for debugging (not the official score)."""
    try:
        score = run_evaluate(student_search_results_path, dataset_path)
        print(f"Recall@k: {score}")
    except FileNotFoundError as exc:
        print(f"Error: {exc}")
    except Exception as exc:
        print(f"Evaluation failed: {exc}")


def serve(host: str = "127.0.0.1", port: int = 8000) -> None:
    """Start the local HTTP API (bonus 5)."""
    import uvicorn
    uvicorn.run("src.api:app", host=host, port=port)


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
            "serve": serve,
        }
    )


if __name__ == "__main__":
    main()
