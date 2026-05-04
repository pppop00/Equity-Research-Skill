---
schema_version: 1
description: The Anamnesis Pattern — a methodology for building agent harnesses that learn from their own past failures across sessions. The Equity Research Skill implements this pattern with INCIDENTS.md + frozen-at-boot + a P_INCIDENT_PRECHECK / P_INCIDENT_POSTCHECK bracket + adversarial review at Phase 5.7.
---

# The Anamnesis Pattern (as implemented by the Equity Research Skill)

> *Anamnesis* (Greek ἀνάμνησις, "recollection") — Plato's term for the soul calling to mind knowledge held from prior lives. The metaphor: every new agent context window is amnesiac. The pattern lets the agent recollect, every session, what it learned the hard way in every previous one.

This file describes *how the Equity Research Skill applies* the Anamnesis Pattern. The pattern itself is a general methodology; this skill is one instance of it. If you are integrating this skill into a larger harness (for example, the upstream `anamnesis-research` repository), the pattern composes naturally: the harness adds its own `INCIDENTS.md` entries on top of the skill's, and the bracket phases (`P_INCIDENT_PRECHECK` / `P_INCIDENT_POSTCHECK`) fire from the harness side rather than from `SKILL.md`.

## The problem the pattern solves

A new agent context window starts blank. The agent's tendency to repeat past mistakes — wrong-language report, skipped P0 gate, hand-written shortcut around a locked template — is bounded only by whatever rules are encoded in the live system prompt. Three common partial responses, all insufficient:

| Approach | What it does | Why insufficient |
|---|---|---|
| **Vector / RAG memory** | retrieves "relevant" past context on demand | the agent decides what to retrieve; misses what it doesn't know to ask for |
| **Session memory** | remembers within one chat | dies when the session ends |
| **Auto-logging traces** | stores everything | no signal-to-noise control; no enforcement loop; no relapse detection |

The Anamnesis Pattern closes the gap: every accumulated rule is read at the start of every session, verified at the end, and enforced as a delivery gate. Failure to obey a known rule is release-blocking, not advisory.

## The CFRV cycle (the 4 beats)

The pattern names four beats: **Curate · Freeze · Read · Verify**.

| Beat | Where it lives in this skill | Why this design |
|---|---|---|
| **1 · Curate** | A failure surfaces. A *human* (not the agent) writes one entry via `/log-incident <one-line description>`. Spec at `.claude/commands/log-incident.md`; backend at `tools/io/log_incident.py`. The model drafts the entry from the latest `workspace/{Company}_{Date}/` digest; the human confirms before append. | Human curation is the throttle that prevents memory inflation. Auto-logging projects collapse into noise within weeks; human gating forces *"is this worth being read every session forever?"* — almost everything fails that bar, and that is the point. |
| **2 · Freeze** | The entry appends to `INCIDENTS.md` (root of this repo) and is loaded **verbatim** into the session's system prompt at boot, alongside `MEMORY.md`. | Frozen, not retrieved. The agent doesn't decide whether to look up the rule — the rule is in front of it. The worst failures happen when the agent doesn't know to ask. |
| **3 · Read** | Every run's first phase, `P_INCIDENT_PRECHECK`, reads `INCIDENTS.md` end-to-end and acknowledges every entry before any phase work begins. Phases that match an accumulated incident (e.g. private-fund target → I-002 → Phase 5 / Phase 6) raise the bar — strict reading of the contract, no shortcuts. | Mandatory ack ensures the agent has actually processed the rule, not just been "shown" it. |
| **4 · Verify** | Every run's penultimate phase, `P_INCIDENT_POSTCHECK`, re-checks each entry's detection signal. Output: `workspace/{Company}_{Date}/incident_postcheck.json` with `pass | flagged` per incident. **Any flagged entry blocks delivery.** | A relapse on a known failure is more serious than a brand-new bug — the harness already knew, and the run still failed to comply. Hard halt, not warning. |

## The 5th axis — scheduled adversarial review

Orthogonal to memory, the pattern includes **named adversarial-review phases** at high-risk gates. In this skill, that gate is **Phase 5.7**, between the data validator (Phase 5.5) and the packaging validator (Phase 6). Two attackers fire in parallel:

- `agents/attackers/red_team_numeric.md` — attacks values, source chains, units, tolerance compliance, locked-template integrity carry-over, internal consistency.
- `agents/attackers/red_team_narrative.md` — attacks story-arc claims, hidden assumptions, missing counter-evidence, Porter score directionality, prediction-waterfall coherence, locked-template integrity.

