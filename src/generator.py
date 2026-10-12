"""Answer generation using a small local causal language model (Qwen3-0.6B)."""

from __future__ import annotations

import textwrap
from typing import Any

from transformers import AutoModelForCausalLM, AutoTokenizer

from .models import Chunk

MODEL_NAME = "Qwen/Qwen3-0.6B"

_model_cache: dict[str, Any] = {}


def get_model_and_tokenizer() -> tuple[Any, Any]:
    """Lazily load and cache the tokenizer and model."""
    if "model" not in _model_cache:
        print("Loading model...")
        _model_cache["tokenizer"] = AutoTokenizer.from_pretrained(MODEL_NAME)
        _model_cache["model"] = AutoModelForCausalLM.from_pretrained(MODEL_NAME)
    return _model_cache["tokenizer"], _model_cache["model"]


def build_context(chunks: list[Chunk]) -> str:
    """Concatenate chunks into a single context block."""
    return "\n\n".join(
        f"--- SOURCE {i} ---\n{chunk.content}" for i, chunk in enumerate(chunks, start=1)
    )


def build_prompt(query: str, context: str) -> str:
    """Build the instruction prompt sent to the model."""
    return textwrap.dedent(
        f"""
        You are answering a question about the vLLM codebase.
        Use ONLY the following context to answer the question.
        If the context does not contain the answer, say so honestly.

        CONTEXT:
        {context}

        QUESTION:
        {query}

        ANSWER:
        """
    ).strip()


def generate_text(prompt: str, max_new_tokens: int = 256) -> str:
    """Generate text from a prompt using the cached model."""
    tokenizer, model = get_model_and_tokenizer()

    try:
        messages = [{"role": "user", "content": prompt}]
        text = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False,
        )
    except (TypeError, ValueError, AttributeError):
        text = prompt

    inputs = tokenizer(text, return_tensors="pt").to(model.device)
    outputs = model.generate(
        **inputs,
        max_new_tokens=max_new_tokens,
        do_sample=True,
        temperature=0.7,
    )

    input_length = inputs["input_ids"].shape[-1]
    new_tokens = outputs[0][input_length:]
    return tokenizer.decode(new_tokens, skip_special_tokens=True).strip()


def generate_answer(query: str, chunks: list[Chunk]) -> str:
    """Generate a grounded answer to a query from retrieved context chunks."""
    context = build_context(chunks)
    prompt = build_prompt(query, context)
    return generate_text(prompt)
