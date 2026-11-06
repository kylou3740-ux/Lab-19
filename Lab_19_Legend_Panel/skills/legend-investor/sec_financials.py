"""SEC EDGAR financial facts and Buffett checks for FIN 43900 Lab 18.

SEC facts are returned in USD; this script converts amounts to USD millions.
No third-party financial-data service or API key is used.
"""
from __future__ import annotations

import argparse
import json
import os
import re
from datetime import date
from typing import Any

import requests

TICKER_URL = "https://www.sec.gov/files/company_tickers.json"
FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"

TAG_CHOICES = {
    "revenue": [
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "Revenues",
    ],
    "net_income": ["NetIncomeLoss"],
    "operating_cash_flow": [
        "NetCashProvidedByUsedInOperatingActivities"
    ],
    "capital_spending": [
        "PaymentsToAcquirePropertyPlantAndEquipment",
        "PaymentsToAcquireProductiveAssets",
    ],
    "research_and_development": ["ResearchAndDevelopmentExpense"],
    "equity": ["StockholdersEquity"],
    "liabilities": ["Liabilities"],
    "assets_current": ["AssetsCurrent"],
    "liabilities_current": ["LiabilitiesCurrent"],
}
FLOW_FIELDS = {
    "revenue", "net_income", "operating_cash_flow", "capital_spending",
    "research_and_development",
}


class SECDataError(RuntimeError):
    """Raised when SEC data cannot be retrieved or interpreted."""


def make_session() -> requests.Session:
    """Create an SEC-compliant session with a descriptive, identifying User-Agent."""
    email = os.getenv("SEC_USER_EMAIL", "").strip()
    if not email or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise SECDataError(
            "Set SEC_USER_EMAIL to your real email address first. "
            "PowerShell example: $env:SEC_USER_EMAIL='you@example.com'"
        )
    session = requests.Session()
    session.headers.update({
        "User-Agent": f"FIN43900 Lab18 Student Research Contact {email}",
        "Accept-Encoding": "gzip, deflate",
        "Accept": "application/json",
    })
    return session


def get_json(session: requests.Session, url: str) -> dict[str, Any]:
    response = session.get(url, timeout=30)
    response.raise_for_status()
    return response.json()


def ticker_to_cik(ticker: str, session: requests.Session) -> str:
    directory = get_json(session, TICKER_URL)
    wanted = ticker.strip().upper()
    for record in directory.values():
        if str(record.get("ticker", "")).upper() == wanted:
            return str(record["cik_str"]).zfill(10)
    raise SECDataError(f"Ticker {wanted} was not found in the SEC ticker directory.")


def get_usd_entries(companyfacts: dict, tag: str) -> list[dict]:
    """Return USD observations for a us-gaap XBRL tag, or an empty list."""
    facts = companyfacts.get("facts", {}).get("us-gaap", {})
    return facts.get(tag, {}).get("units", {}).get("USD", [])


def is_one_year_period(entry: dict) -> bool:
    """Accept annual duration observations (330–380 days) only."""
    if not entry.get("start") or not entry.get("end"):
        return False
    try:
        days = (
            date.fromisoformat(entry["end"]) -
            date.fromisoformat(entry["start"])
        ).days
    except ValueError:
        return False
    return 330 <= days <= 380


def annual_observations(companyfacts: dict, field: str, tag: str) -> list[dict]:
    """Filter a tag to annual 10-K observations appropriate to the metric."""
    observations = []
    for entry in get_usd_entries(companyfacts, tag):
        if entry.get("form") != "10-K" or not entry.get("end"):
            continue
        if field in FLOW_FIELDS and not is_one_year_period(entry):
            continue
        if field in {"equity", "liabilities", "assets_current", "liabilities_current"}:
            # Instant fact: require fiscal-year context when SEC provides it.
            if entry.get("fp") not in (None, "FY"):
                continue
        observations.append(entry)
    return observations


def choose_observation(
    companyfacts: dict, field: str, fiscal_year_end: str
) -> tuple[float | None, str | None]:
    """Select the preferred tag and latest-filed 10-K observation for one year.

    The professor's tag order is honored. For repeated observations of the same
    fiscal period, the latest filing date wins.
    """
    for tag in TAG_CHOICES[field]:
        candidates = [
            item for item in annual_observations(companyfacts, field, tag)
            if item.get("end") == fiscal_year_end
        ]
        if not candidates:
            continue
        candidates.sort(
            key=lambda item: (item.get("filed", ""), item.get("accn", "")),
            reverse=True,
        )
        return float(candidates[0]["val"]) / 1_000_000.0, tag
    return None, None


def discover_fiscal_year_ends(companyfacts: dict) -> list[str]:
    """Discover annual year ends from the permitted 10-K facts, newest first."""
    ends = set()
    for field, tags in TAG_CHOICES.items():
        for tag in tags:
            for item in annual_observations(companyfacts, field, tag):
                ends.add(item["end"])
    return sorted(ends, reverse=True)[:5][::-1]


