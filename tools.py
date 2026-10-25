"""Research tools + Claude API tool definitions."""

from __future__ import annotations

import json
import os
import re
from datetime import date
from pathlib import Path
from urllib.parse import quote_plus, urlparse

import requests
from bs4 import BeautifulSoup

from config import HTTP_USER_AGENT, SEC_USER_AGENT

# ---------------------------------------------------------------------------
# Tool definitions for Claude API (function-calling schema)
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS = [
    {
        "name": "web_search",
        "description": "Search the web via DuckDuckGo for news, analyst opinions, industry reports, etc. Returns top results with titles, URLs and snippets. Supports English and Chinese queries.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query (use English for global data, Chinese for A-share / HK specific data)",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Number of results to return (default 8)",
                    "default": 8,
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_stock_info",
        "description": "Get basic stock info: price, market cap, PE, PB, sector, industry, beta, 52-week range, dividend yield, etc. Works for listed companies only.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Stock ticker symbol (e.g. AAPL, 600519.SS, 0700.HK)",
                },
            },
            "required": ["ticker"],
        },
    },
    {
        "name": "get_financials",
        "description": "Get financial statements (income statement, balance sheet, cash flow) for a listed company. Returns annual data by default.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Stock ticker symbol",
                },
                "statement": {
                    "type": "string",
                    "enum": ["income", "balance", "cashflow"],
                    "description": "Which financial statement to retrieve",
                },
                "quarterly": {
                    "type": "boolean",
                    "description": "If true, return quarterly data instead of annual",
                    "default": False,
                },
            },
            "required": ["ticker", "statement"],
        },
    },
    {
        "name": "get_sec_filings",
        "description": (
            "List the KEY SEC filings of a US-listed company with URLs: (1) financial reports — the "
            "latest 10-K, the 10-Qs since it, and quarterly earnings releases (8-K Item 2.02, with a "
            "direct link to the press release exhibit); (2) key personnel changes — 8-K Item 5.02 "
            "(departure/appointment of directors and officers). Read any URL with read_url."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "US stock ticker symbol (e.g. AAPL)",
                },
            },
            "required": ["ticker"],
        },
    },
    {
        "name": "get_insider_trading",
        "description": (
            "Summarize holding changes of directors, officers and 10% owners of a US-listed company "
            "from their SEC Form 4 filings: per person, open-market buys/sells (shares, value, avg "
            "price, how much was under a pre-arranged 10b5-1 plan), other transactions by type, and "
            "shares held after the latest filing."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "US stock ticker symbol (e.g. AAPL)",
                },
                "days": {
                    "type": "integer",
                    "description": "Look-back window in days (default 180)",
                    "default": 180,
                },
            },
            "required": ["ticker"],
        },
    },
    {
        "name": "get_sec_financial_data",
        "description": (
            "AUTHORITATIVE reported financials for a US-listed company, taken from the XBRL data of its "
            "10-K/10-Q filings at SEC (revenue, gross profit, operating income, net income, EPS, R&D, "
            "stock-based comp, operating cash flow, capex, buybacks, cash, equity, debt, shares). "
            "Returns the last fiscal years and the last 3-month quarters with period end dates. "
            "Prefer these numbers over get_financials / web sources when they disagree."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "US stock ticker symbol (e.g. FIG, AAPL)",
                },
            },
            "required": ["ticker"],
        },
    },
    {
        "name": "read_url",
        "description": (
            "Fetch and extract main text content from a web URL. Use this to read news articles, "
            "SEC filings, analyst reports, etc. Long pages (e.g. a 10-K/10-Q is ~400k chars) are "
            "returned one window at a time: use `find` to jump to a section (e.g. "
            "'Statements of Operations', 'Results of Operations', 'Liquidity and Capital Resources'), "
            "or `offset` to continue from where the previous window ended."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "Full URL to fetch",
                },
                "find": {
                    "type": "string",
                    "description": "Optional text to jump to; the window starts just before its first match (case-insensitive) at or after `offset`",
                },
                "offset": {
                    "type": "integer",
                    "description": "Character position to start reading from (default 0)",
                    "default": 0,
                },
                "max_chars": {
                    "type": "integer",
                    "description": "Window size in characters (default 15000)",
                    "default": 15000,
                },
            },
            "required": ["url"],
        },
    },
    {
        "name": "read_local_file",
        "description": "Read a local file (PDF, markdown, text). Use this to read previous research reports or local documents.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the local file (absolute or relative to project root)",
                },
                "max_chars": {
                    "type": "integer",
                    "description": "Max characters to return (default 15000)",
                    "default": 15000,
                },
            },
            "required": ["file_path"],
        },
    },
]


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

