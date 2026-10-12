# from __future__ import annotations

# import ast
# import re
# from pathlib import Path

# from .models import Chunk


# def split_text(
#     file_path: str,
#     content: str,
#     max_chunk_size: int,
#     start_offset: int = 0,
# ) -> list[Chunk]:

#     if max_chunk_size <= 0:
#         raise ValueError("max_chunk_size must be greater than 0")

#     chunks: list[Chunk] = []

#     for start in range(0, len(content), max_chunk_size):
#         end = min(start + max_chunk_size, len(content))

#         chunks.append(
#             Chunk(
#                 file_path=file_path,
#                 first_character_index=start_offset + start,
#                 last_character_index=start_offset + end - 1,
#                 content=content[start:end],
#             )
#         )

#     return chunks


# # def chunk_python(
# #     file_path: str,
# #     content: str,
# #     max_chunk_size: int,
# # ) -> list[Chunk]:

# #     if max_chunk_size <= 0:
# #         raise ValueError("max_chunk_size must be greater than 0")

# #     if not content:
# #         return []

# #     try:
# #         tree = ast.parse(content)
# #     except SyntaxError:
# #         return split_text(
# #             file_path,
# #             content,
# #             max_chunk_size,
# #         )

# #     lines = content.splitlines(keepends=True)

# #     line_offsets = [0]

# #     for line in lines:
# #         line_offsets.append(line_offsets[-1] + len(line))

# #     chunks: list[Chunk] = []

# #     for node in tree.body:

# #         start = line_offsets[node.lineno - 1]
# #         end = line_offsets[node.end_lineno]

# #         piece = content[start:end]

# #         if not piece:
# #             continue

# #         if len(piece) <= max_chunk_size:

# #             chunks.append(
# #                 Chunk(
# #                     file_path=file_path,
# #                     first_character_index=start,
# #                     last_character_index=end - 1,
# #                     content=piece,
# #                 )
# #             )

# #         else:
# #             chunks.extend(
# #                 split_text(
# #                     file_path,
# #                     piece,
# #                     max_chunk_size,
# #                     start_offset=start,
# #                 )
# #             )

# #     return chunks


# def chunk_python(
#     file_path: str,
#     content: str,
#     max_chunk_size: int,
# ) -> list[Chunk]:

#     if max_chunk_size <= 0:
#         raise ValueError("max_chunk_size must be greater than 0")

#     if not content:
#         return []

#     try:
#         tree = ast.parse(content)
#     except SyntaxError:
#         return split_text(file_path, content, max_chunk_size)

#     lines = content.splitlines(keepends=True)
#     line_offsets = [0]
#     for line in lines:
#         line_offsets.append(line_offsets[-1] + len(line))

#     chunks: list[Chunk] = []
#     buffer_start = None
#     buffer_end = None

#     def flush_buffer():
#         if buffer_start is not None:
#             chunks.append(
#                 Chunk(
#                     file_path=file_path,
#                     first_character_index=buffer_start,
#                     last_character_index=buffer_end - 1,
#                     content=content[buffer_start:buffer_end],
#                 )
#             )

#     for node in tree.body:
#         start = line_offsets[node.lineno - 1]
#         end = line_offsets[node.end_lineno]

#         if end - start > max_chunk_size:
#             flush_buffer()
#             chunks.extend(
#                 split_text(file_path, content[start:end], max_chunk_size, start_offset=start)
#             )
#             buffer_start = None
#             continue

#         if buffer_start is None:
#             buffer_start, buffer_end = start, end
#             continue

#         if end - buffer_start <= max_chunk_size:
#             buffer_end = end
#         else:
#             flush_buffer()
#             buffer_start, buffer_end = start, end

#     flush_buffer()

#     if not chunks:
#         return split_text(file_path, content, max_chunk_size)

#     return chunks


# def chunk_markdown(
#     file_path: str,
#     content: str,
#     max_chunk_size: int,
# ) -> list[Chunk]:

#     if max_chunk_size <= 0:
#         raise ValueError("max_chunk_size must be greater than 0")

#     heading_pattern = re.compile(r"^#{1,6}\s+")

#     sections = []
#     current_start = 0
#     position = 0

#     for line in content.splitlines(keepends=True):
#         if heading_pattern.match(line) and position > current_start:
#             sections.append((current_start, position))
#             current_start = position
#         position += len(line)

#     if current_start < len(content):
#         sections.append((current_start, len(content)))

#     chunks: list[Chunk] = []
#     buffer_start = None
#     buffer_end = None

#     def flush():
#         if buffer_start is not None:
#             chunks.append(
#                 Chunk(
#                     file_path=file_path,
#                     first_character_index=buffer_start,
#                     last_character_index=buffer_end - 1,
#                     content=content[buffer_start:buffer_end],
#                 )
#             )

#     for start, end in sections:
#         if start >= end:
#             continue

