# Meridian

**Multi-tenant, multi-agent customer support platform.** Any company uploads their
support documents and connects their order data; Meridian routes each customer
question to the right specialist agent, refuses to guess when it isn't confident,
and records every decision it makes.

> Status: **under construction** — week 1 of 6. Metrics below are placeholders
> until the evaluation suite runs (week 5). Whatever it actually reports is what
> gets published here.

## The idea

A meridian is the reference line everything is measured against. This system's
core mechanic is a confidence **threshold** — a line. Above it, the system acts
on its own. Below it, a human takes over.

## Components

**Four agents** — each has a different model, prompt, and *tool access*:

| | Role |
|---|---|
| **Compass** | Reads the message, decides who handles it. Returns intent + confidence. |
| **Almanac** | Answers from the tenant's documents, with citations. Cannot read orders. |
| **Manifest** | Answers account questions via tool calls. Cannot read documents. |
| **Beacon** | Escalates to a human with the full reasoning attached. |

**Four systems** — plain code, no LLM:

| | Role |
|---|---|
| **Threshold** | The confidence gate and risk tiers. Deliberately *not* an agent — a comparison should be deterministic. |
| **Trace** | Records every step: agent, model, confidence, latency, tokens, cost. |
| **Sextant** | The evaluation harness. Replays labeled cases and scores the system. |
| **Relay** | The human escalation inbox. Resolutions become new labeled cases. |

## What makes it different from a support chatbot

1. **Tenant isolation at the database layer** — Postgres row-level security, with
   an automated cross-tenant test suite. A broken `WHERE` clause still cannot leak.
2. **Confidence gating with risk tiers** — reads run autonomously; writes require
   elevated confidence plus confirmation, or they escalate.
3. **A labeled evaluation suite in CI** — routing accuracy, escalation recall, and
   hallucination rate on hard negatives, enforced on every change.

## Stack

FastAPI · Next.js · Postgres + pgvector (Neon) · fastembed (ONNX) ·
Groq + Gemini free tiers · Vercel + Hugging Face Spaces.
Runs end to end at **$0.00** — no paid inference, no credit card.

## Local setup

```bash
git clone <repo> && cd meridian
bash scripts/install-hooks.sh      # secret guard — do this first
cp .env.example .env               # then fill it in
```

`.env` is gitignored and a pre-commit hook rejects key-shaped strings. Nothing
in this repo requires a paid account.
