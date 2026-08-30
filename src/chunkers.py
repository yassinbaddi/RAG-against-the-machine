import ast
from pathlib import Path
from models import Chunk


def split_text(
    file_path: str,
    content: str,
    max_chunk_size: int,
    start_offset: int = 0,
) -> list[Chunk]:
    chunks = []
    for start in range(0, len(content), max_chunk_size):
        end = min(start + max_chunk_size, len(content))
        chunks.append(
            Chunk(
                file_path=file_path,
                first_character_index=start_offset + start,
                last_character_index=start_offset + end - 1,
                content=content[start:end],
            )
        )
    return chunks


def chunk_file(
    file_path: Path,
    max_chunk_size: int,
) -> list[Chunk]:
    content = file_path.read_text(encoding="utf-8")

    if not content:
        return []

    if file_path.suffix == ".py":
        return chunk_python(str(file_path), content, max_chunk_size)

    if file_path.suffix == ".md":
        return chunk_markdown(str(file_path), content, max_chunk_size)

    return split_text(str(file_path), content, max_chunk_size)


def chunk_python(
    file_path: str,
    content: str,
    max_chunk_size: int,
) -> list[Chunk]:
    if len(content) <= max_chunk_size:
        return [
            Chunk(
                file_path=file_path,
                first_character_index=0,
                last_character_index=len(content) - 1,
                content=content,
            )
        ]

    try:
        tree = ast.parse(content)
    except SyntaxError:
        return split_text(file_path, content, max_chunk_size)

    line_offsets = [0]
    for line in content.splitlines(keepends=True):
        line_offsets.append(line_offsets[-1] + len(line))

    chunks: list[Chunk] = []

    for node in tree.body:
        start_index = line_offsets[node.lineno - 1]
        end_index = line_offsets[node.end_lineno] # type: ignore
        span = end_index - start_index

        if span > max_chunk_size:
            chunks.extend(split_text(file_path, content[start_index:end_index], max_chunk_size, start_index))
        else:
            chunks.append(
                Chunk(
                    file_path=file_path,
                    first_character_index=start_index,
                    last_character_index=end_index - 1,
                    content=content[start_index:end_index],
                )
            )

    return chunks

def chunk_markdown(
    file_path: str,
    content: str,
    max_chunk_size: int,
) -> list[Chunk]:
    if len(content) <= max_chunk_size:
        return [
            Chunk(
                file_path=file_path,
                first_character_index=0,
                last_character_index=len(content) - 1,
                content=content,
            )
        ]

    sections = []
    current_start = 0
    position = 0
    in_fence = False

    for line in content.splitlines(keepends=True):
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence

        if line.startswith("#") and not in_fence and position > current_start:
            sections.append((current_start, position))
            current_start = position

        position += len(line)

    if current_start < len(content):
        sections.append((current_start, len(content)))

    chunks: list[Chunk] = []
    for start, end in sections:
        section = content[start:end]
        if len(section) <= max_chunk_size:
            chunks.append(
                Chunk(
                    file_path=file_path,
                    first_character_index=start,
                    last_character_index=end - 1,
                    content=section,
                )
            )
        else:
            chunks.extend(split_text(file_path, section, max_chunk_size, start))

    return chunks


