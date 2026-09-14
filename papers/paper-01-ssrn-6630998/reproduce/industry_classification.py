"""
Free US industry classification, resolving the blocker noted in
read_notes.md: Alpaca provides no sector/industry field (confirmed by
inspecting its asset metadata directly -- see STATUS.md), so this pulls
SIC codes from SEC EDGAR (free, official, covers all SEC-reporting
companies) and maps them to the Fama-French 12-industry scheme (free,
well-established, standard in academic finance -- not the paper's exact
grouping, since Stosik & Zaremba don't specify their industry taxonomy,
but a defensible, citable, widely-used choice rather than an invented one).

SEC EDGAR usage policy: requires a descriptive User-Agent with contact
info, and asks for a max of ~10 requests/second. This module is
deliberately polite (small delay between requests) and caches results to
disk so a given ticker is only ever fetched once.

Data sources:
  - https://www.sec.gov/files/company_tickers.json (ticker -> CIK)
  - https://data.sec.gov/submissions/CIK##########.json (CIK -> SIC code)
  - Fama-French 12-industry SIC ranges: Ken French's data library,
    https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/Siccodes12.zip
    (fetched 2026-09-14; ranges hardcoded below with that source cited --
    this file changes rarely enough that hardcoding is reasonable, but if
    results look suspicious, re-fetch and diff before trusting old ranges)
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import pandas as pd
import requests

CACHE_DIR = Path(__file__).parent / "cache"
TICKER_CIK_CACHE = CACHE_DIR / "ticker_cik.json"
SIC_CACHE = CACHE_DIR / "cik_sic.json"

USER_AGENT = "quant-paper-pipeline research kuzey8113@gmail.com"
REQUEST_DELAY_SECONDS = 0.15  # ~6-7 req/sec, comfortably under SEC's ~10/sec guidance

# Fama-French 12 industries, SIC code ranges (inclusive). Source: see
# module docstring. Group 12 ("Other") is everything not matched below.
FF12_RANGES: dict[str, list[tuple[int, int]]] = {
    "NoDur": [(100, 999), (2000, 2399), (2700, 2749), (2770, 2799), (3100, 3199), (3940, 3989)],
    "Durbl": [(2500, 2519), (2590, 2599), (3630, 3659), (3710, 3711), (3714, 3714), (3716, 3716), (3750, 3751), (3792, 3792), (3900, 3939), (3990, 3999)],
    "Manuf": [(2520, 2589), (2600, 2699), (2750, 2769), (3000, 3099), (3200, 3569), (3580, 3629), (3700, 3709), (3712, 3713), (3715, 3715), (3717, 3749), (3752, 3791), (3793, 3799), (3830, 3839), (3860, 3899)],
    "Enrgy": [(1200, 1399), (2900, 2999)],
    "Chems": [(2800, 2829), (2840, 2899)],
    "BusEq": [(3570, 3579), (3660, 3692), (3694, 3699), (3810, 3829), (7370, 7379)],
    "Telcm": [(4800, 4899)],
    "Utils": [(4900, 4949)],
    "Shops": [(5000, 5999), (7200, 7299), (7600, 7699)],
    "Hlth": [(2830, 2839), (3693, 3693), (3840, 3859), (8000, 8099)],
    "Money": [(6000, 6999)],
    # "Other" has no listed ranges in the source file -- it's the catch-all.
}


def sic_to_ff12(sic: int | None) -> str:
    """Map a 4-digit SIC code to one of the 12 Fama-French industry
    groups. Returns "Other" for unmatched or missing codes -- this is the
    correct behavior per the FF12 definition (Group 12 has no explicit
    ranges; it's everything else), not a fallback covering an error.
    """
    if sic is None:
        return "Other"
    for group, ranges in FF12_RANGES.items():
        for lo, hi in ranges:
            if lo <= sic <= hi:
                return group
    return "Other"


def _load_cache(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def _save_cache(path: Path, data: dict) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=0), encoding="utf-8")


def fetch_ticker_to_cik(force_refresh: bool = False) -> dict[str, int]:
    """ticker (upper-case) -> CIK (int). Cached to disk -- this file is
    ~800KB and changes slowly; re-fetch manually (force_refresh=True) if
    working with a ticker that's IPO'd recently and comes back missing.
    """
    if not force_refresh:
        cached = _load_cache(TICKER_CIK_CACHE)
        if cached:
            return {k: int(v) for k, v in cached.items()}

    resp = requests.get(
        "https://www.sec.gov/files/company_tickers.json",
        headers={"User-Agent": USER_AGENT},
        timeout=30,
    )
    resp.raise_for_status()
    raw = resp.json()  # {"0": {"cik_str": ..., "ticker": ..., "title": ...}, ...}
    mapping = {row["ticker"].upper(): int(row["cik_str"]) for row in raw.values()}
    _save_cache(TICKER_CIK_CACHE, mapping)
    return mapping


def fetch_sic_for_cik(cik: int, sic_cache: dict) -> int | None:
    """SIC code for one CIK, via SEC's per-company submissions endpoint.
    `sic_cache` is mutated in place (caller is responsible for persisting
    it -- see get_industries, which batches many lookups and saves once).
    """
    key = str(cik)
    if key in sic_cache:
        return sic_cache[key]

    cik_padded = f"{cik:010d}"
    resp = requests.get(
        f"https://data.sec.gov/submissions/CIK{cik_padded}.json",
        headers={"User-Agent": USER_AGENT},
        timeout=30,
    )
    time.sleep(REQUEST_DELAY_SECONDS)
    if resp.status_code != 200:
        sic_cache[key] = None
        return None
    data = resp.json()
    sic_raw = data.get("sic")
    sic = int(sic_raw) if sic_raw not in (None, "") else None
    sic_cache[key] = sic
    return sic


def get_industries(tickers: list[str]) -> pd.DataFrame:
    """
    For each ticker: look up its CIK, fetch its SIC code (cached), map to
    an FF12 industry group. Returns a DataFrame with columns:
    ticker, cik, sic, industry. Tickers not found in SEC's ticker->CIK
    file (e.g. delisted, OTC-only, or too new) get cik=None, sic=None,
    industry="Other" -- and are flagged via a printed warning, since
    silently dropping them could bias which stocks make it into the
    industry-adjusted signal.
    """
    ticker_to_cik = fetch_ticker_to_cik()
    sic_cache = _load_cache(SIC_CACHE)

    rows = []
    not_found = []
    for t in tickers:
        cik = ticker_to_cik.get(t.upper())
        if cik is None:
            not_found.append(t)
            rows.append({"ticker": t, "cik": None, "sic": None, "industry": "Other"})
            continue
        sic = fetch_sic_for_cik(cik, sic_cache)
        rows.append({"ticker": t, "cik": cik, "sic": sic, "industry": sic_to_ff12(sic)})

    _save_cache(SIC_CACHE, sic_cache)

    if not_found:
        print(
            f"WARNING: {len(not_found)}/{len(tickers)} tickers not found in "
            f"SEC's ticker->CIK mapping, defaulted to industry='Other': "
            f"{not_found[:20]}{'...' if len(not_found) > 20 else ''}"
        )

    return pd.DataFrame(rows)