def calculate_checks(rows: list[dict]) -> dict[str, str]:
    """Calculate the three required Buffett checks with explicit unknown states."""
    if not rows:
        return {
            "roe_15_percent_every_year": "not known",
            "owner_earnings_positive_every_year": "not known",
            "owner_earnings_grew_first_to_last": "not known",
        }

    roes = [row.get("roe_pct") for row in rows]
    owner_earnings = [row.get("owner_earnings") for row in rows]

    roe_status = (
        "not known" if any(value is None for value in roes)
        else "pass" if all(value >= 15 for value in roes)
        else "fail"
    )
    positive_status = (
        "not known" if any(value is None for value in owner_earnings)
        else "pass" if all(value > 0 for value in owner_earnings)
        else "fail"
    )
    growth_status = (
        "not known"
        if len(owner_earnings) < 2
        or owner_earnings[0] is None
        or owner_earnings[-1] is None
        else "pass" if owner_earnings[-1] > owner_earnings[0]
        else "fail"
    )
    return {
        "roe_15_percent_every_year": roe_status,
        "owner_earnings_positive_every_year": positive_status,
        "owner_earnings_grew_first_to_last": growth_status,
    }


def build_year_row(companyfacts: dict, fiscal_year_end: str) -> dict:
    row = {
        "fiscal_year_end": fiscal_year_end,
        "revenue": None,
        "net_income": None,
        "operating_cash_flow": None,
        "capital_spending": None,
        "research_and_development": None,
        "equity": None,
        "liabilities": None,
        "assets_current": None,
        "liabilities_current": None,
        "current_ratio": None,
        "liabilities_to_equity": None,
        "roe_pct": None,
        "owner_earnings": None,
        "tags": {},
    }
    for field in TAG_CHOICES:
        value, tag = choose_observation(companyfacts, field, fiscal_year_end)
        row[field] = value
        row["tags"][field] = tag if tag else "not found"

    equity = row["equity"]
    net_income = row["net_income"]
    if equity is not None and equity > 0 and net_income is not None:
        row["roe_pct"] = net_income / equity * 100.0
    if row["assets_current"] is not None and row["liabilities_current"] not in (None, 0):
        row["current_ratio"] = row["assets_current"] / row["liabilities_current"]
    if row["liabilities"] is not None and equity is not None and equity > 0:
        row["liabilities_to_equity"] = row["liabilities"] / equity

    operating_cash_flow = row["operating_cash_flow"]
    capital_spending = row["capital_spending"]
    if operating_cash_flow is not None and capital_spending is not None:
        row["owner_earnings"] = operating_cash_flow - capital_spending
    return row


CATHIE_WOOD_REVENUE_GROWTH_THRESHOLD = 15.0
CATHIE_WOOD_RD_REVENUE_THRESHOLD = 5.0


def calculate_revenue_cagr(rows: list[dict]) -> float | None:
    """Annualized revenue growth from first to last of five fiscal years."""
    if len(rows) != 5:
        return None
    first, last = rows[0].get("revenue"), rows[-1].get("revenue")
    if first is None or last is None or first <= 0 or last <= 0:
        return None
    return ((last / first) ** (1 / 4) - 1) * 100.0


def calculate_panel_checks(rows: list[dict]) -> dict[str, dict[str, str]]:
    """Calculate Buffett, Cathie Wood, and Burry checks; gaps stay unknown."""
    if not rows:
        return {name: {} for name in ("buffett", "cathie_wood", "burry")}
    net_income = [r.get("net_income") for r in rows]
    ocf = [r.get("operating_cash_flow") for r in rows]
    latest = rows[-1]
    revenue_cagr = calculate_revenue_cagr(rows)
    rd = latest.get("research_and_development")
    revenue = latest.get("revenue")
    rd_pct = (rd / revenue * 100.0) if rd is not None and revenue not in (None, 0) else None
    buffett = calculate_checks(rows)
    cathie_wood = {
        "revenue_growth_15_percent_first_to_last": (
            "not known" if revenue_cagr is None else
            ("pass" if revenue_cagr >= CATHIE_WOOD_REVENUE_GROWTH_THRESHOLD else "fail")
        ),
        "research_and_development_5_percent_latest_year": (
            "not known" if rd_pct is None else
            ("pass" if rd_pct >= CATHIE_WOOD_RD_REVENUE_THRESHOLD else "fail")
        ),
    }
    burry = {
        "operating_cash_flow_at_least_net_income_every_year": (
            "not known" if any(a is None or b is None for a, b in zip(ocf, net_income))
            else ("pass" if all(a >= b for a, b in zip(ocf, net_income)) else "fail")
        ),
        "liabilities_no_more_than_2x_equity_latest_year": (
            "not known" if latest.get("liabilities_to_equity") is None
            else ("pass" if latest["liabilities_to_equity"] <= 2.0 else "fail")
        ),
    }
    return {"buffett": buffett, "cathie_wood": cathie_wood, "burry": burry}


