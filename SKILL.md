---
name: equity-research
description: >
  Full-stack equity research report generator. Trigger this skill whenever the user wants to analyze a company, generate an equity research report, do fundamental financial analysis, or produce investment research on a stock. Works with just a company name (web search mode) or uploaded SEC filings (10-K / 10-Q PDFs). Outputs one professional interactive Chinese HTML report with embedded Sankey revenue flow diagrams, a macro-factor prediction waterfall, and Porter Five Forces analysis.

  TRIGGER on any of: "equity research", "research report", "analyze [company]", "financial analysis of [company]", "做研报", "研究报告", "分析[公司]", user uploads a 10-K or 10-Q and asks for analysis beyond just the revenue flow diagram.
---

# Equity Research Skill

Generate a professional equity research report for any public company. You are the orchestrator — you coordinate data collection, analysis, and report writing, either via parallel subagents (Claude Code) or sequentially (Claude.ai).

## Step 0: Parse Input & Setup Workspace

**Identify the input mode:**

- **Mode A** — Company name only → Web Search mode
- **Mode B** — Company name + 10-K PDF → File-based mode (last year actual, current year predicted via web)
- **Mode C** — Company name + 10-K + 10-Q PDF → Full File mode (richest data)

**Create a workspace directory** for this run:
```
workspace/{Company}_{Date}/
```
All intermediate JSON files go here. All final output files also go here.

**Detect environment:**
- If subagents are available (Claude Code): use parallel agent spawning as described below
- If no subagents (Claude.ai): execute each phase sequentially in the same conversation

---

## Phase 1 + 2 (Macro) + 3 (News): Parallel Data Collection

In Claude Code, spawn these three agents simultaneously. In Claude.ai, run them sequentially.

### Agent 1 — Financial Data Collector
**File:** `agents/financial_data_collector.md`
**Task prompt to pass:**
```
Company: {company_name}
Uploaded files: {list of uploaded PDFs, or "none"}
Output path: workspace/{Company}_{Date}/financial_data.json
Follow instructions in agents/financial_data_collector.md
```

### Agent 2 — Macro Factor Scanner
**File:** `agents/macro_scanner.md`
**Task prompt to pass:**
```
Company: {company_name}
Sector hint: {infer from company or ask user}
Reference: references/prediction_factors.md (load this file for the β table)
Output path: workspace/{Company}_{Date}/macro_factors.json
Follow instructions in agents/macro_scanner.md
```

### Agent 3 — News & Industry Researcher
**File:** `agents/news_researcher.md`
**Task prompt to pass:**
```
Company: {company_name}
Sector: {same as Agent 2}
Output path: workspace/{Company}_{Date}/news_intel.json
Follow instructions in agents/news_researcher.md
```

**Wait for all three agents to complete before proceeding.**

---

## Phase 2: Financial Analysis (Orchestrator runs this inline)

Read `workspace/{Company}_{Date}/financial_data.json` and compute the metrics defined in `references/financial_metrics.md`:

- Profitability: Gross Margin, Operating Margin, Net Margin, ROE, ROA
- Growth: Revenue YoY%, Net Income YoY%, EPS Growth
- Cash Flow: Operating CF, Free Cash Flow, FCF Margin
- Leverage: Debt/Equity, Interest Coverage
- Valuation: P/E, EV/EBITDA (if market data available from web)

For each of Net Income, Net Margin, and FCF:
- If current year > last year → trend = "↑ Increasing", provide growth driver analysis
- If current year < last year → trend = "↓ Decreasing", provide risk factor analysis

Save results to `workspace/{Company}_{Date}/financial_analysis.json`.

---

## Phase 2.5: Revenue Prediction (Macro Factor Model)

Read `references/prediction_factors.md` for the full formula, β table, and φ value.

**Formula:**
```
Predicted_Revenue_Growth =
    Baseline_Growth
  + Σ (Factor_Change% × β_sector × φ)
  + Company_Specific_Adjustment
```

**Baseline Growth:**
- If 10-Q available: annualize YTD revenue (`YTD / quarters_reported × 4`), compute YoY vs last year
- Otherwise: use analyst consensus from web search

