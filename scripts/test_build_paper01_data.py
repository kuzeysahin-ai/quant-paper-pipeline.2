"""
Unit tests for the pure aggregation/point-in-time logic in
build_paper01_data.py -- synthetic data only, no network calls.
"""
import pandas as pd
import pytest

from build_paper01_data import (
    build_market_cap_panel,
    monthly_close_and_returns,
    select_point_in_time_value,
)


def test_monthly_close_and_returns_picks_last_trading_day():
    # Irregular daily dates (simulating weekends/holidays missing),
    # spanning parts of 3 calendar months.
    dates = pd.to_datetime(
        ["2020-01-30", "2020-01-31", "2020-02-27", "2020-02-28", "2020-03-30", "2020-03-31"]
    )
    daily = pd.DataFrame({"A": [100, 101, 110, 112, 90, 91]}, index=dates)

    monthly_close, monthly_returns = monthly_close_and_returns(daily)

    assert list(monthly_close["A"]) == [101, 112, 91]
    assert pd.isna(monthly_returns["A"].iloc[0])  # no prior month
    assert monthly_returns["A"].iloc[1] == pytest.approx(112 / 101 - 1)
    assert monthly_returns["A"].iloc[2] == pytest.approx(91 / 112 - 1)


def test_monthly_close_and_returns_handles_gaps_across_tickers():
    dates = pd.to_datetime(["2020-01-31", "2020-02-28"])
    daily = pd.DataFrame({"A": [100, 110], "B": [50, None]}, index=dates)
    monthly_close, monthly_returns = monthly_close_and_returns(daily)
    assert pd.isna(monthly_close["B"].iloc[1])
    assert pd.isna(monthly_returns["B"].iloc[1])  # missing price -> missing return, not zero


def test_select_point_in_time_value_picks_latest_filed_not_latest_end():
    entries = [
        {"end": "2020-06-30", "filed": "2020-08-01", "val": 1000},  # filed AFTER as_of below
        {"end": "2020-03-31", "filed": "2020-05-01", "val": 900},
        {"end": "2019-12-31", "filed": "2020-02-01", "val": 800},
    ]
    as_of = pd.Timestamp("2020-06-01")  # before the 2020-08-01 filing, after the 2020-05-01 one
    assert select_point_in_time_value(entries, as_of) == 900


def test_select_point_in_time_value_none_before_any_filing():
    entries = [{"end": "2020-03-31", "filed": "2020-05-01", "val": 900}]
    assert select_point_in_time_value(entries, pd.Timestamp("2020-01-01")) is None


def test_select_point_in_time_value_avoids_lookahead():
    """The whole point of using `filed` over `end`: a report covering an
    earlier period but filed later must not be usable before it's
    actually filed, even if its `end` date is old."""
    entries = [
        {"end": "2020-01-01", "filed": "2020-09-01", "val": 999},  # old 'end', late 'filed'
    ]
    # as_of is well after 'end' but before 'filed' -- must NOT see this value.
    assert select_point_in_time_value(entries, pd.Timestamp("2020-06-01")) is None


def test_build_market_cap_panel_multiplies_shares_by_price():
    dates = pd.to_datetime(["2020-01-31", "2020-02-29"])
    monthly_close = pd.DataFrame({"A": [10.0, 12.0]}, index=dates)
    shares_by_ticker = {
        "A": [{"end": "2019-12-31", "filed": "2020-01-15", "val": 100}],
    }
    market_cap = build_market_cap_panel(monthly_close, shares_by_ticker)
    assert market_cap.loc[dates[0], "A"] == pytest.approx(1000.0)  # 100 shares * 10.0
    assert market_cap.loc[dates[1], "A"] == pytest.approx(1200.0)  # 100 shares * 12.0


def test_build_market_cap_panel_nan_when_no_shares_data():
    dates = pd.to_datetime(["2020-01-31"])
    monthly_close = pd.DataFrame({"A": [10.0], "B": [20.0]}, index=dates)
    shares_by_ticker = {"A": [{"end": "2019-12-31", "filed": "2020-01-01", "val": 5}]}  # B missing entirely
    market_cap = build_market_cap_panel(monthly_close, shares_by_ticker)
    assert market_cap.loc[dates[0], "A"] == pytest.approx(50.0)
    assert pd.isna(market_cap.loc[dates[0], "B"])


def test_build_market_cap_panel_nan_when_price_missing():
    dates = pd.to_datetime(["2020-01-31"])
    monthly_close = pd.DataFrame({"A": [None]}, index=dates)
    shares_by_ticker = {"A": [{"end": "2019-12-31", "filed": "2020-01-01", "val": 5}]}
    market_cap = build_market_cap_panel(monthly_close, shares_by_ticker)
    assert pd.isna(market_cap.loc[dates[0], "A"])
