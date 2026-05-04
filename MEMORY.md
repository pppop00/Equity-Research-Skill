---
schema_version: 1
description: Project-level invariants for the Equity Research Skill. Frozen into the system prompt at session start, alongside INCIDENTS.md. Do not violate without an explicit user instruction in the same turn.
---

# Equity Research Skill — Project Memory

These rules are **load-bearing** and apply to every run. They are read once at session start and frozen into `meta/system_prompt.frozen.txt` (when the harness is in use). `INCIDENTS.md` is loaded alongside this file at the same moment and into the same frozen prompt — it carries the project's institutional memory of past failure modes (one entry per incident, with the load-bearing rule that prevents recurrence). Read both. The contracts compose: anything in `INCIDENTS.md` overrides nothing here, and nothing here waives anything in `INCIDENTS.md`.

## P0 gates — ordered, blocking, not skippable

The Equity Research Skill has **two** P0 interactive gates (see `SKILL.md` Step 0A):

1. **`P0_lang` (§0A.1)** — `report_language ∈ {en, zh}`. If not derivable from one of the explicit phrases listed in `SKILL.md` §0A.1, ask the bilingual gate question and **stop until answered**. Do not infer from chat language alone.
2. **`P0_sec_email` (§0A.2)** — only when `listing == US` AND `Mode A` (no PDFs uploaded). Ask for a real email or accept explicit decline. Reject obvious placeholders (`example.com`, `test@test`, `user@localhost`) with one re-ask. The email is **never** persisted — it lives only as a runtime arg to `scripts/sec_edgar_fetch.py`.

The only allowed `source` values for these two interactive gates are `user_response`, `explicit_phrase` (§0A.1 only), `skipped` / `declined` (§0A.2 only). Strings like `auto_mode_default`, `inferred_from_chat_language`, `inferred_from_locale`, `assumed`, or any free-form value are P0 violations. **Auto mode is not an override.** If neither a real user reply nor a whitelisted extra is available, halt and ask. (See `INCIDENTS.md` I-001.)

## Hard rules

- **Locked HTML template.** `agents/report_writer_cn.md` and `agents/report_writer_en.md` are SHA256-pinned in `tests/test_extract_report_template.py`. Phase 5 must extract the skeleton via `scripts/extract_report_template.py` and substitute `{{PLACEHOLDER}}` only; never edit structure. **There is no institution-compatible / private-company / scope-limited / simplified bypass.** Every run — public, private fund, hedge fund, family office, government entity, anything — fills the same locked skeleton. When issuer-level statements are unavailable, fill the locked sections with the best available proxies (AUM, strategy, top holdings, manager-level filings, peer macro) and label residual gaps inline; do not drop sections, shorten the template, or emit a hand-written page. (See `INCIDENTS.md` I-002.)
- **Packaging profiles (`structure_conformance.json -> profile`)** must be one of the four whitelisted in `workflow_meta.json -> packaging_profiles`: `strict_18_full_qc_secapi`, `strict_17_full_qc_no_secapi`, `strict_13_fast_no_qc_secapi`, `strict_12_fast_no_qc_no_secapi`. The picker is `(qc_mode, sec_api_mode)`. Inventing profile names (`institution_compat_*`, `private_company_*`, `scope_limited_*`, etc.) is a P6 violation.
- **`report_validation.txt`** top-line status is one of `pass | warn | critical`. `pass_with_scope_limitations`, `not_applicable`, `partial_pass`, `pass with scope limitations`, `institution-compatible pass`, `scope-limited pass` and similar freeform statuses are fabrications and the run is not deliverable.

## QC scoring math (Phase 3.6)

For each `(perspective, force)` pair: `weighted = 0.34·draft + 0.33·peer_a + 0.33·peer_b`.
- `delta = |weighted − draft|`
- If `delta > 1.00` → change score to `round(weighted)`, clamped to 1–5.
- If `delta ≤ 1.00` → keep draft, mark as "maintain X" (never fabricate "from X to Y").

