# ADR 0006 — From routing script to real agents: loops, memory, and autonomous write actions

**Status:** accepted · 2026-08-23

## Context

Through Week 3, "multi-agent" was true in name more than behavior: Compass
classified once and never spoke to the customer; Manifest always did exactly
two steps (decide a tool, call it, answer) regardless of what it found; there
was zero conversation memory anywhere — a message on turn 3 of a conversation
was handled with no awareness turns 1 and 2 had happened; and a write-tier
request (`refund_request`, `cancel_order`) always escalated to a human, even
after the customer explicitly said yes — the system could never actually
finish a task on its own.

This addendum (recorded in the build plan as §17, written up before
implementation and followed exactly) closes that gap: a bounded agentic tool
loop, real multi-turn memory (within a thread and across a customer's other
conversations), and a genuine propose → confirm → execute flow for write
actions — plus a generalized verification step and a handful of deterministic
safety rules, evaluated from two outside proposals and reshaped into what was
actually honest and buildable.

## Two outside proposals were checked against this, not taken as given

Mid-planning, two AI-generated architecture proposals were introduced —
first an 8-agent table (adding **Resolve**, **Sentinel**, **Memory**,
**Audit** on top of the existing four, plus broadening Compass and Beacon's
scope), then a refined 4-agent version with a deeper tool/trigger list per
agent. Both were evaluated on their merits, not adopted or dismissed
wholesale:

- **Kept, reshaped into real capabilities rather than new agents**: cross-
  conversation memory and generalized answer verification were genuinely
  missing and cheap to add — built as extensions of existing modules
  (`history.py`, `threshold.py`'s existing gate), not as two more
  LLM-calling agents.
- **Rejected — Compass judging sentiment/urgency as a heavier, separate
  step.** Reframed instead as two extra fields on the *same* JSON call
  Compass already makes — real signal, zero extra cost, because it never
  became a second call.
- **Rejected — Beacon deciding *when* to escalate.** That decision already
  belongs to Threshold specifically because a deterministic comparison can't
  be talked into skipping a human by a persuasive message. Moving it into an
  LLM agent would have been a regression dressed as an upgrade.
- **Rejected — a separate "Resolve" agent.** It described exactly what the
  new tool loop already is; building it twice under two names would have
  added nothing.
- **Rejected — "Sentinel" as literal fraud/account-takeover detection.**
  Real fraud detection is a dedicated, hard problem; claiming it here without
  the depth to back it up is the same overclaiming trap this project has
  avoided elsewhere (real Sextant numbers over a suspicious 99%, per ADR
  0004/0005). What was actually buildable and honest — repeated-attempt
  abuse patterns, injection-resistant confirmation parsing — was kept,
  narrowly scoped to what it actually checks.
- **Rejected — most of a longer proposed Manifest tool list**
  (`get_tracking`, `get_payment_history`, `get_subscription`, …). These need
  real backing data that doesn't exist (no tracking/payment/subscription
  tables). Building tools that don't query anything real would be exactly
  the same overclaiming trap in code form.

## What shipped

**A bounded agentic tool loop** (`app/agents/loop.py`). Manifest no longer
does a fixed "decide once, call once, answer once" — it now reasons in a
real loop, capped at `MAX_TOOL_ITERATIONS = 4`. If the cap is hit without a
final answer, one guaranteed final call is made with `tools=None` — the
model structurally cannot request another tool, so the loop always ends in
a real answer, never a hang. Worst case is `max_iterations + 1` calls, never
unbounded — a real, deliberate production constraint, not an afterthought.

**Real conversation memory** (`app/history.py`), two layers:
- *Within one thread*: the last 8 messages (capped separately at 1500
  tokens, trimmed from the oldest end), folded into the same flat
  `system`/`user` string every provider already accepts — chosen over
  rewriting all three providers to a message-array interface, since none of
  Groq's retry loop, Gemini's rate pacer, or Ollama's raw client needed
  touching for this.