These are **distinct** from QC peer review (`qc_macro_peer_a.md` / `qc_macro_peer_b.md` / `qc_porter_peer_a.md` / `qc_porter_peer_b.md` at Phases 2.6 and 3.5):

| | QC peers | Red-team attackers |
|---|---|---|
| Job | vote on agreement; weighted-average; flag deltas > tolerance | try to break the writer's claim; succeed when they find a defect |
| Output | score deltas → `qc_audit_trail.json` | challenge list with severity → `red_team_*_phase_5_7.json` |
| Loop budget | high (Phase 3.6 merge can incorporate up to dozens of items) | low (cap = 1 writer loop per phase) |
| Clean output is | suspicious — peers usually disagree on something | acceptable — a clean draft is a valid result |
| Risk if conflated | diluted votes mask single-source defects | adversarial loops drown the writer in subjective criticism |

A clean attacker output (zero findings) is a valid result. The harness must not pressure attackers to manufacture issues. Conversely, a draft that dismisses an attacker's critical finding without writing why is release-blocking.

## How this differs from other agent memory designs

| | Anamnesis Pattern | Vector RAG memory | Session memory | Auto-logging |
|---|---|---|---|---|
| Cross-session | ✓ frozen at boot | ✓ retrieved on query | ✗ | ✓ |
| Curated | ✓ human-gated | ✗ | n/a | ✗ |
| Read mandatory pre-run | ✓ | ✗ (only if model asks) | n/a | rarely |
| Verified post-run | ✓ | ✗ | ✗ | ✗ |
| Relapse blocks delivery | ✓ | ✗ | ✗ | ✗ |
| Scales as log grows | ✓ curation throttle | degrades — noise dilutes retrieval | n/a | degrades — noise floods log |
| Adversarial review | ✓ scheduled phases | ✗ | ✗ | ✗ |

The pattern's distinguishing claim: **a rule worth keeping is worth pre-checking, post-checking, and blocking on**. Anything weaker is a wish.

## Anti-patterns to avoid

1. **Auto-populated INCIDENTS.md.** Defeats curation. Within weeks the file is unreadable.
2. **Retrieval-based incident lookup** (RAG over INCIDENTS.md). Defeats the "agent doesn't know what it doesn't know" guarantee.
3. **Soft post-check** (warning instead of block). Defeats enforcement. Within months users learn to ignore the warnings.
4. **Adversarial agents that vote with QC peers.** Conflates falsification with consensus. Both jobs degrade.
5. **Editing past INCIDENTS entries.** Defeats append-only auditability. Supersede with a new entry that links back.
6. **Burying the post-check inside the report validator.** They are different jobs. Phase 6's `report_validator` checks "is this run's structure conformant"; `P_INCIDENT_POSTCHECK` checks "did this run relapse on a known failure". Combining them lets a clean structure check hide a relapse.

## Required files in this skill

| Concern | File |
|---|---|
| Append-only failure log | `INCIDENTS.md` |
| Frozen-at-boot project invariants | `MEMORY.md` |
| Pre-check phase | `P_INCIDENT_PRECHECK` (declared in `workflow_meta.json`, executed by orchestrator per `SKILL.md`) |
| Post-check phase | `P_INCIDENT_POSTCHECK` (same) |
| Adversarial agent — numeric | `agents/attackers/red_team_numeric.md` |
| Adversarial agent — narrative | `agents/attackers/red_team_narrative.md` |
| Curation entry-point | `.claude/commands/log-incident.md` (slash command) + `tools/io/log_incident.py` (collector) |
| Machine-readable phase contract | `workflow_meta.json` declares `phase_incident_precheck` first and `phase_incident_postcheck` after `phase_6` |

## Composing with the upstream `anamnesis-research` harness

When this skill is consumed as a submodule by the `anamnesis-research` harness:

- The harness's own `INCIDENTS.md` and `MEMORY.md` are loaded alongside this skill's. They compose; neither overrides.
- `P_INCIDENT_PRECHECK` and `P_INCIDENT_POSTCHECK` fire from the harness's orchestrator (which also handles `P_DB_INDEX` blocking on the post-check verdict). The skill's own copies of these phases are descriptive, not executive, in that mode.
- `Phase 5.7 RED TEAM` fires from this skill's contract; the harness adds `P10_7_RED_TEAM` (cards) on top. The two attackers (`red_team_numeric.md` / `red_team_narrative.md`) are the same agents, parameterised by the firing phase.
- The `/log-incident` slash command lives in this skill for standalone use and is overridden by the harness's version when both are mounted (the harness's collector also pulls run-event-log digests, which the standalone skill does not maintain).

For the full upstream pattern definition, see the `anamnesis-research` repo's `references/anamnesis_pattern.md`.
