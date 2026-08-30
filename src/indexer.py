import json
from pathlib import Path
from chunkers import chunk_file
from models import Chunk
import bm25s


def build_chunks(
    root: Path,
    max_chunk_size: int,
) -> list[Chunk]:
    chunks = []

    for file_path in root.rglob("*"):
        if not file_path.is_file():
            continue

        if file_path.suffix not in (".py", ".md"):
            continue

        chunks.extend(
            chunk_file(
                file_path,
                max_chunk_size,
            )
        )

    return chunks


def build_bm25_index(
    chunks: list[Chunk],
) -> bm25s.BM25:
    list_content = [chunk.content for chunk in chunks]

    corpus_tokens = bm25s.tokenize(list_content)

    retriever = bm25s.BM25()
    retriever.index(corpus_tokens)

    return retriever


def save_bm25_index(
    retriever: bm25s.BM25,
    chunks: list[Chunk],
    output_path: Path,
) -> None:
    output_path.mkdir(
        parents=True,
        exist_ok=True,
    )

    retriever.save(str(output_path))

    with (output_path / "chunks.json").open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            [chunk.model_dump() for chunk in chunks],
            file,
            ensure_ascii=False,
            indent=2,
        )