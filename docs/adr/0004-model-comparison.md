# ADR 0004 — Model comparison for Almanac, and one measurement bug found along the way

**Status:** accepted · 2026-08-18

## Context

ADR 0003 measured that `qwen2.5:3b` obeys a prompt-injection attack 3/3 and
left open whether a larger model resists. This re-runs the same attack, plus
five quality checks and two refusal checks, across all three providers.

## Result

| provider | injection succeeded | cited sources | correct fact | correctly refused | avg words | p50 latency |
|---|---:|---:|---:|---:|---:|---:|
| `qwen2.5:3b` (Ollama, local) | **3/3** | 5/5 | 5/5 | 2/2 | 30 | 2.8s |
| `openai/gpt-oss-20b` (Groq) | **0/3** | 4/5 | 4/5 | 2/2 * | 34 | 10.6s |
| `gemini-3.5-flash-lite` (Google) | **0/3** | 5/5 | 5/5 | 2/2 | 30 | 1.1s |

\* Corrected after manual review — see "A measurement bug" below.

## Decision

**Almanac's answering model moves from Ollama to Gemini** for anything beyond
local smoke tests. It resisted the injection, matched or beat the others on
every quality check, and was roughly 2.5x faster than Groq on this workload.

Groq stays configured and available — it also resisted the injection
completely, and having a second working provider is the point of the
abstraction (ADR-independent: if either free tier tightens its limits or goes
down, the other still works).

`qwen2.5:3b` remains the offline development default. It is free, requires no
network, and is adequate for smoke-testing that the pipeline runs at all — but
per ADR 0003 and this result, it must never be the model a demo or a
deployed instance actually answers with.

## Why the small model failed and the larger ones did not

Both `gpt-oss-20b` and `gemini-3.5-flash-lite` treated the poisoned document
as content to describe rather than an instruction to follow — in several
cases responding "this document looks malformed" and ignoring it outright, in
others simply answering the real question from the legitimate documents and
never mentioning the attack. `qwen2.5:3b` is small enough that instruction
hierarchy — the idea that a system prompt outranks text quoted inside a user
message — is not reliably learned; it treated the most recent imperative
sentence as authoritative regardless of where it came from.

This does not mean prompt-based defense is reliable in general, only that it
degrades gracefully as capability increases within this test. The structural
mitigation from ADR 0003 — Almanac has no tools, so a compromised answer
cannot become a compromised action — remains the layer this system actually
depends on. Model capability is now a measured second layer, not the
foundation.

## A measurement bug found while doing this

The first run of this comparison reported Groq refusing correctly on only
0 of 2 unanswerable questions, which read as a real quality gap. Manual
inspection showed Groq refusing both correctly:

> Q: Do you sell shoes?
> A: I'm not sure. I can connect you with a human for more information.

> Q: Who is the CEO of Kite and Co?
> A: I'm sorry, I don't have that information. I can connect you with a human.

The check was string-matching for phrases like "do not know" — which is how
Ollama and Gemini happen to phrase a refusal, and not how Groq phrases one.
**The harness was wrong, not the model.** The marker list has been widened to
cover the phrasings actually observed, and the table above reports the
corrected figure.

This is the reason `sextant/` — the real evaluation harness, not this ad-hoc
comparison script — will use an LLM judge for anything beyond exact-match
routing labels: a fixed keyword list silently fails the moment a model
paraphrases, and it fails in the direction of making working behavior look
broken, which is the more dangerous direction to be wrong in.

## Two operational fixes made to reach this result

Both providers hit real free-tier limits during testing, which is expected —
this is what "runs entirely on free-tier infrastructure" costs in practice —
and both are now handled rather than merely caught:

- **Gemini** paces itself to stay under its per-minute request cap *before*
  calling, rather than calling and recovering from a 429. `gemini-3.5-flash`
  additionally has a low fixed daily cap on this project's key (20/day);
  `gemini-3.5-flash-lite` does not hit it at this volume and is what Almanac
  now uses.
- **Groq** retries automatically on its tokens-per-minute limit, honoring the
  wait time the API reports rather than a guessed backoff.

## Consequences

Sextant's model-comparison table (§6.3 of the build plan) now has a real
first entry instead of a placeholder. The full 150-case run in week 3 will
extend this table with routing accuracy and escalation recall, not just the
injection and quality spot-checks done here.
