from pathlib import Path
import fire
from indexer import build_chunks, save_chunks


def index(
    max_chunk_size: int = 2000,
) -> None:
    root = Path("test_vllm")

    chunks = build_chunks(
        root,
        max_chunk_size,
    )

    output_path = Path(
        "data/processed/chunks.json"
    )

    # save_chunks(
    #     chunks,
    #     output_path,
    # )

    print(f"Indexed {len(chunks)} chunks.")
    print(f"Saved to {output_path}")


def main() -> None:
    fire.Fire({"index": index})


if __name__ == "__main__":
    main()