Reasoning-only QC items must say "maintain X". Only QC items with an actual score change in the audit trail may say "from X to Y".

## Porter score orientation

Threat / pressure scale (not attractiveness):
- 1–2 = low threat / green
- 3 = mixed / amber
- 4–5 = high threat / red

Intense rivalry → high red; minimal competition → low green. Reverse this and the validator and red-team narrative attacker will catch it.

## Numerical reconciliation tolerances

When red-team numeric attackers (Phase 5.7) recompute values from source JSONs:

- margins / ratios / percentage points: ±0.5pp
- currency amounts: ±0.5% relative
- growth rates: ±0.5pp
- prices, share counts, or any value tagged `"exact": true`: 0 tolerance

A 0.4pp delta on a margin is *within tolerance* and is **not** a defect — flagging it wastes the writer's loop budget.

## Privacy invariants

- SEC EDGAR email is **never** persisted to disk beyond the run's `User-Agent` HTTP header. It lives only as a runtime arg to `scripts/sec_edgar_fetch.py`.
- Before serializing any `data_source` string, run `re.sub(r'\([^)]*@[^)]*\)', '()', value)` to strip embedded emails (User-Agent leak guard). Workspace JSONs and the final HTML must never contain a user-supplied email address.

## Failure caps

- Single subagent failure → 2 retries with same prompt, then halt.
- Phase 5.5 → Phase 5 (data validation fail → rewrite) cap = 2.
- **Phase 5.7 red team → Phase 5 (red-team critical) cap = 1.** A second critical from the red team after the loop = halt and surface to user.
- Subagent timeouts: research 600s / QC 180s; first timeout retries at ×1.5; second timeout = phase failure.
- Phase 6 has no auto-retry — failures surface to the user with paths and a "which upstream phase to re-run" question.
- `P_INCIDENT_POSTCHECK` flagged retry = 0 (relapse on a known failure is release-blocking; surface to user).

## Incident loop (load-bearing)

The Equity Research Skill implements the **Anamnesis Pattern** — see `references/anamnesis_pattern.md` for the full methodology.

- `P_INCIDENT_PRECHECK` runs **before** Step 0A. The orchestrator reads `INCIDENTS.md` end-to-end and acknowledges each entry (writing one event per entry to `workspace/{Company}_{Date}/meta/run.jsonl` if the harness layer maintains one, else to in-memory state). A run that did not pre-check is not deliverable.
- `P5_7_RED_TEAM` runs **after** Phase 5.5 (data validator) and **before** Phase 6 (packaging). Two adversarial agents fire in parallel: `agents/attackers/red_team_numeric.md` and `agents/attackers/red_team_narrative.md`. They are **not** QC peers — QC peers vote on agreement; attackers try to falsify. Critical findings loop the writer once (cap = 1); a second critical halts the run.
- `P_INCIDENT_POSTCHECK` runs **after** Phase 6 and **before** announcing delivery. The orchestrator re-reads `INCIDENTS.md` and confirms each entry's detection signal is green for this run. Output: `workspace/{Company}_{Date}/incident_postcheck.json`. Any `flagged` entry **blocks delivery** — the run's HTML is not handed off as complete; surface the relapse to the user with the exact incident id, the file path that contradicts it, and the rule that was violated.
- New failure modes are captured by the user via the `/log-incident` slash command (spec at `.claude/commands/log-incident.md`, backend at `tools/io/log_incident.py`). The model drafts an `INCIDENTS.md` entry; the user confirms; only then is it appended. **Append-only — never delete or rewrite past entries; supersede with a new entry if needed.**

## What this project does NOT do

- No skill self-improvement / DSPy / GEPA optimizer. Auditability beats agility — every numeric in the report is traceable to a source JSON, a frozen system prompt, and a pinned template SHA.
- No code-execution sandbox. Everything is a registered script under `scripts/` or `tools/`.
- No streaming UI. The deliverable is the workspace folder.
