#!/usr/bin/env python3
"""
Fetch SEC EDGAR submissions plus key US-GAAP XBRL facts for a US-listed issuer
via https://data.sec.gov/ (official JSON APIs).

SEC fair-access policy requires a descriptive User-Agent that includes contact info:

  export SEC_EDGAR_USER_AGENT='MyApp/1.0 (you@example.com)'

Example:

  python3 scripts/sec_edgar_fetch.py --ticker MSFT \\
    -o workspace/Microsoft_2026-04-08/sec_edgar_bundle.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_SUBMISSIONS_TMPL = "https://data.sec.gov/submissions/CIK{cik}.json"
SEC_FACTS_TMPL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"

# Tag families: first alias with usable rows is not used — we pick the alias whose
# newest `filed` date is latest (handles ASC 606 / tag renames like Revenues vs RevenueFromContract...).
CONCEPT_ALIASES: dict[str, list[str]] = {
    "revenue": [
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "Revenues",
        "SalesRevenueNet",
        "TotalRevenueNetSales",
    ],
    "cost_of_revenue": ["CostOfRevenue", "CostOfGoodsAndServicesSold"],
    "gross_profit": ["GrossProfit"],
    "rd_expense": ["ResearchAndDevelopmentExpense"],
    "sm_expense": ["SellingAndMarketingExpense", "SalesAndMarketingExpense"],
    "ga_expense": ["GeneralAndAdministrativeExpense"],
    "total_opex": ["OperatingExpenses", "CostsAndExpenses"],
    "operating_income": ["OperatingIncomeLoss"],
    "interest_expense": [
        "InterestExpense",
        "InterestAndDebtExpense",
        "InterestIncomeExpenseNet",
    ],
    "pretax_income": [
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
        "IncomeBeforeIncomeTaxes",
    ],
    "income_tax": ["IncomeTaxExpenseBenefit"],
    "net_income": ["NetIncomeLoss", "ProfitLoss"],
    "diluted_eps": [
        "EarningsPerShareDiluted",
        "EarningsPerShareBasic",
        "EarningsPerShareBasicAndDiluted",
    ],
    "diluted_shares": [
        "WeightedAverageNumberOfDilutedSharesOutstanding",
        "WeightedAverageNumberOfSharesOutstandingBasicAndDiluted",
    ],
    "cash": ["CashAndCashEquivalentsAtCarryingValue"],
    "short_term_investments": ["ShortTermInvestments", "MarketableSecuritiesCurrent"],
    "total_assets": ["Assets"],
    "total_equity": [
        "StockholdersEquity",
        "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
    ],
    "ocf": ["NetCashProvidedByUsedInOperatingActivities"],
    "capex": [
        "PaymentsToAcquirePropertyPlantAndEquipment",
        "PaymentsToAcquireProductiveAssets",
    ],
}

REQUEST_GAP_SEC = 0.12
# company_tickers.json is large; give SEC a beat before the next host request.
POST_TICKERS_COOLDOWN_SEC = 0.25


def get_user_agent(cli: str | None) -> str:
    u = (cli or os.environ.get("SEC_EDGAR_USER_AGENT", "")).strip()
    if not u:
        print(
            "error: SEC requires a descriptive User-Agent with contact information.\n"
            "  export SEC_EDGAR_USER_AGENT='MyApp/1.0 (you@example.com)'\n"
            "or pass:  --user-agent 'MyApp/1.0 (you@example.com)'",
            file=sys.stderr,
        )
        sys.exit(3)
    return u


def http_get_json(url: str, headers: dict[str, str]) -> Any:
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:800]
        raise RuntimeError(f"HTTP {e.code} for {url}: {body}") from e


def load_tickers_map(headers: dict[str, str]) -> dict[str, int]:
    data = http_get_json(SEC_TICKERS_URL, headers)
    out: dict[str, int] = {}
    if not isinstance(data, dict):
        return out
    for row in data.values():
        if isinstance(row, dict) and "ticker" in row and "cik_str" in row:
            out[str(row["ticker"]).upper()] = int(row["cik_str"])
    return out


def cik_10(cik: int | str) -> str:
    if isinstance(cik, str):
        digits = cik.strip()
        if not digits.isdigit():
            raise ValueError(f"CIK must be numeric: {cik!r}")
        return digits.zfill(10)
    return f"{int(cik):010d}"


def pick_best_concept(
    facts_usgaap: dict[str, Any], aliases: list[str]
) -> tuple[str, str, list[dict[str, Any]]] | None:
    best: tuple[str, str, str, list[dict[str, Any]]] | None = None
    for tag in aliases:
        if tag not in facts_usgaap:
            continue
        blob = facts_usgaap[tag]
        units = blob.get("units") or {}
        if not isinstance(units, dict):
            continue
        for uom, rows in units.items():
            if not isinstance(rows, list) or not rows:
                continue
            dated = [r for r in rows if isinstance(r, dict) and r.get("filed")]
            if not dated:
                continue
            mx = max(str(r["filed"]) for r in dated)
            cand = (mx, tag, str(uom), rows)
            if best is None or mx > best[0]:
                best = cand
    if best is None:
        return None
    _, tag, uom, rows = best
    return tag, uom, rows


def trim_rows(rows: list[dict[str, Any]], keep_years: int = 8) -> list[dict[str, Any]]:
    dated = [r for r in rows if isinstance(r, dict) and r.get("filed")]
    if not dated:
        return rows[-200:]
    mx = max(str(r["filed"]) for r in dated)
    try:
        mx_dt = datetime.strptime(mx, "%Y-%m-%d")
    except ValueError:
        return rows[-200:]
    cutoff = (mx_dt - timedelta(days=365 * keep_years)).strftime("%Y-%m-%d")
    trimmed = [r for r in rows if isinstance(r, dict) and str(r.get("filed") or "") >= cutoff]
    return trimmed if trimmed else rows[-200:]


def extract_recent_periodic_filings(
    submissions: dict[str, Any], limit: int = 40
) -> list[dict[str, Any]]:
    rec = submissions.get("filings", {}).get("recent", {})
    if not isinstance(rec, dict) or "form" not in rec:
        return []
    forms = rec["form"]
    n = len(forms)
    rd = rec.get("reportDate")
    if not isinstance(rd, list) or len(rd) != n:
        rd = [None] * n
    pd = rec.get("primaryDocument")
    if not isinstance(pd, list) or len(pd) != n:
        pd = [None] * n
    out: list[dict[str, Any]] = []
    for i in range(n):
        f = forms[i]
        if f not in ("10-K", "10-Q", "20-F", "40-F"):
            continue
        out.append(
            {
                "form": f,
                "filing_date": rec["filingDate"][i],
                "report_date": rd[i],
                "accession": rec["accessionNumber"][i],
                "primary_document": pd[i],
            }
        )
        if len(out) >= limit:
            break
    return out


def build_bundle(
    submissions: dict[str, Any],
    companyfacts: dict[str, Any],
    ticker: str,
    cik10: str,
    report_date: str | None,
) -> dict[str, Any]:
    facts_root = companyfacts.get("facts") or {}
    usgaap = facts_root.get("us-gaap")
    if not isinstance(usgaap, dict):
        usgaap = {}

    selections: dict[str, Any] = {}
    slices: dict[str, Any] = {}

    for logical, aliases in CONCEPT_ALIASES.items():
        picked = pick_best_concept(usgaap, aliases)
        if picked is None:
            continue
        tag, uom, rows = picked
        selections[logical] = {"us_gaap_tag": tag, "unit": uom}
        slim: list[dict[str, Any]] = []
        for r in trim_rows(rows):
            if not isinstance(r, dict):
                continue
            slim.append(
                {
                    k: r.get(k)
                    for k in (
                        "start",
                        "end",
                        "val",
                        "fy",
                        "fp",
                        "form",
                        "filed",
                        "accn",
                        "frame",
                    )
                    if k in r
                }
            )
        slices[logical] = slim

    edgar_viewer = "https://www.sec.gov/edgar/browse/?CIK=" + cik10.lstrip("0")

    return {
        "ok": True,
        "schema": "sec_edgar_bundle.v1",
        "cik": cik10,
        "ticker": ticker.upper(),
        "entity_name": submissions.get("name"),
        "sic": submissions.get("sic"),
        "sic_description": submissions.get("sicDescription"),
        "exchanges": submissions.get("exchanges"),
        "tickers_on_submission": submissions.get("tickers"),
        "fiscal_year_end_mmdd": submissions.get("fiscalYearEnd"),
        "report_date_hint": report_date,
        "edgar_entity_url": edgar_viewer,
        "recent_filings": extract_recent_periodic_filings(submissions),
        "concept_selection": selections,
        "facts_recent_slices": slices,
        "notes_for_agent": [
            "Values are as reported in XBRL; scale is tag-specific (USD vs USD/shares vs shares). "
            "For consolidated annual P&L, prefer rows with form=10-K and fp=FY; when multiple rows "
            "share the same fy, the consolidated total is usually the largest val for that fy.",
            "Segment / geographic splits are often not in these tags — still read the 10-K HTML or notes if needed.",
            "Map into financial_data.json in millions for USD line items where appropriate; keep EPS as dollars per share.",
            "Set data_source to \"SEC EDGAR API (data.sec.gov)\" when numbers are taken from this bundle; "
            "data_confidence can be \"high\" for successfully aligned filing rows.",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.strip().split("\n")[0])
    p.add_argument("--ticker", help="US trading symbol (e.g. MSFT). Required unless --cik is set.")
    p.add_argument("--cik", help="Numeric CIK (zero-padding optional); skips ticker lookup.")
    p.add_argument("-o", "--output", type=Path, help="Write JSON bundle to this file.")
    p.add_argument("--report-date", dest="report_date", help="Optional YYYY-MM-DD context for the run.")
    p.add_argument("--user-agent", dest="user_agent", help="Override SEC_EDGAR_USER_AGENT.")
    args = p.parse_args(argv)

    ua = get_user_agent(args.user_agent)
    headers = {"User-Agent": ua, "Accept": "application/json"}

    try:
        if args.cik:
            cik10 = cik_10(args.cik)
            ticker_guess = (args.ticker or "UNKNOWN").upper()
        else:
            if not args.ticker:
                print("error: provide --ticker or --cik", file=sys.stderr)
                return 2
            tickers = load_tickers_map(headers)
            time.sleep(POST_TICKERS_COOLDOWN_SEC)
            t = args.ticker.strip().upper()
            if t not in tickers:
                print(f"error: ticker not found in SEC company_tickers: {t!r}", file=sys.stderr)
                return 2
            cik10 = cik_10(tickers[t])
            ticker_guess = t

        sub_url = SEC_SUBMISSIONS_TMPL.format(cik=cik10)
        submissions = http_get_json(sub_url, headers)
        time.sleep(REQUEST_GAP_SEC)

        facts_url = SEC_FACTS_TMPL.format(cik=cik10)
        companyfacts = http_get_json(facts_url, headers)

        tickers_meta = submissions.get("tickers") if isinstance(submissions, dict) else None
        if isinstance(tickers_meta, list) and tickers_meta:
            primary = str(tickers_meta[0]).upper()
        else:
            primary = ticker_guess

        bundle = build_bundle(
            submissions if isinstance(submissions, dict) else {},
            companyfacts if isinstance(companyfacts, dict) else {},
            primary,
            cik10,
            args.report_date,
        )
    except (RuntimeError, ValueError, OSError, urllib.error.URLError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    text = json.dumps(bundle, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