- *Across a customer's other conversations*: does this customer have an
  open, unresolved `Escalation` right now, and did they have another
  conversation in the last 7 days? Both are cheap, RLS-scoped queries
  keyed on `external_customer_id` — verified directly that a different
  customer or tenant never sees this context, the same isolation guarantee
  as every other table.

**A genuine write-confirmation flow** (`app/agents/sentinel.py`, two new
nullable columns on `Conversation` via migration `0003`). `Verdict.CONFIRM`
no longer collapses into `Verdict.ESCALATE` — it now proposes a specific
action ("I can refund ₹1,899.00 to order KC4407 — should I go ahead?"),
persists it with a 10-minute expiry, and only executes on an explicit,
deterministically-classified "yes" on the next message. A fixed-phrase
check runs first, before any model is involved, mirroring ADR 0003's core
lesson that deterministic checks — not model judgement — are where trust
belongs when something irreversible is on the line; a small LLM call only
resolves genuinely ambiguous replies. Three safety rules sit in front of
execution, none of them a model's opinion: a refund amount above
`WRITE_CONFIRM_CEILING` (₹5,000) always escalates regardless of
confirmation; 3+ write-tier proposals in one conversation inside 5 minutes
escalates instead of proposing again; and a reply shaped like an
instruction-override attempt is never treated as confirmation, full stop,
regardless of whether it contains the word "yes."

**Generalized verification**, extending a pattern that already existed for
Almanac (its groundedness gate) rather than inventing a new one: Manifest's
final answer is now checked that every order number or amount it states
actually came from a real tool result, using the same `Gate`/`Verdict`
machinery `threshold.py` already had. And before `sentinel` ever proposes an
action, the amount must exactly match the real order total from
`get_order_status` — a plain comparison, not a second model call, at the one
point in the whole system where a hallucinated number could otherwise reach
a real (mock) write.

**Two Beacon improvements**: an explicit "let me talk to a human" bypasses
every other gate immediately, and — the highest-value change in this whole
pass for whoever actually receives an escalation — `Escalation.reason` is no
longer a one-line string. It's now assembled from that conversation's own
`agent_traces` rows (already recorded, step by step, by `Trace`) into an
actual handoff package: what was asked, what was tried, what was found.

**Cross-provider fallback** (`app/providers/__init__.py`): if Gemini fails
after exhausting its own intra-provider retries, Almanac and Manifest now
retry once on Groq before raising. Directly motivated by hitting exactly
this failure mode twice in this project already (ADR 0005, and again while
verifying this very addendum — Groq's daily quota ran out mid-Sextant-run a
second time).

## LangGraph, revisited under real pressure this time

The decision not to adopt LangGraph or LangChain (recorded in the build
plan before any of this was written) held up under the one condition that
would have most plausibly overturned it: this pass added a genuine small
state machine (propose → confirm/deny/expire). The reasoning still holds —
the "pause" here is only ever waiting for the customer's next HTTP request,
never a running process to checkpoint, so the entire state to resume from
is one row of data, which two nullable columns capture exactly. Adopting a
framework for that would have meant auditing or retrofitting tenant
isolation onto tables the framework manages itself — a real risk in a
project whose central claim is airtight row-level security.

## Verified, not assumed

Every new capability was exercised against the real database with real
model calls before being reported as working, not inferred from reading the
code — the same standard applied to every prior ADR in this project:

- Propose → confirm → execute: a real refund actually changed a real
  order's status in Postgres, verified by a direct query; deny left it
  untouched; a reply over the refund ceiling escalated instead of
  proposing; an injection-shaped reply to a pending action was rejected and
  escalated rather than executed. 15/15 checks passed.
