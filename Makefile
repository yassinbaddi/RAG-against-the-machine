



all: run

run: install
	uv run python src --max_chunk_size 2000

install:
	uv sync

t:
	uv run python test.py

clean:
	rm -rf __pycache__ */__pycache__ **/__pycache__

fclean:
	rm -rf .venv
