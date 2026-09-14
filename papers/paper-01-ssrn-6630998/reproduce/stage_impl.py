"""
paper-01-ssrn-6630998's implementation of the fixed pipeline contract
(pipeline/interface.py) -- the first paper built directly against that
interface rather than bespoke code (paper #2 predates it).

`data_dir` contract for reproduce_stage/sample_stage (documented here
since pipeline/interface.py deliberately doesn't prescribe a data format
-- that's a per-paper concern):

    data_dir/returns.csv     wide format, index=month-end date (YYYY-MM-DD),
                              one column per ticker, monthly total return
    data_dir/market_cap.csv  same shape/index, market cap in USD as of
                              each formation month (for value-weighting)

Neither file is produced by a real data pipeline yet -- see this folder's
README.md "Not built yet" section (Alpaca monthly aggregation, SEC
market-cap source). reproduce_stage/sample_stage read whatever CSVs are
at those paths; wiring real Alpaca/SEC data in means writing something
that produces those two files, not changing this module.

Industry labels come from industry_classification.get_industries (SEC
EDGAR + FF12, already real -- see that module), not a data_dir file.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from pipeline.interface import (  # noqa: E402
    ReadExtraction,
    ReproduceResult,
    SampleResult,
    VerifyResult,
)

from industry_classification import get_industries  # noqa: E402
from portfolio import monthly_long_short_returns  # noqa: E402
from reversal_signal import industry_adjusted_reversal_signal  # noqa: E402

PAPER_SLUG = "paper-01-ssrn-6630998"

REPRODUCE_ASSUMPTIONS = [
    "Industry peer mean is leave-one-out (excludes the stock itself) -- "
    "the paper says 'peers' but doesn't spell out whether that includes "
    "the stock; read the more conservative way.",
    "Industry classification is Fama-French 12, static for the whole "
    "sample -- not the paper's own (unspecified) taxonomy, and doesn't "
    "model a stock changing industry over time.",
    "Signal formed on month t's realized return, portfolio held over "
    "month t+1 -- one-month formation-to-holding lag, matching the "
    "paper's 'prior-month return' framing.",
    "Value-weighted quintiles (5 groups), matching the paper's headline "
    "Table 1-3 results, not the equal-weighted variant it also reports.",
]


def _load_panel(data_dir: Path, filename: str) -> pd.DataFrame:
    path = data_dir / filename
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found -- reproduce_stage/sample_stage expect "
            f"{filename} in data_dir (see this module's docstring for "
            f"the expected shape). No real data-fetching pipeline "
            f"produces this yet; supply it manually or via a script."
        )
    df = pd.read_csv(path, index_col=0, parse_dates=True)
    return df


def _run_backtest(data_dir: Path, industry_map: pd.Series | None = None) -> pd.DataFrame:
    returns = _load_panel(data_dir, "returns.csv")
    market_cap = _load_panel(data_dir, "market_cap.csv")

    if industry_map is None:
        industries_df = get_industries(list(returns.columns))
        industry_map = industries_df.set_index("ticker")["industry"]

    signal = industry_adjusted_reversal_signal(returns, industry_map)
    return monthly_long_short_returns(signal, returns, market_cap, n_groups=5)


def reproduce_stage(
    extraction: ReadExtraction, data_dir: Path, industry_map: pd.Series | None = None
) -> ReproduceResult:
    """
    Real implementation for this paper. Loads returns.csv/market_cap.csv
    from data_dir (see module docstring), computes the industry-adjusted
    reversal signal, runs the quintile value-weighted long-short
    backtest, and returns the resulting monthly return series.

    `industry_map` is exposed as an override purely for testing (skip the
    live SEC calls) -- production callers should omit it and let this
    function derive industries from the tickers in returns.csv.
    """
    monthly = _run_backtest(data_dir, industry_map=industry_map)
    return ReproduceResult(
        paper_slug=PAPER_SLUG,
        returns=monthly["long_short_return"],
        positions=monthly[["n_long", "n_short"]],
        assumptions=list(REPRODUCE_ASSUMPTIONS),
        notes=(
            f"{len(monthly)} monthly observations, "
            f"{monthly.index.min()} to {monthly.index.max()}."
            if len(monthly)
            else "No monthly observations produced."
        ),
    )


def verify_stage(
    reproduce_result: ReproduceResult,
    extraction: ReadExtraction,
    target_label: str = "United States",
    target_metric_keyword: str = "industry",
    tolerance_pct_points: float = 0.20,
) -> VerifyResult:
    """
    Compares reproduce_result's mean monthly return against the paper's
    own published number for `target_label` (default: the US row --
    the only market Alpaca-sourced data can realistically cover; see
    read_notes.md on why US is the paper's *weakest* major-market result,
    not its strongest).

    `comparable=False` is the correct, expected outcome when no matching
    row exists in extraction.key_results, or when reproduce_result has no
    usable observations -- not an error.
    """
    if reproduce_result.returns is None or len(reproduce_result.returns.dropna()) == 0:
        return VerifyResult(
            comparable=False,
            skip_reason="reproduce_result has no non-NaN monthly returns to compare",
        )

    match = next(
        (
            r
            for r in extraction.key_results
            if target_label.lower() in r.get("label", "").lower()
            and target_metric_keyword.lower() in r.get("metric", "").lower()
        ),
        None,
    )
    if match is None:
        return VerifyResult(
            comparable=False,
            skip_reason=(
                f"No key_results row found matching label={target_label!r} "
                f"metric containing {target_metric_keyword!r}"
            ),
        )

    try:
        paper_value = float(str(match["value"]).replace("%", "").strip())
    except (KeyError, ValueError):
        return VerifyResult(
            comparable=False,
            skip_reason=f"Could not parse a numeric value from key_results row: {match!r}",
        )

    our_value = float(reproduce_result.returns.dropna().mean()) * 100  # to percent, matching paper units
    within = abs(our_value - paper_value) <= tolerance_pct_points

    return VerifyResult(
        comparable=True,
        our_value=our_value,
        paper_value=paper_value,
        within_tolerance=within,
        notes=(
            f"Our mean monthly long-short return: {our_value:.3f}%. "
            f"Paper's {target_label} figure: {paper_value:.3f}%. "
            f"Tolerance: +/-{tolerance_pct_points} pct points."
        ),
    )


def sample_stage(reproduce_result: ReproduceResult, data_dir: Path) -> SampleResult:
    """
    Re-runs the same backtest mechanism against whatever's in data_dir --
    intended to be a CURRENT (2016+) data window, separate from any
    period used for a Verify comparison. Same mechanism as
    reproduce_stage; the difference is meant to be the data_dir contents,
    not the code path.
    """
    monthly = _run_backtest(data_dir)
    non_null = monthly["long_short_return"].dropna()

    summary_stats = {}
    if len(non_null):
        summary_stats = {
            "mean_monthly_return_pct": float(non_null.mean()) * 100,
            "n_months": int(len(non_null)),
            "pct_positive_months": float((non_null > 0).mean()) * 100,
        }

    return SampleResult(
        paper_slug=PAPER_SLUG,
        period_start=str(monthly.index.min()) if len(monthly) else "n/a",
        period_end=str(monthly.index.max()) if len(monthly) else "n/a",
        returns=monthly["long_short_return"],
        summary_stats=summary_stats,
    )
