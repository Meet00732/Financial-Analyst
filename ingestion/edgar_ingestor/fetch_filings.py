#!/usr/bin/env python3
"""
pipeline.py

Combined ingestion pipeline for MarketScope MVP:
- Fetches latest SEC filings (text sections + XBRL facts) via EdgarTools
- Fetches historical market data and fundamentals via yfinance
- Supports top N S&P 500 tickers dynamically
"""

import time
import json
from edgar import Company, set_identity
import yfinance as yf
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
from utils import *
from storage import *

# === Configuration ===
IDENTITY = get_secret("marketscope-EDGAR_IDENTITY")
FORM_TYPE = "10-K"
TOP_N = 10
MARKET_PERIOD = "5y"
MARKET_INTERVAL = "1d"
RATE_LIMIT_SEC = 0.2

# === Identity for EdgarTools ===
set_identity(IDENTITY)



def fetch_edgar_filings(form_type: str = FORM_TYPE, top_n: int = TOP_N) -> list[dict]:
    """
    Fetch latest `form_type` filings and company XBRL facts for top N S&P companies.

    Returns:
        List of dicts with keys: ticker, filing_date, source_url, sections, xbrl_facts
    """
    docs = []
    for ticker in get_sp500_tickers(top_n):
        comp = Company(ticker)
        filings = comp.get_filings(form=form_type)
        latest = filings.latest()

        # 1) Rate limit
        time.sleep(RATE_LIMIT_SEC)

        # 2) Extract text sections
        html = latest.html()
        sections = extract_sections(html)

        # 3) Build the *correct* SEC URL
        # EdgarTools gives you:
        cik_str = latest.cik            # e.g. "0000320193"
        accession = latest.accession_no    # e.g. "0000320193-25-000056"
        # strip leading zeros on CIK for folder path
        cik_num = str(int(cik_str))
        acc_no_dashes = accession.replace("-", "")
        sec_url = (
            f"https://www.sec.gov/Archives/edgar/data/"
            f"{cik_num}/{acc_no_dashes}/{acc_no_dashes}-index.html"
        )

        # 4) Pull XBRL facts as before
        facts = comp.get_facts().to_pandas().to_dict(orient="records")

        docs.append({
            "ticker": ticker,
            "filing_date": latest.filing_date,
            "source_url": sec_url,       # ← now correct
            "sections": sections,
            "xbrl_facts": facts,
        })

        time.sleep(RATE_LIMIT_SEC)
    return docs


def fetch_market_data(ticker: str, period: str = "5y", interval: str = "1d") -> dict:
    """
    Fetch historical market data and key fundamentals for `ticker`.
    """
    tk = yf.Ticker(ticker)
    hist = tk.history(period=period, interval=interval)
    info = tk.info
    fundamentals = {
        "trailingPE": info.get("trailingPE"),
        "forwardPE": info.get("forwardPE"),
        "returnOnEquity": info.get("returnOnEquity"),
        "debtToEquity": info.get("debtToEquity"),
    }
    return {"history": hist, "fundamentals": fundamentals}


# if __name__ == "__main__":
#     # 1) Ingest filings
#     results = fetch_edgar_filings()
#     save_filings(results)
#     # print(json.dumps(results, indent=2, default=str))

#     # 2) Enrich with market data
#     for doc in results:
#         mdata = fetch_market_data(doc['ticker'])
#         save_market_data(doc['ticker'], mdata)
#         doc['market_data'] = {
#             'fundamentals': mdata['fundamentals'],
#             'recent_history': mdata['history'].tail().to_dict(orient='list')
#         }

#     # 3) Save combined snapshot
#     save_combined(results)