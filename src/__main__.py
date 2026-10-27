"""Module entry point: `uv run python -m src <command> [options]`."""

import sys
from .cli import main

if __name__ == "__main__":
    # try:
    main()
    # except Exception as exc:
    #     print("Error:", exc, file=sys.stderr)
