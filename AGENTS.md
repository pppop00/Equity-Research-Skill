# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

## Commands

**Run all tests:**
```bash
python3 -m unittest discover -s tests -v
```

**Validate machine-readable workflow contract:**
```bash
python3 scripts/validate_workflow_meta.py --meta workflow_meta.json
```

**Run a single test class or method:**
```bash
python3 -m unittest tests.test_extract_report_template.TestSha256Stable -v
python3 -m unittest tests.test_extract_report_template.TestSha256Stable.test_cn_hash_matches_known_snapshot -v
```

**Extract the locked HTML skeleton (for auditing or Phase 5 generation):**
```bash
python3 scripts/extract_report_template.py --lang cn --sha256 -o workspace/MyCo_2026-04-08/_locked_cn_skeleton.html
python3 scripts/extract_report_template.py --lang en --sha256 -o workspace/MyCo_2026-04-08/_locked_en_skeleton.html
```

**US SEC EDGAR bundle (Agent 1 API-first path; orchestrator obtains a real user email per `SKILL.md` Step 0A.2, then passes `--user-agent`):**
```bash
python3 scripts/sec_edgar_fetch.py --ticker MSFT --user-agent "EquityResearchSkill/1.0 (you@example.com)" --report-date 2026-04-11 -o workspace/Microsoft_2026-04-11/sec_edgar_bundle.json
```

**Capture a new failure rule (`/log-incident`):**
```bash
# Backend that the /log-incident slash command shells out to. Read-only — does NOT modify INCIDENTS.md.
python3 tools/io/log_incident.py --collect --workspace workspace/<latest_run>/ --description "<one-line description>"
```

## Architecture

This is an **AI skill pack** built on the **Anamnesis Pattern** — cross-session institutional memory plus scheduled adversarial review. The "code" is primarily markdown files that instruct AI assistants (Codex, ChatGPT, Cursor) how to produce equity research reports under a closed-loop enforcement contract.

### Boot order (every session)

1. `SKILL.md` — orchestration entry; describes phases, agents, and the hard floor.
2. `MEMORY.md` — project invariants (P0 gates, locked-template rule, QC scoring math, Porter orientation, tolerances). Frozen into the session's system prompt.
3. `INCIDENTS.md` — append-only log of past failure modes, frozen into the same prompt. Read end-to-end at every session boot.
4. `workflow_meta.json` — machine-readable phase + gate contract. The `phase_order` list now brackets the research/report phases with `phase_incident_precheck` (first) and `phase_incident_postcheck` (last), and inserts `phase_5_7_red_team` between Phase 5.5 and Phase 6.

### The Anamnesis Pattern in this skill

Two interlocking loops plus an adversarial axis (see `references/anamnesis_pattern.md` for the full methodology):

- **Outer loop (across runs):** a real failure → `/log-incident` (human-gated curation, slash command spec at `.claude/commands/log-incident.md`, backend at `tools/io/log_incident.py`) → append to `INCIDENTS.md` → frozen into the next session's system prompt.
- **Inner loop (within one run):** `P_INCIDENT_PRECHECK` reads INCIDENTS.md → phases run with raised standards on matched incidents → adversarial review at Phase 5.7 → `P_INCIDENT_POSTCHECK` re-checks every rule → flagged blocks delivery.
- **Adversarial axis:** Two attackers fire in parallel at Phase 5.7 — `agents/attackers/red_team_numeric.md` (values, units, source chains, tolerance, locked-template integrity carry-over) and `agents/attackers/red_team_narrative.md` (hidden assumptions, missing counter-evidence, Porter directionality, prediction-waterfall coherence, locked-template integrity). They are **distinct** from QC peers (`qc_macro_peer_*`, `qc_porter_peer_*`): peers vote on agreement; attackers try to falsify and succeed when they find a defect. Critical from either attacker → loop the writer once (cap = 1); a second critical halts.

### Execution flow

