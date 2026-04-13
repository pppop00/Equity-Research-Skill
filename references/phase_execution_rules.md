# Phase Execution Rules (Detailed)

This file stores detailed execution constraints that were intentionally moved out of `SKILL.md`.
`SKILL.md` stays as the orchestration contract (inputs, outputs, agent call, gate), while this file carries cross-cutting rules and orchestrator-inline phase details.

Agent-specific rules live in `agents/*.md` — each agent file now includes a "Downstream Contract" section covering its output obligations and how downstream phases consume it.

---

## Phase 1: Orchestration Details

- Start Agent 1, Agent 2, and Agent 3 in parallel when possible.
- Agent prompts must always include `Report language: {en|zh}`.
- Agent 4 may start after Agent 1 and Agent 3 finish; Agent 2 may still be running.
- Do not leave Phase 1 until all of `financial_data.json`, `macro_factors.json`, and `news_intel.json` exist.
- **Post-collection reconciliation (orchestrator duty):** After `financial_data.json` and `news_intel.json` exist, re-check `macro_factors.json -> macro_regime_context` against filing geography and industry news. If materially inconsistent, revise context/commentary or rerun Agent 2.

---

## Phase 2: Financial Analysis (Orchestrator Inline)

Phase 2 is executed by the orchestrator, not a subagent, so its detailed rules stay here.

### Fiscal-Year Alignment

- Year labels in Section II and KPI cards must align with `financial_data.json`:
  - `income_statement.current_year`
  - `income_statement.prior_year`
- YoY always means these two consecutive full fiscal years.
- If latest year has only interim data, either:
  - keep full-year comparison and include lag explanation in `notes[]`, or
  - add a clearly labeled interim-vs-prior-interim block.

### Table and Card Contracts

- Section II metrics table final column (`同比变动` / `YoY movement`) must be qualitative verdict text, not raw numeric delta. Use controlled vocabulary from `references/financial_metrics.md`.
- Latest operating update must:
  - use `latest_interim` from Agent 1 as primary structured source,
  - lead with covered period,
  - prefer YoY headline unless filing context explicitly centers QoQ.
- Geographic revenue card must be factual and filing-grounded; avoid meta/disclaimer filler text.
- KPI third card (FCF): if both years negative but narrowing toward zero, use `neutral-kpi` class, not `up`. See `references/financial_metrics.md` and `references/report_style_guide_cn.md`.

### Narrative Evidence and Language

- Valuation statements require evidence from `financial_analysis.json -> valuation` or explicitly cited appendix data.
- Do not present live-market conclusions as facts when source fields are null.
- All HTML-bound narrative strings must be plain text (no Markdown symbols).
- Language lock:
  - `report_language = en` -> English narrative fields
  - `report_language = zh` -> Chinese narrative fields

### Investment Summary Structure

- `summary_para_1`: business + latest financial performance (zh: 160-200 chars; en: 90-130 words).
- `summary_para_2`: edge insight interpretation and implication from `edge_insights.json -> summary_para_2_draft`.
- `summary_para_3`: thesis/catalysts with constraints.
- `summary_para_4`: industry position reconciled with filings and geography from `news_intel.json -> industry_position`.

---

## Phase 2.5: Revenue Prediction (Orchestrator Inline)

### Model and Label Consistency

- Use formula and factor framework from `references/prediction_factors.md`.
- Keep macro factor names and ordering consistent with `macro_factors.json` and chosen geography.
- `predicted_fiscal_year_label` should default to `FY(latest_actual + 1)E` and match Sankey forecast label.

### Source-of-Truth Split

- `news_intel.json` = raw event layer (`company_events[].revenue_impact_pct`).
- `prediction_waterfall.json` = final model layer (`company_specific_adjustment_pct` and final bridge).
- Do not maintain competing root-level company-adjustment totals across files.

### Event Normalization

If `company_events_detail[]` is present, prefer:

`final_impact_pct = raw_impact_pct * timing_weight * (1 - overlap_ratio) * run_rate_weight * probability_weight * realization_weight`

and keep `company_specific_adjustment_pct` approximately equal to the sum of event-level `final_impact_pct`.

### Section III Table Contract

- Factor table final column is direction text:
  - `zh`: `正向` / `负向` / `中性`
  - `en`: `Positive` / `Negative` / `Neutral`
- Do not repeat numeric percentage values in the direction column.
- Use existing positive/negative CSS classes only where required by locked template conventions.

### Interim-to-Model Bridge

- Material interim/TTM evidence may adjust company-specific impacts.
- When adjusted value diverges from simple event net sum, explain via assumptions/notes/qc deliberation fields.
- Keep Section III waterfall and Section IV forecast assumptions aligned.

---

## Phase 2.6 / 3.5 / 3.6: QC Phases

Detailed rules for each QC agent live in their respective agent files:
- `agents/qc_macro_peer_a.md` (includes Downstream Contract)
- `agents/qc_macro_peer_b.md` (includes Downstream Contract)
- `agents/qc_porter_peer_a.md` (includes Downstream Contract)
- `agents/qc_porter_peer_b.md` (includes Downstream Contract)
- `agents/qc_resolution_merge.md` (includes Execution Policy: full-run/fast-run, conflict priority)

---

## Phase 4: Sankey Build (Orchestrator Inline)

- Build actual tab from `financial_data.json` current-year P&L basis.
- Build forecast tab from same structure scaled by Phase 2.5 predicted growth and forecast fiscal label.
- Keep Sankey year labels consistent with prediction horizon.
- Node labels must match `report_language` (English names for `en`, Chinese for `zh`).

---

## Phase 5: Report Generation

### Locked Template and Extraction

- Always extract locked skeleton with `scripts/extract_report_template.py` before placeholder filling.
- Only replace `{{PLACEHOLDER}}` values; do not edit HTML/CSS/JS structure.

### Waterfall Data Contract (P0)

- Section III waterfall values are percentage points, not decimals and not currency amounts.
- Build from growth bridge fields (baseline/macro/company/result), not revenue totals.
- Result bar must reconcile with `predicted_revenue_growth_pct` within rounding tolerance.
- Putting `base_revenue` into waterfall produces nonsense like "37296.0%" — that is a unit error.

### Language Branching

- `zh` branch uses `agents/report_writer_cn.md` + `references/report_style_guide_cn.md`.
- `en` branch uses `agents/report_writer_en.md` + `references/report_style_guide_en.md`.

Detailed placeholder rules, Porter comment handling, and post-processing cautions live in the respective `agents/report_writer_*.md` files.

---

## Phase 5.5 / Phase 6: Validation

- Phase 5.5 (`agents/final_report_data_validator.md`): data/professional validation — recompute formulas, reconcile quantities, fix upstream JSON first.
- Phase 6 (`agents/report_validator.md`): delivery/structure validation — resolve CRITICAL plus designated pre-delivery WARNING blockers.
- Both agent files contain their own detailed checklists and blocker policies.
