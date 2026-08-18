# ADR 0002 — Retrieval baseline, and why hybrid search is next

**Status:** accepted · 2026-08-17

## Context

Before adding any language model, retrieval was measured directly against 12
hand-written customer questions whose correct source document is known. This
is a deliberately small set; its purpose is to catch gross problems early, not
to be the evaluation suite (that is Sextant, week 3).

## What was measured

**Chunk size ablation** — five configurations, re-embedding the whole corpus
each time:

| chunk_tokens | overlap | chunks | hit@1 | hit@3 |
|---:|---:|---:|---:|---:|
| 400 | 80 | 15 | 7/12 | 10/12 |
| 250 | 50 | 27 | 8/12 | 10/12 |
| 150 | 40 | 40 | 6/12 | 11/12 |
| 100 | 30 | 58 | 6/12 | 10/12 |
| 64 | 20 | 96 | 8/12 | 9/12 |

Chunk size barely moves accuracy across a 6× range. **Chunking is not the
bottleneck**, which is worth knowing before spending time tuning it.

**hit@k at the chosen configuration** (250 tokens, 50 overlap):

| k | hit@k | still missing |
|---:|---:|---|
| 1 | 8/12 | Returns, Refunds, Damaged Items, Gift Cards |
| 3 | 10/12 | Damaged Items, Gift Cards |
| 6 | 11/12 | Gift Cards |
| 10 | 11/12 | Gift Cards |

## Decision

Ship week 1 on pure vector search at `top_k = 6`, chunked at 250/50.

## The finding that shapes week 3

One case fails at every k: *"does my voucher run out"* should retrieve **Gift
Cards**, and does not, even at k=10. Increasing depth cannot fix it — the
document is simply far from the query in vector space, because "voucher" and
"gift card" are not close under this embedding model. The other near-misses
are the same shape ("money reach my account" → Refunds).

These are **vocabulary mismatches**, and semantic similarity is the wrong tool
for them. A keyword index would match "voucher" trivially.

The next retrieval change is therefore **hybrid search** — Postgres full-text
search combined with vector distance — and not more chunk tuning. It is cheap
here precisely because both live in the same database (ADR 0001).

It is deliberately not being done now: without Sextant there is no way to show
it helped rather than merely changed the numbers on twelve hand-picked cases.
**Measure first, then optimise.**