**Company_Specific_Adjustment:** Sum the `revenue_impact_pct` values from `news_intel.json` `company_events` array.

Build the waterfall data:
```json
{
  "baseline_growth_pct": 4.2,
  "macro_adjustments": [
    {"factor": "Fed Funds Rate", "adjustment_pct": 6.4},
    ...
  ],
  "company_specific_adjustment_pct": 1.2,
  "predicted_revenue_growth_pct": 11.8,
  "phi": 0.5,
  "confidence": "medium"
}
```

Save to `workspace/{Company}_{Date}/prediction_waterfall.json`.

---

## Phase 3: Porter Five Forces Analysis

Read the Porter framework from `references/porter_framework.md`.

Using `financial_data.json` + `news_intel.json`, write three analytical perspectives (~300 words each):

1. **Company-Level:** The specific company's position within each of the five forces
2. **Industry-Level:** The industry's overall five-force dynamics
3. **Forward-Looking:** How the five forces are likely to evolve over the next 2-3 years

For each perspective, cover all five forces: Supplier Power, Buyer Power, Threat of New Entrants, Threat of Substitutes, Competitive Rivalry.

Save to `workspace/{Company}_{Date}/porter_analysis.json`.

---

## Phase 4: Sankey Data Preparation

Prepare two Sankey datasets from the financial data:

**Last Year (Actual):** From `financial_data.json` income statement — revenue → COGS → gross profit → OpEx breakdown → operating income → tax/other → net income

**Current Year (Predicted):** Scale last year's figures by `(1 + predicted_revenue_growth_pct/100)`. Apply proportional scaling to each line item unless news events suggest structural changes (e.g., new cost-cutting measures → lower OpEx ratio).

These Sankey datasets feed directly into the HTML report templates. No separate files needed — embed them as JS variables in the HTML.

---

## Phase 5: Report Generation (Chinese Only)

### Agent 4B — Chinese HTML Report
**File:** `agents/report_writer_cn.md`
**Inputs:** all JSON files from workspace + sankey datasets prepared in Phase 4
**Output:** `workspace/{Company}_{Date}/{Company}_Research_CN.html`

**CRITICAL:** Agent 4B must use the locked HTML template in `agents/report_writer_cn.md` verbatim. It fills `{{PLACEHOLDER}}` markers only. It must NOT design its own CSS, invent new class names, or alter the HTML structure.

**Wait for Agent 4B to complete before proceeding to Phase 6.**

---

## Phase 6: Report Validation

### Agent 5 — HTML Validator
**File:** `agents/report_validator.md`
**Inputs:**
- `workspace/{Company}_{Date}/{Company}_Research_CN.html`
- `workspace/{Company}_{Date}/financial_data.json`
- `workspace/{Company}_{Date}/prediction_waterfall.json`

**Behavior:**
- Runs all 8 validation checks defined in `agents/report_validator.md`
- If any CRITICAL errors → fixes the HTML and re-validates until 0 CRITICAL remain
- If only WARNINGs → passes but notes them in the final output

**Wait for Agent 5 to complete before presenting final output.**

---

## Final Output

Present the output file to the user:
- `{Company}_Research_CN.html` — Full interactive Chinese report

Tell the user:
- Which data mode was used (web search / file-based / full file)
- The predicted revenue growth figure and key drivers
- Any data confidence caveats (e.g., "Web search mode — some line items estimated")
- The φ (friction factor) used and that they can adjust β values in `references/prediction_factors.md`
- Validation result summary (CRITICAL count / WARNING count)

---

## Data Confidence Labels

Always label data source clearly in outputs:
- `"data_source": "10-K upload"` → High confidence
- `"data_source": "web search"` → Medium confidence, mark estimates with `~`
- If numbers couldn't be found → use `null` and note "Data unavailable"

---

## Reference Files

Load these only when needed for the relevant phase:
- `references/prediction_factors.md` — β table, φ value, full formula (load in Phase 2.5)
- `references/porter_framework.md` — Five forces scoring guide (load in Phase 3)
- `references/financial_metrics.md` — Metric calculation formulas (load in Phase 2)
- `references/report_style_guide_cn.md` — CN report style (Agent 4B loads this)
