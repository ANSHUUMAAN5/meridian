"""Turn an uploaded document into searchable chunks.

Runs inside the caller's tenant-scoped session, so every row written inherits
that tenant and the RLS WITH CHECK clause rejects anything that doesn't. The
tenant id is therefore never a parameter to these functions — it comes from
the session, which comes from a signed token.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Chunk, Document
from app.rag.chunker import chunk_text
from app.rag.embedder import embed


@dataclass(frozen=True)
class IngestResult:
    document_id: str
    title: str
    chunks: int
    tokens: int


async def ingest_document(
    session: AsyncSession,
    *,
    tenant_id: str,
    title: str,
    text: str,
    source: str | None = None,
) -> IngestResult:
    """Chunk, embed, and store one document.

    Status moves pending -> chunking -> embedding -> indexed so a partially
    processed document is distinguishable from a finished one in the UI, and a
    crash leaves evidence of where it stopped rather than a silent gap.
    """
    doc = Document(tenant_id=tenant_id, title=title, source=source, status="chunking")
    session.add(doc)
    await session.flush()  # assigns doc.id without ending the transaction

    try:
        pieces = chunk_text(text)
        if not pieces:
            doc.status = "failed"
            await session.flush()
            return IngestResult(str(doc.id), title, 0, 0)

        doc.status = "embedding"
        await session.flush()

        # Embedding is CPU-bound ONNX work; keep the event loop responsive.
        vectors = await asyncio.to_thread(embed, [p.content for p in pieces])

        session.add_all(
            [
                Chunk(
                    tenant_id=tenant_id,
                    document_id=doc.id,
                    ordinal=p.ordinal,
                    content=p.content,
                    embedding=v,
                    meta={"tokens": p.tokens, "title": title},
                )
                for p, v in zip(pieces, vectors, strict=True)
            ]
        )

        doc.status = "indexed"
        await session.flush()
        return IngestResult(str(doc.id), title, len(pieces), sum(p.tokens for p in pieces))

    except Exception:
        doc.status = "failed"
        raise


async def document_stats(session: AsyncSession, document_id: str) -> tuple[str, int]:
    """(status, chunk_count) — used by the ingestion progress UI."""
    doc = (await session.execute(select(Document).where(Document.id == document_id))).scalar_one()
    n = len((await session.execute(select(Chunk.id).where(Chunk.document_id == document_id))).all())
    return doc.status, n
