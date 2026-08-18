"""Tenant-scoped vector search.

There is deliberately no `tenant_id` filter in the query below. That is the
point of putting vectors in Postgres rather than an external vector database:
the row-level security policy governs retrieval itself, so a missing or wrong
filter cannot leak another tenant's content. The isolation test suite asserts
exactly this by running the search with no filter at all.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models import Chunk, Document
from app.rag.embedder import embed_query


@dataclass(frozen=True)
class Retrieved:
    chunk_id: str
    document_id: str
    document_title: str
    ordinal: int
    content: str
    distance: float

    @property
    def similarity(self) -> float:
        """Cosine similarity in [0, 1]; pgvector returns cosine *distance*."""
        return 1.0 - self.distance


async def search(
    session: AsyncSession, query: str, *, top_k: int | None = None
) -> list[Retrieved]:
    top_k = top_k or get_settings().retrieve_top_k

    # bge is asymmetric: the query gets an instruction prefix, passages do not.
    vector = await asyncio.to_thread(embed_query, query)

    distance = Chunk.embedding.cosine_distance(vector).label("distance")
    stmt = (
        select(Chunk.id, Chunk.document_id, Document.title, Chunk.ordinal, Chunk.content, distance)
        .join(Document, Document.id == Chunk.document_id)
        .order_by(distance)
        .limit(top_k)
    )

    rows = (await session.execute(stmt)).all()
    return [
        Retrieved(
            chunk_id=str(r.id),
            document_id=str(r.document_id),
            document_title=r.title,
            ordinal=r.ordinal,
            content=r.content,
            distance=float(r.distance),
        )
        for r in rows
    ]