1. **`workflow_meta.json`** — Machine-readable contract. Defines gate IDs, phase order (with the `phase_incident_*` bracket and `phase_5_7_red_team`), Phase 6 packaging profiles (`strict_18_full_qc_secapi`, `strict_17_full_qc_no_secapi`, `strict_13_fast_no_qc_secapi`, `strict_12_fast_no_qc_no_secapi`), and `memory_files` to freeze at session start.
2. **`SKILL.md`** — The orchestrator. **P_INCIDENT_PRECHECK** reads INCIDENTS.md before anything else. Then **P0 gates (Step 0A.0):** resolve report language (`en`/`zh`) per explicit rules **and** resolve SEC email or explicit decline when §0A.2 applies — **before** `workspace/`, Phase 1, or any research. Then set up `workspace/{Company}_{Date}/` and coordinate parallel agents.
3. **`agents/`** — Sub-task instruction files.
   - Phase 1 runs **Agents 1–3** in parallel (financials, macro, news); **Agent 4** (`edge_insight_writer.md`) may start once Agents 1 and 3 finish, while Agent 2 may still be running.
   - The standard full workflow then runs **dual QC on macro/Porter** followed by **`qc_resolution_merge.md`**.
   - Phase 5 uses **`report_writer_*.md`**.
   - **`final_report_data_validator.md`** (Phase 5.5) performs the final professional data validation pass.
   - **`agents/attackers/red_team_numeric.md`** + **`agents/attackers/red_team_narrative.md`** (Phase 5.7) fire in parallel as adversarial reviewers. Critical → loop Phase 5 once (cap = 1).
   - **`report_validator.md`** (Phase 6) performs final HTML structure / delivery validation and selects packaging profile from `workflow_meta.json`. The `report_validator` has hard preconditions in §0: locked skeleton must exist on disk; `validate_report_html.py` must have run with exit 0; profile must be from the whitelist; status must be `pass | warn | critical`.
   - **P_INCIDENT_POSTCHECK** runs after Phase 6, before delivery; flagged blocks handoff.
   - Workspace holds JSON throughout (plus HTML after Phase 5).
   - For Porter, scores are threat/pressure scores (**1–2 green low threat, 3 amber, 4–5 red high threat**); intense competitive rivalry must score high/red, not low/green. The Porter workflow is **draft → peer challenges → merge verdict → report wording**: only a QC item that **actually changes the score in the audit trail** may be written as **"from X to Y"**; reasoning-only QC that preserves the score must be written as **"maintain X"**, not as a fabricated score change.
   - For revenue prediction, treat `news_intel.json` as the **raw event layer** and `prediction_waterfall.json` as the **final model layer**: when `company_events_detail[]` is present, it should bridge `raw_impact_pct` to `final_impact_pct` using explicit timing / overlap / run-rate / probability / realization fields so QC and the red-team narrative attacker can recompute the final adjustment.
   - Skip adversarial QC and the Phase 5.7 red team **only in intentionally shortened runs** that the user explicitly requests.
4. **`references/`** — Domain knowledge: financial metric definitions, macro model formulas (φ, β), **sector regime / transmission** notes in `prediction_factors.md`, Porter Five Forces guide, style guides, and **`anamnesis_pattern.md`** for the institutional-memory + adversarial-review methodology.
5. **Phase 5 (report generation)** — The AI fills `{{PLACEHOLDER}}` markers in the locked HTML template from `agents/report_writer_cn.md` or `agents/report_writer_en.md`. It must use `scripts/extract_report_template.py` to get the canonical skeleton rather than copying from an existing workspace HTML.

### The locked HTML templates

`agents/report_writer_cn.md` and `agents/report_writer_en.md` each contain a single ` ```html ``` ` fenced block — the locked interactive HTML skeleton with Sankey, waterfall, and Porter radar charts using the **institutional-research palette** (deep navy `#1a2c4e` primary, deep forest green `#2e7d4f`, wine red `#a83232`, amber `#b8842a`, paper-toned background `#f5f3ee`; serif headings via Source Serif 4 / Noto Serif SC, sans body via Noto Sans / Noto Sans SC). **Do not change the structure**; only `{{PLACEHOLDER}}` substitutions are allowed.

`scripts/extract_report_template.py` extracts this block. The SHA256 hashes of the extracted bytes are pinned in `tests/test_extract_report_template.py`. If the templates change intentionally, update both the template and the expected hashes in `TestSha256Stable`.

### Key constraint: SHA256 snapshot tests

`TestSha256Stable` pins the exact bytes of both HTML templates. Any edit to the fenced block in `agents/report_writer_cn.md` or `agents/report_writer_en.md` will break these tests — this is intentional (audit trail). Update the expected digests in the test file when templates are deliberately changed.

### Hard floor (do not violate)

- Never skip `P_INCIDENT_PRECHECK` or `P_INCIDENT_POSTCHECK`.
- Never bypass an interactive P0 gate by inventing a value (auto-mode is not an override; see `INCIDENTS.md` I-001).
- Never edit the locked HTML template structure during Phase 5; never accept a simplified hand-written report regardless of target type (see `INCIDENTS.md` I-002).
- Never invent a packaging profile name or `report_validation.txt` status string.
- Never persist a user-supplied SEC EDGAR email beyond the run's HTTP `User-Agent`.
- Never auto-append to `INCIDENTS.md`; only the `/log-incident` slash command appends, and only after explicit user confirmation.
