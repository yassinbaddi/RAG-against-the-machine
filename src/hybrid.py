"""Simple hybrid retrieval: merge BM25 and embedding results."""
from src.models import Chunk
from src.retriever import search_bm25
from src.embeddings import search_embeddings


def search_hybrid(retriever, vectors, chunks: list[Chunk], query: str, k: int = 5) -> list[Chunk]:
    """Combine lexical and semantic results, keeping order of first appearance."""
    lexical = search_bm25(retriever, query, chunks, k=k)
    semantic = search_embeddings(query, vectors, chunks, k=k) if vectors is not None else []

    merged = []
    seen = set()
    # interleave: one from each list at a time
    for a, b in zip(lexical, semantic):
        for c in (a, b):
            key = (c.file_path, c.start, c.end)
            if key not in seen:
                seen.add(key)
                merged.append(c)

    return merged[:k]
