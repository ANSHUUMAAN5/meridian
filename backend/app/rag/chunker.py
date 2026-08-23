from __future__ import annotations

import re
from dataclasses import dataclass

from app.config import get_settings
from app.rag.embedder import count_tokens, counting_tokenizer

_SENTENCE_END = re.compile(r"(?<=[.!?])\s+|\n{2,}")


@dataclass(frozen=True)
class Chunk:
    ordinal: int
    content: str
    tokens: int


def _split_sentences(text: str) -> list[str]:
    parts = [p.strip() for p in _SENTENCE_END.split(text.strip()) if p and p.strip()]
    return parts or ([text.strip()] if text.strip() else [])


def _hard_split(sentence: str, budget: int) -> list[str]:
    tok = counting_tokenizer()
    ids = tok.encode(sentence, add_special_tokens=False).ids
    out: list[str] = []
    for start in range(0, len(ids), budget):
        piece = tok.decode(ids[start : start + budget]).strip()
        if piece:
            out.append(piece)
    return out


def chunk_text(text: str, *, max_tokens: int | None = None, overlap: int | None = None) -> list[Chunk]:
    settings = get_settings()
    max_tokens = max_tokens or settings.chunk_tokens
    overlap = overlap if overlap is not None else settings.chunk_overlap

    if max_tokens > settings.embed_max_tokens:
        raise ValueError(
            f"chunk_tokens={max_tokens} exceeds the model ceiling of "
            f"{settings.embed_max_tokens}; chunks would be silently truncated"
        )
    if overlap >= max_tokens:
        raise ValueError("chunk_overlap must be smaller than chunk_tokens")

    text = text.strip()
    if not text:
        return []

    sentences: list[str] = []
    for s in _split_sentences(text):
        sentences.extend([s] if count_tokens(s) <= max_tokens else _hard_split(s, max_tokens))

    chunks: list[Chunk] = []
    current: list[str] = []
    current_tokens = 0

    def flush() -> None:
        nonlocal current, current_tokens
        if not current:
            return
        body = " ".join(current).strip()
        chunks.append(Chunk(ordinal=len(chunks), content=body, tokens=count_tokens(body)))
        carried: list[str] = []
        carried_tokens = 0
        for s in reversed(current):
            t = count_tokens(s)
            if carried_tokens + t > overlap:
                break
            carried.insert(0, s)
            carried_tokens += t
        current = carried
        current_tokens = carried_tokens

    for sentence in sentences:
        t = count_tokens(sentence)
        if current and current_tokens + t > max_tokens:
            flush()
        current.append(sentence)
        current_tokens += t

    if current:
        body = " ".join(current).strip()
        if body and (not chunks or chunks[-1].content != body):
            chunks.append(Chunk(ordinal=len(chunks), content=body, tokens=count_tokens(body)))

    return chunks
