"""Simple incremental indexing: skip unchanged files."""
import json
import hashlib
from pathlib import Path

MANIFEST_FILE = "manifest.json"


def file_hash(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def load_manifest(output_dir: str) -> dict:
    path = Path(output_dir) / MANIFEST_FILE
    if path.exists():
        return json.loads(path.read_text())
    return {}


def save_manifest(manifest: dict, output_dir: str) -> None:
    Path(output_dir, MANIFEST_FILE).write_text(json.dumps(manifest))


def has_changed(path: Path, manifest: dict) -> bool:
    return manifest.get(str(path)) != file_hash(path)
