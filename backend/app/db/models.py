"""Database models.

Two conventions hold across this file:

1. Every table except `tenants` carries a non-null `tenant_id`. Row-level
   security policies (created in the Alembic migration, not here) key off it.
   SQLAlchemy has no concept of RLS — the policies are DDL, so they live in
   the migration and the models stay unaware of them. That is deliberate: the
   guarantee should not depend on the ORM doing anything.

2. `metadata` is reserved by SQLAlchemy's declarative base, so JSON columns of
   that name are mapped as `meta` in Python and "metadata" in Postgres.
"""

from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.config import get_settings
from app.db.base import Base

EMBED_DIM = get_settings().embed_dim


def _pk() -> Mapped[str]:
    return mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )


def _tenant_fk() -> Mapped[str]:
    return mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )


def _created() -> Mapped[datetime]:
    return mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


# ─────────────────────────────────────────────────────────────────────────────


class Tenant(Base):
    """One customer company. The only table without RLS — it is the root."""

    __tablename__ = "tenants"

    id: Mapped[str] = _pk()
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(60), nullable=False, unique=True)
    # Per-tenant overrides: thresholds, brand tone, hard escalation rules.
    settings: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    created_at: Mapped[datetime] = _created()


class User(Base):
    """A human on the tenant's support team — not an end customer."""

    __tablename__ = "users"

    id: Mapped[str] = _pk()
    tenant_id: Mapped[str] = _tenant_fk()
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, server_default="agent")
    created_at: Mapped[datetime] = _created()

    __table_args__ = (
        UniqueConstraint("tenant_id", "email", name="uq_users_tenant_email"),
        CheckConstraint("role in ('admin','agent')", name="ck_users_role"),
    )


class Document(Base):
    """An uploaded support document, before chunking."""

    __tablename__ = "documents"

    id: Mapped[str] = _pk()
    tenant_id: Mapped[str] = _tenant_fk()
    title: Mapped[str] = mapped_column(String(400), nullable=False)
    source: Mapped[str | None] = mapped_column(String(600))
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="pending")
    uploaded_at: Mapped[datetime] = _created()

    __table_args__ = (
        CheckConstraint(
            "status in ('pending','chunking','embedding','indexed','failed')",
            name="ck_documents_status",
        ),
    )


class Chunk(Base):
    """A slice of a document plus its embedding.

    Retrieval reads this table through RLS, so a vector search physically
    cannot return another tenant's chunks even with no WHERE clause.
    """

    __tablename__ = "chunks"

    id: Mapped[str] = _pk()
    tenant_id: Mapped[str] = _tenant_fk()
    document_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)  # position in the doc
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBED_DIM), nullable=False)
    meta: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, server_default="{}")

    __table_args__ = (
        Index("ix_chunks_tenant_document", "tenant_id", "document_id"),
        UniqueConstraint("document_id", "ordinal", name="uq_chunks_doc_ordinal"),
    )


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = _pk()
    tenant_id: Mapped[str] = _tenant_fk()
    # The tenant's own customer identifier — Meridian never owns end users.
    external_customer_id: Mapped[str | None] = mapped_column(String(200), index=True)
    created_at: Mapped[datetime] = _created()


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = _pk()
    tenant_id: Mapped[str] = _tenant_fk()
    conversation_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = _created()

    __table_args__ = (
        CheckConstraint("role in ('customer','assistant','system')", name="ck_messages_role"),
        Index("ix_messages_conversation_created", "conversation_id", "created_at"),
    )


class AgentTrace(Base):
    """One row per agent step. This table is the Trace product surface.

    Cost is stored per step rather than derived later, because the model behind
    a step can change between runs and the historical cost must not move.
    """

    __tablename__ = "agent_traces"

    id: Mapped[str] = _pk()
    tenant_id: Mapped[str] = _tenant_fk()
    conversation_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    message_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("messages.id", ondelete="CASCADE")
    )
    step: Mapped[int] = mapped_column(Integer, nullable=False)
    agent_name: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    model: Mapped[str | None] = mapped_column(String(120))

    input: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    output: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    # Null for steps that make no judgement (a tool call has no confidence).
    confidence: Mapped[float | None] = mapped_column(Float)

    latency_ms: Mapped[int | None] = mapped_column(Integer)
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    cost_usd: Mapped[float | None] = mapped_column(Numeric(12, 8))

    created_at: Mapped[datetime] = _created()

    __table_args__ = (
        CheckConstraint(
            "confidence is null or (confidence >= 0 and confidence <= 1)",
            name="ck_traces_confidence_range",
        ),
    )


class Escalation(Base):
    """A case handed to a human. Written only by Beacon."""

    __tablename__ = "escalations"

    id: Mapped[str] = _pk()
    tenant_id: Mapped[str] = _tenant_fk()
    conversation_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    reason: Mapped[str] = mapped_column(String(60), nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="open")
    assigned_to: Mapped[str | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    resolution_note: Mapped[str | None] = mapped_column(Text)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = _created()

    __table_args__ = (
        CheckConstraint("status in ('open','claimed','resolved')", name="ck_escalations_status"),
        Index("ix_escalations_tenant_status", "tenant_id", "status"),
    )


class Order(Base):
    """Stands in for the tenant's real commerce backend.

    Manifest reaches this through a tool interface, never directly, so swapping
    it for a real Shopify/internal API is an adapter rather than a rewrite.
    """

    __tablename__ = "orders"

    id: Mapped[str] = _pk()
    tenant_id: Mapped[str] = _tenant_fk()
    order_number: Mapped[str] = mapped_column(String(40), nullable=False)
    external_customer_id: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    items: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    total: Mapped[float | None] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3), nullable=False, server_default="INR")
    placed_at: Mapped[datetime] = _created()

    __table_args__ = (
        UniqueConstraint("tenant_id", "order_number", name="uq_orders_tenant_number"),
    )


# Tables that get row-level security. `tenants` is deliberately absent.
RLS_TABLES: tuple[str, ...] = (
    "users",
    "documents",
    "chunks",
    "conversations",
    "messages",
    "agent_traces",
    "escalations",
    "orders",
)
