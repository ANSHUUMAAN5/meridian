# ADR 0007 — Retiring the dark instrument panel for a warm, Sierra-inspired identity

**Status:** accepted · 2026-09-08

## Context

Every screen built so far — the landing page, and all five console screens —
shared one dark "instrument panel" palette: near-black canvas, per-agent
neon accent colors, JetBrains Mono for every number. That was a deliberate
choice at the time (§7 of the build plan: "instrument panel, not marketing
warmth — the product is about knowing precisely what the machine did") and
it served the console well. It did not hold up as the *public* identity: it
read as generic dark-mode-SaaS rather than as something with a considered
point of view, and it invited the exact comparison the project had
originally set out to avoid making literally — cloning Sierra's identity
rather than learning from its structure.

Sierra's actual site was checked directly rather than worked from memory —
worth recording because two assumptions going in turned out wrong. It does
not use a serif display face (a clean grotesk sans, `gtAmerica`, appears in
both headlines and body copy, computed at `font-weight: 400`), and it is not
a flat "paper" color — it's real photography with a warm-neutral wash, a
frosted-glass chat panel floating on top of it, fully pill-shaped buttons,
and exactly one surprising saturated accent (a bold blue banner) breaking an
otherwise warm-neutral page. Per-feature sections each carry a small looping
illustrative animation, not one large scroll-jacked sequence.

## Decision

Rebuild the visual identity — landing page and all five console screens —
around a warm neutral palette, keeping the structural lesson from Sierra
("glass panel floating on a warm scene, one bold accent, pill controls,
small per-feature loops") without copying the specific execution ("real
photography of people," a licensed proprietary typeface).

**Typography.** Geist, already in use project-wide, stays as the only
typeface — headlines and body both. The first pass at this redesign tried a
serif display face (Fraunces) on the assumption that "warm palette" implied
"editorial serif." Checking the actual reference corrected that: Sierra's
own headlines are a plain grotesk. Keeping Geist is simultaneously the more
accurate read of the reference and the smaller, more honest change — no new
typeface family to introduce or justify.

**Palette.** Warm neutral base, warm charcoal ink instead of pure black.
Buttons and primary controls stay neutral — a dark charcoal pill on light
surfaces, a frosted-glass pill on photographic/textured ones — because that
is what Sierra's own buttons actually are; its blue is reserved for exactly
one loud, rare placement (a banner), never a default control color. Compass's
existing purple takes that same rare, one-off role here rather than becoming
the new button color: a single accent placement (the live-metrics eyebrow,
or one glow behind the hero panel), everywhere else quiet.

| Token | Value | Use |
|---|---|---|
| `--canvas` | `#F1EAD9` | page background |
| `--surface` | `#FAF6EC` | raised cards, panels |
| `--ink` | `#28241D` | primary text |
| `--muted` | `#7C7361` | secondary text |
| `--line` | `rgba(40,36,29,0.14)` | borders/hairlines |
| `--control` | `#28241D` on `#FAF6EC` | default button (charcoal pill) |
| `--accent-rare` | `#7C6BFF` (existing Compass purple) | the one loud placement, used once per screen at most |
| `--compass` | `#7A5C6E` | retuned from `#7C6BFF` |
| `--almanac` | `#3F6B7A` | retuned from `#3DA9FC` |
| `--manifest` | `#4B6C3A` | retuned from `#21C08B` |
| `--beacon` | `#B8792E` | retuned from `#F5A524` |
| `--danger` | `#A34632` | retuned, used for Sentinel/high-risk states |

**The four agent colors are retuned, not replaced.** Compass/Almanac/
Manifest/Beacon were tuned against `#0B0D0F`; used as-is on a light warm
ground they read as neon UI-kit defaults. Same four hue families (violet,
blue, green, amber), pulled into an earthy, desaturated register so they sit
inside the palette instead of fighting it. This was checked visually before
being decided — a mocked-up trace panel with the retuned colors in actual
badges and a confidence bar, not just swatches in a row.

**No real photography.** Sierra's hero is a photo of a person with a glass
chat panel over it. Meridian has no real photography, and stock or
generated photography would look exactly as cheap as it is, undermining the
"one person actually built this" story the project already cares about.
The structural pattern is kept — a frosted glass panel floating on a warm
textured scene — but what's inside the glass is the actual live routing
demo already built for the current landing page, not a staged photo. This
is more honest than the reference, not just a workaround for lacking assets.

**Motion stays scoped, not literal 3D.** Confirmed directly: depth and
motion (glass, blur, soft glow, floating cards, scroll reveals, small
per-feature looping animations) rather than real WebGL/3D. Sierra itself
doesn't use heavy 3D either — its "wow" is craft and restraint, not
polygon count. This also keeps the redesign inside Framer Motion and CSS,
the same toolchain already in use, instead of introducing Three.js and its
own bundle-size and performance risk for a portfolio project on a laptop
with 8GB of RAM.

**Buttons and cards go fully pill/rounded, with a frosted-glass treatment**
on floating surfaces (the hero panel, popover-style cards) — flat bordered
cards stay for dense console content where Sierra's own split between
marketing warmth and functional product screens argues for less ornament,
not more.

## Rejected alternatives

**Literal 3D (Three.js/WebGL).** Considered and explicitly rejected after
confirming what "3D" meant in practice — the user's own call, made after
seeing that Sierra doesn't need it either. A real 3D scene is a genuinely
new skill area with real performance and scope risk; the depth/motion
approach gets the same visual ambition without the new dependency.

**A full copy of Sierra's specific execution** (photography, its licensed
typeface, its exact section choreography). Rejected on the same grounds the
original build plan already argued for the landing page's structure: "take
Sierra's structure, not its identity — a clone reads as derivative." That
argument gets stronger, not weaker, once real photography and a warmer
palette are in play — those are the two things that would make a direct
copy actually recognizable as one.

**Keeping the dark palette and merely adding effects to it.** Considered as
"Option A" in the design pass and mocked up side by side with the warm
direction before this was decided. Rejected by preference, not by any
functional problem with it — the dark instrument-panel identity worked, but
read as generic rather than considered.

## Scope

Landing page and all five console screens (chat, traces, relay, knowledge,
sextant) move to the new palette together, so the product doesn't end up
half-redesigned. The light/dark toggle that existed in the original design
system (`[data-theme="light"]` as an override on a dark-first default) is
dropped rather than carried forward as a second theme to design against —
Sierra itself ships one considered theme, not two, and maintaining a dark
variant of every new glass/blur surface would roughly double this pass's
size for a toggle that saw little real use.

## Consequences

- Every shared token (`globals.css`) and the agent color map (`lib/agents.ts`)
  change, so this touches every screen that reads from them — the redesign
  has to land as one coordinated pass, not screen-by-screen, or the site
  will look like two different products mid-migration.
- The existing hero routing demo, trace-panel confidence bar, and badge
  components carry over structurally (same data, same behavior) with new
  colors and surfaces — this is a re-skin of working interaction patterns,
  not a rebuild of the underlying logic.
- Losing the dark theme is a real, if deliberate, regression for anyone who
  specifically preferred it. Revisiting a dark variant later is possible —
  the token structure this pass introduces is what would carry it — but it
  is explicitly not attempted in this pass.
