"""Simple semantic search using sentence embeddings."""
from pathlib import Path
import numpy as np
from sentence_transformers import SentenceTransformer
from src.models import Chunk

MODEL_NAME = "all-MiniLM-L6-v2"


def embed_chunks(chunks: list[Chunk]) -> np.ndarray:
    """Turn all chunks into vectors."""
    model = SentenceTransformer(MODEL_NAME)
    texts = [c.content for c in chunks]
    return model.encode(texts, normalize_embeddings=True)


def save_embeddings(vectors: np.ndarray, output_dir: str) -> None:
    np.save(Path(output_dir) / "embeddings.npy", vectors)


def load_embeddings(output_dir: str) -> np.ndarray | None:
    path = Path(output_dir) / "embeddings.npy"
    if not path.exists():
        return None
    return np.load(path)


def search_embeddings(query: str, vectors: np.ndarray, chunks: list[Chunk], k: int = 5) -> list[Chunk]:
    """Return the k most similar chunks to the query."""
    model = SentenceTransformer(MODEL_NAME)
    q_vec = model.encode([query], normalize_embeddings=True)[0]
    scores = vectors @ q_vec  # cosine similarity (vectors are normalized)
    top_idx = np.argsort(scores)[::-1][:k]
    return [chunks[i] for i in top_idx]
