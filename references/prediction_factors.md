# Prediction Factors Reference

This file defines the macro factor model used in Phase 2.5 of the equity research skill. Update β values and φ over time as you calibrate against actual outcomes.

---

## Core Formula

```
Predicted_Revenue_Growth =
    Baseline_Growth
  + Σ (Factor_Change% × β_sector × φ)
  + Company_Specific_Adjustment
```

**Baseline_Growth:** Annualized growth rate from 10-Q YTD data (`YTD_revenue / quarters_reported × 4` vs prior year full-year), or analyst consensus from web search if no 10-Q available.

**Company_Specific_Adjustment:** Sum of `revenue_impact_pct` from all `company_events` in `news_intel.json`.

---

## φ — Friction Factor (Market Transmission)

```
φ = 0.5  (default)
```

The friction factor represents how much of a macro change actually transmits to company revenue. A value of 0.5 means 50% transmission — accounting for market frictions, hedging, contract lock-ins, and time lags.

| φ Value | Interpretation |
|---------|---------------|
| 0.1–0.2 | High friction: heavily hedged, long-term contracts, regulated industry |
| 0.3–0.5 | Moderate friction: typical corporate exposure ← **default** |
| 0.6–0.8 | Low friction: commodity-linked, unhedged, spot-market exposure |
| 0.9–1.0 | Direct pass-through: fully exposed, commodity producer or pure-play |

---

## β — Sector Sensitivity Coefficients

These are the default starting values. Adjust based on company-specific characteristics and validated predictions over time.

| Sector | Interest Rate β | GDP Growth β | PCE Inflation β | USD Index β | Oil Price β | Consumer Confidence β |
|--------|:--------------:|:------------:|:---------------:|:-----------:|:-----------:|:---------------------:|
| Technology | 0.3 | 1.2 | -0.2 | -0.4 | -0.1 | 0.5 |
| Real Estate / REITs | 1.8 | 0.8 | -0.3 | 0.1 | -0.1 | 0.2 |
| Financials / Banks | -0.8 | 1.0 | 0.2 | 0.2 | 0.0 | 0.6 |
| Healthcare | 0.1 | 0.5 | -0.1 | -0.2 | -0.1 | 0.1 |
| Consumer Discretionary | 0.5 | 1.5 | -0.5 | -0.3 | -0.2 | 1.2 |
| Consumer Staples | 0.05 | 0.3 | 0.3 | -0.3 | -0.1 | 0.2 |
| Energy | -0.2 | 0.8 | 0.1 | -0.5 | 1.5 | 0.0 |
| Industrials | 0.4 | 1.3 | -0.2 | -0.3 | -0.3 | 0.7 |
| Utilities | 1.2 | 0.3 | -0.1 | 0.0 | -0.2 | 0.0 |
| Communication Services | 0.2 | 1.0 | -0.1 | -0.2 | 0.0 | 0.8 |
| Materials | 0.3 | 1.2 | 0.3 | -0.5 | 0.4 | 0.3 |
| Semiconductors (sub-sector) | 0.4 | 1.5 | -0.2 | -0.3 | -0.1 | 0.6 |

**β sign interpretation:**
- Positive: this macro factor rising helps revenue
- Negative: this macro factor rising hurts revenue

**Interest Rate β note:** Measured as the impact of a 1% decline in the Fed Funds Rate level (not basis points). So β = 1.8 for REITs means a 1% rate *decline* → ~1.8% revenue growth benefit (before φ).

---

## Macro Factor Registry

Agents should search for current values of these factors:

| Factor | What to search for | Unit | Change direction |
|--------|-------------------|------|-----------------|
| Fed Funds Rate | "federal funds rate current FOMC forecast year-end 2026" | % level | Lower rates = positive for most sectors |
| Real GDP Growth | "US real GDP growth forecast 2026 IMF Fed" | % YoY | Higher = positive |
| PCE Inflation | "PCE inflation rate 2026 Federal Reserve forecast" | % YoY | Higher = raises costs for most sectors |
| USD Index (DXY) | "DXY dollar index current 2026" | Index level | Higher USD = negative for exporters |
| WTI Crude Oil | "WTI crude oil price forecast 2026" | $/barrel | Sector-dependent |
| Consumer Confidence | "US consumer confidence index Conference Board 2026" | Index level | Higher = positive for consumer sectors |

**Factor_Change% calculation:**
- For rate/index levels: `(Forecast - Current) / |Current| × 100`
- Example: Fed Funds goes from 3.625% to 3.375% → Change% = (3.375 - 3.625) / 3.625 × 100 = -6.9%

---

## Calibration Log

Record prediction outcomes here over time to improve the model:

| Date | Company | Predicted Growth | Actual Growth | Error | Action |
|------|---------|-----------------|---------------|-------|--------|
| — | — | — | — | — | Update φ or β if systematic bias detected |

**Calibration rules:**
- If systematic over-prediction: lower φ by 0.05
- If systematic under-prediction: raise φ by 0.05
- If sector-specific bias: adjust that sector's β values
- Aim to validate predictions 6-12 months after report generation

---

## Worked Example

**Company:** Prologis (PLD) — Logistics REIT | **Sector:** Real Estate / REITs | **φ = 0.5**

| Factor | Current | Forecast | Change% | β | φ | Adjustment% |
|--------|---------|----------|---------|---|---|------------|
| Fed Funds Rate | 3.625% | 3.375% | -6.9% | 1.8 | 0.5 | +6.2% |
| GDP Growth | 2.4% | 2.4% | 0.0% | 0.8 | 0.5 | +0.0% |
| PCE Inflation | 2.7% | 2.7% | 0.0% | -0.3 | 0.5 | +0.0% |
| USD Index | 102 | 99 | -2.9% | 0.1 | 0.5 | -0.1% |
| Oil Price | $78 | $72 | -7.7% | -0.1 | 0.5 | +0.4% |

Total macro adjustment: **+6.5%**
Baseline (10-Q annualized): **+4.2%**
Company-specific (new Amazon contract): **+1.5%**
**Predicted Revenue Growth: +12.2%**
