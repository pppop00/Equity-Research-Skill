# Financial Metrics Reference

Calculation formulas for all metrics used in Phase 2 (Financial Analysis). All inputs come from `financial_data.json`.

---

## Profitability Metrics (盈利能力)

| Metric | Formula | Unit | Notes |
|--------|---------|------|-------|
| Gross Margin | `gross_profit / revenue × 100` | % | Higher = more pricing power |
| Operating Margin | `operating_income / revenue × 100` | % | Before interest & tax |
| Net Margin | `net_income / revenue × 100` | % | Bottom-line profitability |
| EBITDA | `operating_income + D&A` | $ M | D&A from cash flow or notes; estimate if unavailable |
| EBITDA Margin | `EBITDA / revenue × 100` | % | — |
| ROE | `net_income / total_equity × 100` | % | Return on shareholders' equity |
| ROA | `net_income / total_assets × 100` | % | Asset efficiency |

---

## Growth Metrics (增长)

| Metric | Formula | Unit | Notes |
|--------|---------|------|-------|
| Revenue Growth YoY | `(current_revenue - prior_revenue) / prior_revenue × 100` | % | — |
| Net Income Growth YoY | `(current_NI - prior_NI) / prior_NI × 100` | % | Use absolute value of prior if prior is negative |
| EPS Growth YoY | `(current_EPS - prior_EPS) / prior_EPS × 100` | % | Diluted EPS |
| Gross Profit Growth YoY | `(current_GP - prior_GP) / prior_GP × 100` | % | — |

---

## Cash Flow Metrics (现金流)

| Metric | Formula | Unit | Notes |
|--------|---------|------|-------|
| Free Cash Flow | `operating_cash_flow - capex` | $ M | CapEx is negative in JSON; add (subtract the negative) |
| FCF Margin | `free_cash_flow / revenue × 100` | % | — |
| FCF Conversion | `free_cash_flow / net_income × 100` | % | >100% = high quality earnings |
| CapEx Intensity | `|capex| / revenue × 100` | % | Lower = asset-light business model |

---

## Leverage Metrics (杠杆)

| Metric | Formula | Unit | Notes |
|--------|---------|------|-------|
| Debt/Equity | `total_debt / total_equity` | ratio | >2x = highly leveraged |
| Net Debt | `total_debt - cash_and_equivalents - short_term_investments` | $ M | Negative = net cash position |
| Net Debt/EBITDA | `net_debt / EBITDA` | ratio | <2x = comfortable; >4x = stressed |
| Interest Coverage | `operating_income / interest_expense` | ratio | >3x = comfortable; <2x = concerning |

---

## Valuation Metrics (估值，if market data available)

These require additional web searches for current market data. Mark as "N/A (market data unavailable)" if you cannot retrieve reliable figures.

| Metric | Formula | Unit | How to obtain market data |
|--------|---------|------|--------------------------|
| P/E Ratio | `current_stock_price / diluted_EPS` | ratio | `web_search "{ticker} stock price today"` |
| Market Cap | `current_stock_price × diluted_shares` | $ M | Same search |
| Enterprise Value | `market_cap + total_debt - cash - short_term_investments` | $ M | Calculate from above |
| EV/EBITDA | `enterprise_value / EBITDA` | ratio | — |
| P/FCF | `market_cap / free_cash_flow` | ratio | — |

---

## Trend Classification Logic

For Net Income, Net Margin, and FCF, classify the trend and write the corresponding analysis:

```
IF current_year > prior_year (improvement):
    trend_label = "↑ Increasing"
    trend_class = "positive"
    Write 2-3 sentences on growth drivers:
      - Volume growth? Price increases? Operating leverage?
      - Segment mix shift?
      - Cost reduction / efficiency gains?

ELSE IF current_year < prior_year (decline):
    trend_label = "↓ Decreasing"
    trend_class = "negative"
    Write 2-3 sentences on risk factors:
      - Revenue decline or margin compression?
      - Rising cost pressures?
      - One-time charges or structural issues?

ELSE:
    trend_label = "→ Stable"
    trend_class = "neutral"
```

---

## Output Schema

Save to `workspace/{Company}_{Date}/financial_analysis.json`:

```json
{
  "profitability": {
    "gross_margin_current": 46.2,
    "gross_margin_prior": 46.2,
    "operating_margin_current": 29.7,
    "operating_margin_prior": 29.8,
    "net_margin_current": 24.6,
    "net_margin_prior": 24.5,
    "roe_current": 168.7,
    "roa_current": 26.3,
    "ebitda_current": null,
    "ebitda_margin_current": null
  },
  "growth": {
    "revenue_growth_yoy_pct": 2.0,
    "net_income_growth_yoy_pct": 3.6,
    "eps_growth_yoy_pct": 4.9,
    "gross_profit_growth_yoy_pct": 2.1
  },
  "cash_flow": {
    "free_cash_flow": 108807,
    "fcf_margin_pct": 27.8,
    "fcf_conversion_pct": 113.3,
    "capex_intensity_pct": 2.4
  },
  "leverage": {
    "debt_equity_ratio": 1.78,
    "net_debt": -23726,
    "net_debt_ebitda": null,
    "interest_coverage_ratio": 40.4
  },
  "valuation": {
    "stock_price": null,
    "pe_ratio": null,
    "market_cap": null,
    "ev": null,
    "ev_ebitda": null,
    "note": "Market data not retrieved"
  },
  "trends": {
    "net_income": {
      "label": "↑ Increasing",
      "class": "positive",
      "analysis": "Net income rose 3.6% YoY driven by..."
    },
    "net_margin": {
      "label": "→ Stable",
      "class": "neutral",
      "analysis": "Net margin held steady at ~24.6%..."
    },
    "fcf": {
      "label": "↑ Increasing",
      "class": "positive",
      "analysis": "Free cash flow improved to $108.8B..."
    }
  },
  "unit": "millions USD",
  "notes": []
}
```
