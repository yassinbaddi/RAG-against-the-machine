"""Simple local HTTP API for search and answer."""
from fastapi import FastAPI
from src.retriever import load_bm25_index, search_bm25, chunks_to_sources
from src.generator import generate_answer

app = FastAPI()
retriever, chunks = load_bm25_index("data/processed/bm25")


@app.get("/search")
def search(query: str, k: int = 5):
    results = search_bm25(retriever, query, chunks, k=k)
    return {"sources": [s.model_dump() for s in chunks_to_sources(results)]}


@app.get("/answer")
def answer(query: str, k: int = 5):
    results = search_bm25(retriever, query, chunks, k=k)
    answer_text = generate_answer(query, results)
    return {"answer": answer_text, "sources": [s.model_dump() for s in chunks_to_sources(results)]}
