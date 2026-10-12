from __future__ import annotations

import json
from pathlib import Path

import bm25s
from tqdm import tqdm

from .chunkers import chunk_file
from .models import Chunk

SUPPORTED_EXTENSIONS = {".py", ".md", ".txt"}


def build_chunks(root: Path, max_chunk_size: int) -> list[Chunk]:
    """Walk a corpus directory and chunk every supported file.

    Args:
        root: Root directory of the corpus.
        max_chunk_size: Maximum number of characters per chunk.

    Returns:
        The list of chunks produced across all files.

    Raises:
        FileNotFoundError: If ``root`` does not exist.
        NotADirectoryError: If ``root`` is not a directory.
    """
    if not root.exists():
        raise FileNotFoundError(f"Corpus directory does not exist: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"Corpus path is not a directory: {root}")

    files = sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
    )

    chunks: list[Chunk] = []
    for file_path in tqdm(files, desc="Chunking", unit="file"):
        try:
            chunks.extend(chunk_file(file_path, max_chunk_size))
        except Exception as exc:  # noqa: BLE001
            print(f"Warning: failed to process {file_path}: {exc}")
            continue
    return chunks


def build_bm25_index(chunks: list[Chunk]) -> bm25s.BM25:
    """Build an in-memory BM25 index from a list of chunks."""
    if not chunks:
        raise ValueError(
            "No chunks were produced. Check the corpus path and file extensions."
        )

    documents = [chunk.content for chunk in chunks]
    corpus_tokens = bm25s.tokenize(documents, stopwords="en")

    retriever = bm25s.BM25()
    retriever.index(corpus_tokens)
    return retriever


def save_bm25_index(
    retriever: bm25s.BM25,
    chunks: list[Chunk],
    output_path: Path,
    max_chunk_size: int,
) -> None:
    """Persist the BM25 index, the chunks, and indexing metadata to disk."""
    output_path.mkdir(parents=True, exist_ok=True)
    retriever.save(str(output_path))

    with (output_path / "chunks.json").open("w", encoding="utf-8") as file:
        json.dump([chunk.model_dump() for chunk in chunks], file)

    metadata = {
        "chunk_count": len(chunks),
        "max_chunk_size": max_chunk_size,
        "version": 1,
    }
    with (output_path / "metadata.json").open("w", encoding="utf-8") as file:
        json.dump(metadata, file, indent=4)
