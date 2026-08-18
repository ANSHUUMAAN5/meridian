"""Embedding via fastembed (ONNX). No PyTorch, ~67MB of weights.

The model is loaded once per process and reused. Loading takes a few seconds,
so it happens on first use rather than at import time — that keeps test
collection and `--help` fast.
"""

from __future__ import annotations

import threading
from functools import lru_cache

from fastembed import TextEmbedding

from app.config import get_settings

_lock = threading.Lock()


@lru_cache(maxsize=1)
def _model() -> TextEmbedding:
    return TextEmbedding(model_name=get_settings().embed_model)


def tokenizer():
    """The model's own tokenizer, exactly as the encoder uses it.

    Note this instance has truncation ENABLED at 512 — that is correct for
    embedding, and wrong for measuring. Use `counting_tokenizer()` to measure.
    """
    return _model().model.tokenizer


@lru_cache(maxsize=1)
def counting_tokenizer():
    """An independent tokenizer with truncation disabled, for sizing chunks.

    The embedding tokenizer truncates at 512, so asking it how long a 3000-word
    document is returns 512. Measuring with it caps the measurement at the very
    limit being measured against, and a splitter built on it silently discards
    everything past the first chunk. This copy is deserialised from the same
    definition so the token counts still match the encoder exactly.
    """
    from tokenizers import Tokenizer

    t = Tokenizer.from_str(tokenizer().to_str())
    t.no_truncation()
    t.no_padding()
    return t


def count_tokens(text: str) -> int:
    """Real token length, uncapped."""
    return len(counting_tokenizer().encode(text).ids)


def embed(texts: list[str]) -> list[list[float]]:
    """Embed a batch. Order of the result matches the input."""
    if not texts:
        return []
    with _lock:  # ONNX session is not guaranteed thread-safe
        return [v.tolist() for v in _model().embed(texts)]


def embed_one(text: str) -> list[float]:
    return embed([text])[0]


def encoded_length_capped(text: str) -> int:
    """What the encoder will actually consume — capped at the model ceiling."""
    return len(tokenizer().encode(text).ids)


def embed_query(text: str) -> list[float]:
    """Embed a search query.

    bge models are trained with an asymmetric objective: queries are prefixed
    with an instruction, passages are not. Skipping this measurably degrades
    retrieval, and the failure is invisible — you just get slightly worse
    results forever.
    """
    return embed_one(f"Represent this sentence for searching relevant passages: {text}")
