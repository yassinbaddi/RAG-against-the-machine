

from dataclasses import dataclass
from typing import Optional


@dataclass
class Chunk:
    id: int
    file_path: str
    content: str
    file_type: str
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    section: Optional[str] = None
