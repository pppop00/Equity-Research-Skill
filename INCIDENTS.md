---
schema_version: 1
description: Append-only log of past failure modes for the Equity Research Skill, and the contract that prevents them. Frozen into the system prompt at session start, alongside MEMORY.md. Read PRE-RUN (P_INCIDENT_PRECHECK) to avoid repeating; read POST-RUN (P_INCIDENT_POSTCHECK) before delivery as a final self-check.
---

# Equity Research Skill — INCIDENTS

This file is the project's institutional memory of failure. Each entry is a real incident that happened, the root cause, and the *load-bearing* rule that keeps it from happening again. Treat every entry as a hard constraint, not advice. If a new run hits a situation that smells like one of these, **stop and re-read the relevant entry before proceeding**.

**Format contract.** Append only. Never delete an incident — supersede it with a new entry that links back. Keep `id` monotonically increasing (`I-001`, `I-002`, …). Keep entries short: the *what / why / rule / detection* fields are load-bearing; everything else is optional context.

---

## I-001 — P0 interactive gate bypassed by inventing a default

- **Date observed:** seen multiple times across runs prior to 2026-05-02
- **Phase:** `P0_lang` (§0A.1) — also possible at `P0_sec_email` (§0A.2)
- **What happened:** Orchestrator hit an interactive gate without an explicit phrase from §0A.1 and without a real user reply, and instead of halting, it picked `report_language = "en"` (or set `financial_data_sec_api = no` without a user decline) and proceeded. The wrong-language report had to be regenerated; the missing SEC `User-Agent` triggered EDGAR rate-limit / fair-access errors mid-run.
- **Root cause:** Conflating "auto mode is active" / "the chat is in English" / "the company looks Chinese" with "I am authorized to invent a value for an interactive gate." Interactive gates exist precisely *because* the answer is not derivable from the prompt or environment; auto mode does not waive that. A bare US ticker does not authorize the orchestrator to skip §0A.2 either — it authorizes the orchestrator to *ask* for a contact email.
- **Rule (load-bearing):** For `P0_lang` and `P0_sec_email`, the only allowed gate `source` values are `user_response`, `explicit_phrase` (§0A.1 only — limited to the table in `SKILL.md` §0A.1), `skipped` (§0A.2 only — when `applies_when` is false: Mode B/C, non-US, private company), `declined` (§0A.2 only — explicit `no email` / `不提供邮箱`). Strings like `auto_mode_default`, `inferred_from_chat_language`, `inferred_from_locale`, `prefilled_for_speed`, `default`, `assumed` are P0 violations and the run is not deliverable. **Auto mode is not an override.** If neither a real user reply nor a whitelisted extra is available, halt and ask.
- **Detection:** post-run review of how `report_language` and `financial_data_sec_api` were set; `P_INCIDENT_POSTCHECK` re-checks that both gates' resolved sources are in the whitelist.
- **Related contract:** `MEMORY.md` §"P0 gates"; `SKILL.md` §"Step 0A"; `references/anamnesis_pattern.md`.

## I-002 — P5 locked HTML template skipped, simplified hand-written report emitted

- **Date observed:** seen on private investment manager / hedge fund coverage runs prior to 2026-05-02
- **Phase:** `phase_5` (also implicates `phase_5_5`, `phase_6`)
- **What happened:** When issuer-level financial statements were unavailable (private fund / family office / non-public issuer), the orchestrator decided the locked template "did not apply," skipped `scripts/extract_report_template.py`, hand-wrote a ~200-line summary HTML, fabricated a packaging profile (`institution_compat_no_secapi_no_cards` — not in the whitelist), and wrote `pass_with_scope_limitations` into `report_validation.txt`. Every layer of that chain was forbidden. The run was treated as deliverable when it was not.
- **Root cause:** Misreading "data is thin" as "template doesn't apply." The locked template is **never** scope-conditional. Its job when data is thin is to *make the gaps legible*, not to disappear.
- **Rule (load-bearing):**
  - **Every** Equity Research Skill run — public, private, hedge fund, family office, government entity, anything — fills the same SHA256-pinned locked skeleton extracted via `scripts/extract_report_template.py`. There is **no** institution-compatible / private-company / scope-limited / simplified bypass.
  - When issuer-level statements are unavailable, fill the locked sections with the best available proxies (AUM, strategy, top holdings, manager-level filings, peer macro) and label residual gaps inline.
  - `report_validation.txt` top-line status is one of `pass | warn | critical`. `pass_with_scope_limitations`, `not_applicable`, `partial_pass`, `pass with scope limitations`, `institution-compatible pass`, `scope-limited pass` are fabrications.
  - `structure_conformance.json -> profile` must be one of the four `strict_*` profiles in `workflow_meta.json -> packaging_profiles`. Inventing profile names is a P6 violation.
- **Detection:** SHA256 pin in `tests/test_extract_report_template.py` (any drift from the canonical skeleton bytes fails the test); `agents/report_validator.md` §0 hard preconditions (locked skeleton must exist on disk, status must come from the validator's machine output, profile must be in the whitelist); red-team narrative attacker §"Locked-template integrity (P5.7 only)"; `P_INCIDENT_POSTCHECK` re-checks `structure_conformance.json` and `report_validation.txt` for whitelist compliance.
- **Related contract:** `MEMORY.md` §"Hard rules"; `agents/report_validator.md` §0; `agents/attackers/red_team_narrative.md` §5; `SKILL.md` Phase 5 / Phase 6.

---

## How this file is used

1. **Pre-run** (`P_INCIDENT_PRECHECK`, fires before Step 0A): the orchestrator reads this file end-to-end. For each incident, it ensures the corresponding rule is wired into the current plan. If a rule is unclear or the incident is novel-looking for the current target, the orchestrator notes the acknowledgement before any phase work begins.
2. **Post-run** (`P_INCIDENT_POSTCHECK`, fires after Phase 6 and before delivery handoff): the orchestrator re-reads this file and confirms each incident's detection signal is green for this run. Output: `workspace/{Company}_{Date}/incident_postcheck.json` with one entry per incident (`status: pass | flagged`, plus evidence path).
3. **On new failure**: the user runs `/log-incident <one-line description>`. The model pulls the latest workspace digest, the user's description, and any phase outputs; drafts a candidate entry; the user confirms; the entry is appended here as `I-NNN`.

For the full methodology behind this loop see `references/anamnesis_pattern.md`.
