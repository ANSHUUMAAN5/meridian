# ADR 0001 — Vectors live in Postgres, not a dedicated vector database

**Status:** accepted · 2026-08-17

## Context

Retrieval needs a vector store. The obvious candidates were Pinecone, Qdrant,
and Weaviate, all of which are purpose-built and would be easy to adopt.

Meridian is multi-tenant, and its central claim is that tenant isolation is
enforced by the database rather than by application code remembering to filter.

## Decision

Vectors are stored in the same Postgres instance as everything else, using
pgvector, with the `chunks` table under the same row-level security policy as
every other tenant-scoped table.

## Consequences

**The reason this matters more than performance.** External vector databases
separate tenants by *namespace* — a parameter the application passes on each
query. That is precisely the pattern this project argues against: a value a
developer must remember to supply, where forgetting it leaks data silently.

With pgvector, `app/rag/retriever.py` issues a similarity query with **no
tenant filter at all**. It cannot leak, because the policy applies to the
vector search the same way it applies to any other read. The isolation test
asserts exactly this.

**What we give up.** A dedicated vector database would scale further and offer
richer index tuning. At the point where vector search needs its own
infrastructure, this decision should be revisited — and a different isolation
story would be required to replace the one it provides.

**A second consequence, now measured.** Because vectors sit beside ordinary
columns, keyword search and vector search can be combined in a single query.
That turns out to matter: see ADR 0002.