HEADERS = {
    "User-Agent": HTTP_USER_AGENT
}


def web_search(query: str, max_results: int = 8) -> str:
    """Search via DuckDuckGo using the ddgs library."""
    try:
        from ddgs import DDGS
        results = DDGS().text(query, max_results=max_results)
        if not results:
            return "No results found."
        
        formatted_results = []
        for i, r in enumerate(results):
            title = r.get('title', '')
            link = r.get('href', '')
            snippet = r.get('body', '')
            if title or link:
                formatted_results.append(f"[{i+1}] {title}\n    URL: {link}\n    {snippet}")
        
        return "\n\n".join(formatted_results) if formatted_results else "No results found."
    except Exception as e:
        return f"Search error: {e}"


def get_stock_info(ticker: str) -> str:
    """Get basic stock info via yfinance."""
    try:
        import yfinance as yf
        t = yf.Ticker(ticker)
        info = t.info
        if not info or "shortName" not in info:
            return f"No data found for ticker: {ticker}"
        fields = [
            "shortName", "symbol", "exchange", "currency", "sector", "industry",
            "marketCap", "enterpriseValue",
            "currentPrice", "previousClose", "fiftyTwoWeekLow", "fiftyTwoWeekHigh",
            "trailingPE", "forwardPE", "priceToBook", "priceToSalesTrailing12Months",
            "trailingEps", "forwardEps",
            "dividendYield", "payoutRatio",
            "beta", "returnOnEquity", "returnOnAssets",
            "revenueGrowth", "earningsGrowth",
            "totalRevenue", "grossMargins", "operatingMargins", "profitMargins",
            "totalCash", "totalDebt", "debtToEquity",
            "freeCashflow", "operatingCashflow",
            "fullTimeEmployees",
        ]
        lines = []
        for f in fields:
            v = info.get(f)
            if v is not None:
                lines.append(f"{f}: {v}")
        return "\n".join(lines)
    except Exception as e:
        return f"Error fetching stock info: {e}"


def get_financials(ticker: str, statement: str = "income", quarterly: bool = False) -> str:
    """Get financial statements via yfinance."""
    try:
        import yfinance as yf
        t = yf.Ticker(ticker)
        stmt_map = {
            "income": (t.quarterly_income_stmt if quarterly else t.income_stmt),
            "balance": (t.quarterly_balance_sheet if quarterly else t.balance_sheet),
            "cashflow": (t.quarterly_cashflow if quarterly else t.cashflow),
        }
        df = stmt_map.get(statement)
        if df is None or df.empty:
            return f"No {statement} statement data for {ticker}"
        return df.to_string()
    except Exception as e:
        return f"Error fetching financials: {e}"


SEC_HEADERS = {
    "User-Agent": SEC_USER_AGENT,
    "Accept": "application/json",
}


def _sec_cik(ticker: str) -> str | None:
    """Resolve a ticker to its zero-padded SEC CIK via the company tickers endpoint."""
    resp = requests.get("https://www.sec.gov/files/company_tickers.json", headers=SEC_HEADERS, timeout=10)
    resp.raise_for_status()
    for entry in resp.json().values():
        if entry.get("ticker", "").upper() == ticker.upper():
            return str(entry["cik_str"]).zfill(10)
    return None


def _sec_recent_filings(cik: str) -> list[dict]:
    """All recent filings of a company as dicts (form, filed, period, items, url, ...)."""
    resp = requests.get(f"https://data.sec.gov/submissions/CIK{cik}.json", headers=SEC_HEADERS, timeout=30)
    resp.raise_for_status()
    recent = resp.json().get("filings", {}).get("recent", {})
    keys = ["form", "filingDate", "reportDate", "accessionNumber", "primaryDocument", "items"]
    cols = [recent.get(k, []) for k in keys]
    out = []
    for form, filed, period, acc, doc, items in zip(*cols):
        folder = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc.replace('-', '')}"
        out.append({"form": form, "filed": filed, "period": period, "acc": acc,
                    "folder": folder, "url": f"{folder}/{doc}", "doc": doc, "items": items or ""})
    return out


