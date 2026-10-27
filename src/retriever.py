from __future__ import annotations

import json
from pathlib import Path

import bm25s

from .models import Chunk, MinimalSource


def load_bm25_index(index_path: str) -> tuple[bm25s.BM25, list[Chunk]]:
    """Load a persisted BM25 index and its chunks.

    Raises:
        FileNotFoundError: If the index directory does not exist.
    """
    index_path = Path(index_path)
    if not index_path.exists():
        raise FileNotFoundError(f"Index does not exist: {index_path}")

    retriever = bm25s.BM25.load(str(index_path), load_corpus=False)

    with (index_path / "chunks.json").open("r", encoding="utf-8") as file:
        data = json.load(file)

    chunks = [Chunk.model_validate(item) for item in data]
    return retriever, chunks


def search_bm25(
    retriever: bm25s.BM25,
    query: str,
    chunks: list[Chunk],
    k: int = 4,
) -> list[Chunk]:
    """Return the top-k chunks for a query, ranked by BM25 relevance."""
    query = query.strip()
    if not query or k <= 0 or not chunks:
        return []

    k = min(k, len(chunks))
    query_tokens = bm25s.tokenize(query, stopwords="en")
    results, _scores = retriever.retrieve(query_tokens, k=k)
    indices = results[0]

    return [chunks[int(i)] for i in indices if 0 <= int(i) < len(chunks)]


def chunks_to_sources(chunks: list[Chunk]) -> list[MinimalSource]:
    """Convert chunks into their minimal source location representation."""
    return [
        MinimalSource(
            file_path=chunk.file_path,
            first_character_index=chunk.first_character_index,
            last_character_index=chunk.last_character_index,
        )
        for chunk in chunks
    ]


def build_chunk_lookup(chunks: list[Chunk]) -> dict[tuple[str, int, int], Chunk]:
    """Index chunks by (file_path, start, end) for O(1) source lookups."""
    return {
        (c.file_path, c.first_character_index, c.last_character_index): c
        for c in chunks
    }


def find_matching_chunk(
    lookup: dict[tuple[str, int, int], Chunk],
    source: MinimalSource,
) -> Chunk | None:
    """Find the chunk corresponding to a source location, if indexed."""
    key = (source.file_path, source.first_character_index, source.last_character_index)
    return lookup.get(key)