#         if end - start > max_chunk_size:
#             flush()
#             buffer_start = None
#             chunks.extend(
#                 split_text(file_path, content[start:end], max_chunk_size, start_offset=start)
#             )
#             continue

#         if buffer_start is None:
#             buffer_start, buffer_end = start, end
#         elif end - buffer_start <= max_chunk_size:
#             buffer_end = end
#         else:
#             flush()
#             buffer_start, buffer_end = start, end

#     flush()

#     if not chunks:
#         return split_text(file_path, content, max_chunk_size)

#     return chunks



# def chunk_file(
#     file_path: Path,
#     max_chunk_size: int,
# ) -> list[Chunk]:

#     content = file_path.read_text(encoding="utf-8")

#     if not content:
#         return []

#     file_path_str = str(file_path)

#     if file_path.suffix == ".py":
#         return chunk_python(
#             file_path_str,
#             content,
#             max_chunk_size,
#         )

#     if file_path.suffix in {".md", ".txt"}:
#         return chunk_markdown(
#             file_path_str,
#             content,
#             max_chunk_size,
#         )

#     return split_text(
#         file_path_str,
#         content,
#         max_chunk_size,
#     )


from __future__ import annotations

import ast
from pathlib import Path

from langchain_text_splitters import (
    PythonCodeTextSplitter,
    RecursiveCharacterTextSplitter,
)

from .models import Chunk


def split_text(
    file_path: str,
    content: str,
    max_chunk_size: int,
    start_offset: int = 0,
) -> list[Chunk]:
    """Naively split text into fixed-size, non-overlapping windows.

    Used both as a fallback (unparsable Python, generic files) and as a
    safety net to clip any chunk that exceeds ``max_chunk_size``.
    """
    if max_chunk_size <= 0:
        raise ValueError("max_chunk_size must be greater than 0")

    chunks: list[Chunk] = []
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


def _enforce_max_size(chunks: list[Chunk], max_chunk_size: int) -> list[Chunk]:
    """Guarantee that no chunk exceeds max_chunk_size.

    langchain splitters only guarantee a *soft* limit: an atomic unit
    (one long line, one long paragraph) can still come out oversized.
    The grader rejects any source longer than max_context_length, so we
    re-split anything that slipped through.
    """
    enforced: list[Chunk] = []
    for chunk in chunks:
        if len(chunk.content) <= max_chunk_size:
            enforced.append(chunk)
            continue
        enforced.extend(
            split_text(
                chunk.file_path,
                chunk.content,
                max_chunk_size,
                start_offset=chunk.first_character_index,
            )
        )
    return enforced


def chunk_python(file_path: str, content: str, max_chunk_size: int) -> list[Chunk]:
    """Split Python source code along syntactic boundaries."""
    if max_chunk_size <= 0:
        raise ValueError("max_chunk_size must be greater than 0")
    if not content:
        return []

    try:
        ast.parse(content)
    except SyntaxError:
        return split_text(file_path, content, max_chunk_size)

    splitter = PythonCodeTextSplitter(
        chunk_size=max_chunk_size,
        chunk_overlap=0,
        add_start_index=True,
    )
    documents = splitter.create_documents([content])

    chunks = [
        Chunk(
            file_path=file_path,
            first_character_index=doc.metadata["start_index"],
            last_character_index=doc.metadata["start_index"] + len(doc.page_content) - 1,
            content=doc.page_content,
        )
        for doc in documents
    ]
    return _enforce_max_size(chunks, max_chunk_size)


def chunk_markdown(file_path: str, content: str, max_chunk_size: int) -> list[Chunk]:
    """Split Markdown/text content along heading and paragraph boundaries."""
    if max_chunk_size <= 0:
        raise ValueError("max_chunk_size must be greater than 0")
    if not content:
        return []

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=max_chunk_size,
        chunk_overlap=0,
        separators=["\n## ", "\n# ", "\n\n", "\n", " ", ""],
        add_start_index=True,
    )
    documents = splitter.create_documents([content])

    chunks = [
        Chunk(
            file_path=file_path,
            first_character_index=doc.metadata["start_index"],
            last_character_index=doc.metadata["start_index"] + len(doc.page_content) - 1,
            content=doc.page_content,
        )
        for doc in documents
    ]
    return _enforce_max_size(chunks, max_chunk_size)


def chunk_file(file_path: Path, max_chunk_size: int) -> list[Chunk]:
    """Dispatch chunking strategy based on file extension."""
    content = file_path.read_text(encoding="utf-8")
    if not content:
        return []

    file_path_str = str(file_path)

    if file_path.suffix == ".py":
        return chunk_python(file_path_str, content, max_chunk_size)
    if file_path.suffix in {".md", ".txt"}:
        return chunk_markdown(file_path_str, content, max_chunk_size)
    return split_text(file_path_str, content, max_chunk_size)
