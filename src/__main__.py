from pathlib import Path

import fire
from retriever import search_bm25

from indexer import build_chunks, save_bm25_index, build_bm25_index


def index(
    max_chunk_size: int = 2000,
) -> None:
    root = Path("test_vllm")
    output_path = Path("data/processed/bm25")

    chunks = build_chunks(
        root,
        max_chunk_size,
    )

    retriever = build_bm25_index(chunks)

    save_bm25_index(
        retriever,
        chunks,
        output_path,
    )

    print(f"Indexed {len(chunks)} chunks.")
    print(f"Saved to {output_path}")


def main() -> None:
    fire.Fire({"index": index})


if __name__ == "__main__":
    main()