def _exhibit_url(filing: dict, exhibit_type: str = "EX-99.1") -> str | None:
    """URL of an exhibit (e.g. the earnings press release) from the filing index page."""
    resp = requests.get(f"{filing['folder']}/{filing['acc']}-index.htm", headers=SEC_HEADERS, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    for tr in soup.select("table.tableFile tr"):
        cells = [td.get_text(strip=True) for td in tr.find_all("td")]
        link = tr.find("a")
        if link and len(cells) >= 4 and cells[3] == exhibit_type:
            return "https://www.sec.gov" + link["href"]
    return None


def get_sec_filings(ticker: str) -> str:
    """Key SEC filings: financial reports, earnings releases, personnel changes."""
    try:
        cik = _sec_cik(ticker)
        if not cik:
            return f"Could not find CIK for ticker: {ticker} (SEC covers US-listed companies only)"
        # Scans all recent filings: insider Form 4s can push the latest 10-K/10-Q
        # far down the list
        filings = _sec_recent_filings(cik)

        # The original 10-K holds the full annual report; a later 10-K/A is often
        # partial (e.g. only Part III), so list it in addition, never instead
        annual = [f for f in filings if f["form"] == "10-K"][:1]
        since = annual[0]["filed"] if annual else ""
        annual += [f for f in filings if f["form"] == "10-K/A" and f["filed"] >= since][:1]
        quarterly = [f for f in filings if f["form"] in ("10-Q", "10-Q/A") and f["filed"] >= since][:4]
        earnings = [f for f in filings if f["form"] == "8-K" and "2.02" in f["items"]][:4]
        cutoff = f"{date.today().year - 3}{date.today().isoformat()[4:]}"
        personnel = [f for f in filings if f["form"] in ("8-K", "8-K/A") and "5.02" in f["items"]
                     and f["filed"] >= cutoff]

        lines = [f"Key SEC filings — {ticker.upper()} (CIK {cik})", "", "## Financial reports"]
        for f in annual + quarterly:
            lines.append(f"- {f['form']} | period {f['period']} | filed {f['filed']} | {f['url']}")
        if not annual + quarterly:
            lines.append("- none found")
        lines += ["", "## Earnings releases (8-K Item 2.02)"]
        for f in earnings:
            try:
                ex = _exhibit_url(f)
            except Exception:
                ex = None
            lines.append(f"- filed {f['filed']} | press release: {ex or 'exhibit not found'} | 8-K: {f['url']}")
        if not earnings:
            lines.append("- none found")
        lines += ["", "## Key personnel changes (8-K Item 5.02: directors / officers, last 3 years)"]
        for f in personnel:
            lines.append(f"- filed {f['filed']} | items {f['items']} | {f['url']}")
        if not personnel:
            lines.append("- none in the last 3 years")
        lines += ["", "Insider holding changes: use get_insider_trading."]
        return "\n".join(lines)
    except Exception as e:
        return f"Error fetching SEC filings: {e}"


FORM4_CODES = {
    "P": "open-market buy", "S": "open-market sale", "M": "option exercise/vesting",
    "A": "grant/award", "F": "shares withheld for tax", "G": "gift", "C": "conversion",
    "J": "other (e.g. fund distribution in kind)", "D": "disposed to issuer", "X": "option exercise",
}


def _xml_val(node, path: str) -> str:
    el = node.find(path)
    return (el.text or "").strip() if el is not None and el.text else ""


def get_insider_trading(ticker: str, days: int = 180) -> str:
    """Summarize Form 4 holding changes of insiders over the last `days` days."""
    import time
    import xml.etree.ElementTree as ET
    from datetime import timedelta
    try:
        cik = _sec_cik(ticker)
        if not cik:
            return f"Could not find CIK for ticker: {ticker} (SEC covers US-listed companies only)"
        cutoff = (date.today() - timedelta(days=int(days or 180))).isoformat()
        form4s = [f for f in _sec_recent_filings(cik) if f["form"] == "4" and f["filed"] >= cutoff]
        if not form4s:
            return f"No Form 4 filings for {ticker} in the last {days} days"

        people: dict[str, dict] = {}
        seen_trades: set[tuple] = set()
        totals = {"P": 0.0, "S": 0.0}
        failed = 0
        for f in reversed(form4s):  # oldest first, so "holdings after" ends on the latest
            # primaryDocument is the XSL-rendered view; the raw XML has the same name
            xml_url = f"{f['folder']}/{f['doc'].split('/')[-1]}"
            try:
                resp = requests.get(xml_url, headers=SEC_HEADERS, timeout=30)
                resp.raise_for_status()
                root = ET.fromstring(resp.content)
            except Exception:
                failed += 1
                continue
            finally:
                time.sleep(0.12)  # SEC fair-access limit is 10 requests/second

            owner = root.find("reportingOwner")
            name = _xml_val(owner, "reportingOwnerId/rptOwnerName")
            rel = owner.find("reportingOwnerRelationship")
            roles = []
            if _xml_val(rel, "isDirector") in ("1", "true"):
                roles.append("Director")
            if _xml_val(rel, "isOfficer") in ("1", "true"):
                roles.append(_xml_val(rel, "officerTitle") or "Officer")
            if _xml_val(rel, "isTenPercentOwner") in ("1", "true"):
                roles.append("10% owner")
            plan = _xml_val(root, "aff10b5One") in ("1", "true")

            p = people.setdefault(name, {"roles": roles, "filings": 0, "buy_sh": 0.0, "buy_val": 0.0,
                                         "sell_sh": 0.0, "sell_val": 0.0, "sell_plan_sh": 0.0,
                                         "other": {}, "holdings": {}, "last": ""})
            p["filings"] += 1
            p["last"] = f["filed"]
            for tx in root.findall("nonDerivativeTable/nonDerivativeTransaction"):
                code = _xml_val(tx, "transactionCoding/transactionCode")
                shares = float(_xml_val(tx, "transactionAmounts/transactionShares/value") or 0)
                price = float(_xml_val(tx, "transactionAmounts/transactionPricePerShare/value") or 0)
                if code in ("P", "S"):
                    # Joint filers (e.g. a director and his fund) report the same trade;
                    # count it once in the company totals
                    tx_key = (_xml_val(tx, "transactionDate/value"), code, shares, price,
                              _xml_val(tx, "securityTitle/value"))
                    if tx_key not in seen_trades:
                        seen_trades.add(tx_key)
                        totals[code] += shares * price
                if code == "P":
                    p["buy_sh"] += shares
                    p["buy_val"] += shares * price
                elif code == "S":
                    p["sell_sh"] += shares
                    p["sell_val"] += shares * price
                    if plan:
                        p["sell_plan_sh"] += shares
                else:
                    label = FORM4_CODES.get(code, code)
                    p["other"][label] = p["other"].get(label, 0.0) + shares
            # Holdings after this filing, per security and direct/indirect line. Unchanged
            # lines are reported as *Holding entries, and Class B / options sit in the
            # derivative table, so all four kinds are needed (else e.g. a founder holding
            # only Class B shows as 0).
            for entry in (root.findall("nonDerivativeTable/*") + root.findall("derivativeTable/*")):
                key = (_xml_val(entry, "securityTitle/value"),
                       _xml_val(entry, "ownershipNature/directOrIndirectOwnership/value"),
                       _xml_val(entry, "ownershipNature/natureOfOwnership/value"))
                after = _xml_val(entry, "postTransactionAmounts/sharesOwnedFollowingTransaction/value")
                if after:
                    p["holdings"][key] = float(after)

        ranked = sorted(people.items(), key=lambda kv: kv[1]["sell_val"] + kv[1]["buy_val"], reverse=True)
        lines = [
            f"Insider holding changes — {ticker.upper()}, Form 4 filed {cutoff} to {date.today().isoformat()} "
            f"({len(form4s)} filings, {len(people)} people{f', {failed} unreadable' if failed else ''})",
            f"Total open-market sales ${totals['S'] / 1e6:,.1f}M, open-market buys ${totals['P'] / 1e6:,.1f}M "
            "(trades reported by joint filers counted once). Values = shares x reported price. "
            "'Holdings after' = latest reported amount per security, summed over direct and indirect "
            "lines; derivative securities (options, convertible Class B) are listed separately by title.",
        ]
        for name, p in ranked:
            parts = [f"- {name} ({', '.join(p['roles']) or 'insider'}), {p['filings']} filings, latest {p['last']}"]
            if p["sell_sh"]:
                avg = p["sell_val"] / p["sell_sh"]
                plan_pct = 100 * p["sell_plan_sh"] / p["sell_sh"]
                parts.append(f"sold {p['sell_sh']:,.0f} sh ≈ ${p['sell_val'] / 1e6:,.2f}M @avg ${avg:,.2f} "
                             f"({plan_pct:.0f}% under 10b5-1 plan)")
            if p["buy_sh"]:
                parts.append(f"bought {p['buy_sh']:,.0f} sh ≈ ${p['buy_val'] / 1e6:,.2f}M")
            if p["other"]:
                parts.append("other: " + ", ".join(f"{k} {v:,.0f} sh" for k, v in p["other"].items()))
            if p["holdings"]:
                by_title: dict[str, float] = {}
                for (title, _direct, _nature), n in p["holdings"].items():
                    by_title[title] = by_title.get(title, 0.0) + n
                parts.append("holdings after: " + ", ".join(f"{t} {n:,.0f}" for t, n in by_title.items()))
            lines.append("; ".join(parts))
        return "\n".join(lines)
    except Exception as e:
        return f"Error fetching insider trading: {e}"


# (label, unit, candidate XBRL concepts in priority order).
# "Revenues" is the total and must come first: companies with non-contract
# income (e.g. Circle's interest on USDC reserves, $2.6B of $2.7B in FY2025)
# report only a small part of revenue as RevenueFromContractWithCustomer.
# Component lines are printed only when they differ from the total.
SEC_FACTS = [
    ("Total revenue", "USD", ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax", "SalesRevenueNet"]),
    ("  of which revenue from contracts with customers", "USD", ["RevenueFromContractWithCustomerExcludingAssessedTax"]),
    ("  of which interest & dividend income (operating)", "USD", ["InterestAndDividendIncomeOperating"]),
    ("Total operating expenses", "USD", ["OperatingExpenses", "CostsAndExpenses"]),
    ("Gross profit", "USD", ["GrossProfit"]),
    ("Operating income", "USD", ["OperatingIncomeLoss"]),
    ("Net income", "USD", ["NetIncomeLoss"]),
    ("Diluted EPS", "USD/shares", ["EarningsPerShareDiluted"]),
    ("R&D expense", "USD", ["ResearchAndDevelopmentExpense"]),
    ("Sales & marketing", "USD", ["SellingAndMarketingExpense", "SellingGeneralAndAdministrativeExpense"]),
    ("Stock-based comp", "USD", ["ShareBasedCompensation", "AllocatedShareBasedCompensationExpense"]),
    ("Operating cash flow", "USD", ["NetCashProvidedByUsedInOperatingActivities"]),
    ("Capex", "USD", ["PaymentsToAcquirePropertyPlantAndEquipment"]),
    ("Buybacks", "USD", ["PaymentsForRepurchaseOfCommonStock"]),
    ("Cash & equivalents", "USD", ["CashAndCashEquivalentsAtCarryingValue"]),
    ("Marketable securities (current)", "USD", ["MarketableSecuritiesCurrent", "ShortTermInvestments", "AvailableForSaleSecuritiesDebtSecuritiesCurrent"]),
    ("Total stockholders' equity", "USD", ["StockholdersEquity"]),
    ("Long-term debt", "USD", ["LongTermDebt", "LongTermDebtNoncurrent"]),
]


def _fmt_val(val: float, unit: str) -> str:
    if unit == "USD":
        return f"{val / 1e6:,.1f}"
    return f"{val:,.2f}"


def get_sec_financial_data(ticker: str) -> str:
    """Reported financials from SEC XBRL company facts (US-listed companies)."""
    from datetime import date as _date
    try:
        cik = _sec_cik(ticker)
        if not cik:
            return f"Could not find CIK for ticker: {ticker} (SEC data covers US-listed companies only)"
        resp = requests.get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json", headers=SEC_HEADERS, timeout=30)
        resp.raise_for_status()
        facts = resp.json()
        gaap = facts.get("facts", {}).get("us-gaap", {})

        lines = [
            f"SEC XBRL reported financials — {facts.get('entityName', ticker)} (CIK {cik})",
            "Source: 10-K/10-Q as filed (actual reported values). USD amounts in USD millions. "
            "FY = fiscal year; Q = 3-month quarter, labeled by period end date (Q4 is only reported inside FY).",
        ]
        total_revenue_data = ""
        for label, unit, concepts in SEC_FACTS:
            rows = None
            for c in concepts:
                rows = gaap.get(c, {}).get("units", {}).get(unit)
                if rows:
                    break
            if not rows:
                continue
            # Same period appears in several filings; keep the latest filed value
            by_period: dict[tuple, dict] = {}
            for r in rows:
                key = (r.get("start"), r["end"])
                if key not in by_period or r.get("filed", "") > by_period[key].get("filed", ""):
                    by_period[key] = r
            if all(k[0] is None for k in by_period):  # balance-sheet (instant) item
                pts = sorted(by_period.values(), key=lambda r: r["end"])[-6:]
                lines.append(f"{label} [{unit}, period end]: " +
                             "; ".join(f"{r['end']} {_fmt_val(r['val'], unit)}" for r in pts))
                continue
            annual, quarterly = [], []
            for (start, end), r in by_period.items():
                if not start:
                    continue
                days = (_date.fromisoformat(end) - _date.fromisoformat(start)).days
                if 350 <= days <= 380:
                    annual.append(r)
                elif 80 <= days <= 100:
                    quarterly.append(r)
            annual = sorted(annual, key=lambda r: r["end"])[-4:]
            quarterly = sorted(quarterly, key=lambda r: r["end"])[-6:]
            parts = []
            if annual:
                parts.append("FY: " + "; ".join(f"FY ending {r['end']} {_fmt_val(r['val'], unit)}" for r in annual))
            if quarterly:
                parts.append("Q: " + "; ".join(f"{r['end']} {_fmt_val(r['val'], unit)}" for r in quarterly))
            if parts:
                data = " | ".join(parts)
                if label.startswith("  of which") and data == total_revenue_data:
                    continue  # component equals the total: nothing to add
                if label == "Total revenue":
                    total_revenue_data = data
                lines.append(f"{label} [{unit}] {data}")
        if len(lines) <= 2:
            return f"No us-gaap XBRL financial data found for {ticker}"
        return "\n".join(lines)
    except Exception as e:
        return f"Error fetching SEC financial data: {e}"


# Extracted page text by URL, so paging through a long filing downloads it once
_PAGE_CACHE: dict[str, str] = {}


def _fetch_page_text(url: str) -> str:
    if url in _PAGE_CACHE:
        return _PAGE_CACHE[url]
    host = urlparse(url).hostname or ""
    # SEC rejects browser-like User-Agents (403); it requires a declared one
    headers = {"User-Agent": SEC_USER_AGENT} if host == "sec.gov" or host.endswith(".sec.gov") else HEADERS
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    # Remove script/style
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)
    # Collapse whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)
    _PAGE_CACHE[url] = text
    return text


def read_url(url: str, max_chars: int = 15000, offset: int = 0, find: str = "") -> str:
    """Fetch and extract text content from a URL, one window at a time."""
    try:
        text = _fetch_page_text(url)
        total = len(text)
        start = max(0, int(offset or 0))
        if find:
            hit = text.lower().find(find.lower(), start)
            if hit < 0:
                return f"[read_url] '{find}' not found after offset {start} (page has {total:,} chars)."
            start = max(0, hit - 200)
        end = min(total, start + int(max_chars or 15000))
        window = text[start:end]
        if start == 0 and end >= total:
            return window
        more = f"; next offset={end}" if end < total else "; end of page"
        return f"[read_url] chars {start:,}-{end:,} of {total:,}{more}\n\n{window}"
    except Exception as e:
        return f"Error reading URL: {e}"


def read_local_file(file_path: str, max_chars: int = 15000) -> str:
    """Read a local file (PDF, markdown, text)."""
    path = Path(file_path).expanduser()
    if not path.exists():
        # Try relative to project
        alt = Path(__file__).parent / file_path
        if alt.exists():
            path = alt
        else:
            return f"File not found: {file_path}"

    try:
        if path.suffix.lower() == ".pdf":
            try:
                import pypdf
                reader = pypdf.PdfReader(str(path))
                text = "\n\n".join(page.extract_text() or "" for page in reader.pages)
                return text[:max_chars]
            except ImportError:
                return "pypdf not installed. Run: pip install pypdf"
        else:
            return path.read_text(encoding="utf-8", errors="replace")[:max_chars]
    except Exception as e:
        return f"Error reading file: {e}"


# ---------------------------------------------------------------------------
# Dispatcher: name → function
# ---------------------------------------------------------------------------

TOOL_DISPATCH = {
    "web_search": web_search,
    "get_stock_info": get_stock_info,
    "get_financials": get_financials,
    "get_sec_filings": get_sec_filings,
    "get_sec_financial_data": get_sec_financial_data,
    "get_insider_trading": get_insider_trading,
    "read_url": read_url,
    "read_local_file": read_local_file,
}


def execute_tool(name: str, args: dict) -> str:
    """Execute a tool by name with given arguments. Returns string result."""
    fn = TOOL_DISPATCH.get(name)
    if not fn:
        return f"Unknown tool: {name}"
    try:
        return fn(**args)
    except Exception as e:
        return f"Tool execution error ({name}): {e}"
