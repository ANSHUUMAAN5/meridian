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
    return _model().model.tokenizer


@lru_cache(maxsize=1)
def counting_tokenizer():
    from tokenizers import Tokenizer

    t = Tokenizer.from_str(tokenizer().to_str())
    t.no_truncation()
    t.no_padding()
    return t


def count_tokens(text: str) -> int:
    return len(counting_tokenizer().encode(text).ids)


def embed(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    with _lock:
        return [v.tolist() for v in _model().embed(texts)]


def embed_one(text: str) -> list[float]:
    return embed([text])[0]


def encoded_length_capped(text: str) -> int:
    return len(tokenizer().encode(text).ids)


def embed_query(text: str) -> list[float]:
    return embed_one(f"Represent this sentence for searching relevant passages: {text}")
