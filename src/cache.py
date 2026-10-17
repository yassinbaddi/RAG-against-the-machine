"""Simple query result cache stored as a JSON file."""
import json
from pathlib import Path

CACHE_FILE = "cache.json"


def load_cache(output_dir: str) -> dict:
    path = Path(output_dir) / CACHE_FILE
    if path.exists():
        return json.loads(path.read_text())
    return {}


def save_cache(cache: dict, output_dir: str) -> None:
    Path(output_dir, CACHE_FILE).write_text(json.dumps(cache))


def cache_key(query: str, k: int) -> str:
    return f"{query.strip().lower()}::{k}"
