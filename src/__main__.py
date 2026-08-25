
from pathlib import Path
import fire

ROOT = Path("data/raw/vllm-0.10.1")

def chuck_content(chunk_size, *file_type):
    chunks = []
    for file in ROOT.rglob("*"):
        if not file.is_file() or file.suffix not in {*file_type}:
            continue

        content = file.read_text()

        file_chunks = 0

        for start in range(0, len(content), chunk_size):
            end = min(start + chunk_size, len(content))

            chunks.append({
                "id": file_chunks,
                "file_path": str(file),
                "first_character_index": start,
                "last_character_index": end - 1,
                "content": content[start:end],
            })

            file_chunks += 1

        # print(f"{file.name}")
        # print(f"→ {file_chunks} chunks")

    return chunks

def main(max_chunk_size=2000):
    chunks = chuck_content(max_chunk_size ,".py")
    print(f"\nTotal chunks: {len(chunks)}", end="")
    chunks = chuck_content(max_chunk_size, ".md", ".txt")
    print(f"\nTotal chunks: {len(chunks)}")
    # print(max_chunk_size)


if "__main__" == __name__:
    fire.Fire(main)
