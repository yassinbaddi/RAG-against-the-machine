import json
from pathlib import Path

from chunkers import chunk_file
from models import Chunk


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


def save_chunks(
    chunks: list[Chunk],
    output_path: Path,
) -> None:
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    data = [
        chunk.model_dump()
        for chunk in chunks
    ]

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2,
        )