def build_five_year_history(ticker: str) -> dict:
    ticker = ticker.strip().upper()
    session = make_session()
    cik = ticker_to_cik(ticker, session)
    companyfacts = get_json(session, FACTS_URL.format(cik=cik))
    fiscal_ends = discover_fiscal_year_ends(companyfacts)
    rows = [build_year_row(companyfacts, end) for end in fiscal_ends]
    revenue_cagr = calculate_revenue_cagr(rows)
    latest = rows[-1] if rows else {}
    rd = latest.get("research_and_development")
    latest_revenue = latest.get("revenue")
    rd_pct = (rd / latest_revenue * 100.0) if rd is not None and latest_revenue not in (None, 0) else None
    return {
        "ticker": ticker,
        "cik": cik,
        "unit": "USD millions unless percentage",
        "years": rows,
        "checks": calculate_checks(rows),
        "revenue_cagr_pct": revenue_cagr,
        "rd_pct_latest_year": rd_pct,
        "panel_checks": calculate_panel_checks(rows),
    }


def fmt_amount(value):
    return "not found" if value is None else f"{value:,.0f}"


def fmt_pct(value):
    return "not found" if value is None else f"{value:.1f}"

def fmt_pct2(value):
    return "not found" if value is None else f"{value:.2f}"


def print_report(result: dict) -> str:
    lines = [
        f"FIN 43900 LAB 19 — LEGEND INVESTOR PANEL: {result['ticker']}",
        f"CIK: {result['cik']}",
        "All monetary values are USD millions.",
        f"Revenue CAGR, first to last year (annualized): {fmt_pct2(result.get('revenue_cagr_pct'))}%",
        f"Latest-year R&D / revenue: {fmt_pct(result.get('rd_pct_latest_year'))}%",
        "",
        "FY end | Revenue | Net income | Operating cash flow | Capital spending | R&D | Equity | Liabilities | Current assets | Current liabilities | Current ratio | Liabilities/equity | ROE % | Owner earnings",
        "--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---:",
    ]
    for row in result["years"]:
        lines.append(" | ".join([
            row["fiscal_year_end"],
            fmt_amount(row["revenue"]),
            fmt_amount(row["net_income"]),
            fmt_amount(row["operating_cash_flow"]),
            fmt_amount(row["capital_spending"]),
            fmt_amount(row["research_and_development"]),
            fmt_amount(row["equity"]),
            fmt_amount(row["liabilities"]),
            fmt_amount(row["assets_current"]),
            fmt_amount(row["liabilities_current"]),
            "not found" if row["current_ratio"] is None else f"{row['current_ratio']:.2f}",
            "not found" if row["liabilities_to_equity"] is None else f"{row['liabilities_to_equity']:.2f}",
            fmt_pct(row["roe_pct"]),
            fmt_amount(row["owner_earnings"]),
        ]))
        for field in TAG_CHOICES:
            lines.append(f"XBRL tag — {row['fiscal_year_end']} — {field}: {row['tags'][field]}")
    lines.extend([
        "",
        "BUFFETT CHECKS",
        f"ROE of 15% or more every year: {result['checks']['roe_15_percent_every_year']}",
        f"Owner earnings positive every year: {result['checks']['owner_earnings_positive_every_year']}",
        f"Owner earnings grew, first year to last: {result['checks']['owner_earnings_grew_first_to_last']}",
        "",
        "CATHIE WOOD CHECKS",
        f"Revenue grew {CATHIE_WOOD_REVENUE_GROWTH_THRESHOLD:.0f}% or more a year, first to last: {result['panel_checks']['cathie_wood']['revenue_growth_15_percent_first_to_last']}",
        f"R&D at least {CATHIE_WOOD_RD_REVENUE_THRESHOLD:.0f}% of revenue, latest year: {result['panel_checks']['cathie_wood']['research_and_development_5_percent_latest_year']}",
        "",
        "BURRY CHECKS",
        f"Operating cash flow at least net income every year: {result['panel_checks']['burry']['operating_cash_flow_at_least_net_income_every_year']}",
        f"Liabilities no more than 2x equity, latest year: {result['panel_checks']['burry']['liabilities_no_more_than_2x_equity_latest_year']}",
    ])
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Retrieve five fiscal years of SEC 10-K facts and calculate the Lab 19 investor panel."
    )
    parser.add_argument("ticker", help="Ticker, for example COST or JPM")
    parser.add_argument("--json", dest="json_path", help="Optional path for JSON output")
    args = parser.parse_args()

    result = build_five_year_history(args.ticker)
    report = print_report(result)
    print(report)
    if args.json_path:
        with open(args.json_path, "w", encoding="utf-8") as output:
            json.dump(result, output, indent=2)
        print(f"\nSaved JSON: {args.json_path}")


if __name__ == "__main__":
    main()


def find_unprinted_numbers(memo: str, printed_report: str) -> list[str]:
    """Find numeric tokens in a memo that do not occur in the script report."""
    pattern = re.compile(r"(?<![A-Za-z])\d[\d,]*(?:\.\d+)?%?")
    def tokens(text):
        # A report prints ROE as 28.3; a memo may correctly write 28.3%.
        # The percent sign is a unit marker, not a different numeric value.
        return {
            match.replace(",", "").rstrip("%")
            for match in pattern.findall(text)
        }
    return sorted(tokens(memo) - tokens(printed_report))