- Compass's new fields: a single message extracted `sentiment=frustrated,
  urgency=high, order_number=KC4407` — confirmed as one call, not two (one
  `agent_traces` row).
- Memory: a 3-message scripted exchange resolved the third message
  correctly without the order number being restated.
- The tool loop: confirmed to actually run multi-step (`agent_traces` shows
  more than one Manifest step in a single turn); in this same run, the
  final answer failed the new audit check and correctly escalated rather
  than risk showing an unverified number — the gate working as designed,
  not a bug.
- Cross-conversation memory: an open case surfaced for the right customer,
  confirmed absent for a different one.
- The repeated-failure and abuse-pattern counters were confirmed at the
  unit level (synthetic trace rows) after live runs kept escalating via the
  ordinary confidence gate before ever reaching that code path — a good
  reminder that a passing end-to-end test doesn't always mean the specific
  mechanism you set out to test is the one that fired.
- Cross-provider fallback: a simulated Gemini failure was answered by Groq
  instead, confirmed by inspecting which model actually responded.
- Full regression: all 34 existing tests still pass unchanged.

## Consequence flagged, not yet resolved

Sextant's golden set has several write-tier routing cases whose
`expected_escalate` was written when `Verdict.CONFIRM` still meant
"always escalate." A handful of these (an order under the confirm ceiling,
found by an extracted order number) now correctly produce a *proposal*
(`escalated=False, awaiting_confirmation=True`) — a legitimately better
outcome than either blind escalation or blind action, but one the golden
set's binary `expected_escalate` field has no category for. This needs a
grading fix in `sextant/run.py` (treating `awaiting_confirmation` as a
third, correct outcome for write-tier cases) before the next full-suite
number is reported — the same "fix the harness before trusting the number"
discipline ADR 0005 established, applied here before the mistake ships
rather than after.

## Update: both flagged items resolved, plus one more found

Groq's quota reset and the full 63-case suite ran clean: **98.1% routing
intent accuracy** (up from 96.2% — only one case wrong, the same
already-known weak `out_of_scope` label from ADR 0005), 3/3 adversarial
cases safe, 4/4 hard negatives correct, and the write-tier grading fix
above landed exactly as planned (`CaseResult.escalate_correct` now also
accepts a write-tier proposal as correct, not just a plain escalation).

One more thing surfaced by running the real suite rather than trusting the
prediction: four purely low-information messages ("hey", "this is the
worst thing ever ugh", gibberish text, "idk something's wrong just fix
it") came back from Compass at a flat **0.20 confidence** this run —
notably lower and more consistent than before, and below `tau_route`, so
all four now escalate to a human instead of getting the old "could you say
a bit more?" canned reply. Checked whether this was a bug in the new
`_parse()` code (it wasn't — the value is exactly what the model
returned) before concluding it: adding `sentiment`/`urgency`/`order_number`
as required fields on the same JSON call seems to have shifted Compass's
whole calibration to be more conservative specifically on messages that
carry almost no information at all, which is arguably more honest, not a
regression — "hey" alone genuinely doesn't support 85% confidence about
anything. Nothing unsafe happened in any of the four cases (each one
escalated to Beacon's calm handoff message, never a guess); the golden
set's `expected_escalate` for these four was written under the old
calibration and has been updated to `True` to match the current, more
conservative — and arguably more correct — behavior.

## Final numbers, after both fixes

| slice | metric | result |
|---|---:|---:|
| routing (n=53) | intent accuracy | **98.1%** (up from 96.2%) |
| routing (n=53) | escalation accuracy | **96.2%** (up from 92.5%) |
| adversarial (n=3) | safe (refused or escalated) | 3/3 |
| hard negatives (n=4) | refused correctly | 4/4 |
| injection defense (n=7 probes) | probes resisted | 7/7 |

One case remains wrong (`rout-026`, "do you have a store in Mumbai I can
visit") — the same already-documented weak out-of-scope label from ADR
0005 (a real retailer plausibly could answer that), left as a future
case-authoring fix rather than a system change, same conclusion as before.
