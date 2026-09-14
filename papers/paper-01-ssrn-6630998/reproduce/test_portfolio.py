import pandas as pd
import pytest

from portfolio import monthly_long_short_returns, quintile_long_short_tickers, value_weighted_return


def test_quintile_long_short_tickers_bottom_and_top():
    # 10 tickers -> quintile = 2 per leg
    signal = pd.Series({f"T{i}": i for i in range(10)})  # T0=0 (worst) ... T9=9 (best)
    market_cap = pd.Series({f"T{i}": 1.0 for i in range(10)})
    long_t, short_t = quintile_long_short_tickers(signal, market_cap, n_groups=5)
    assert long_t == {"T0", "T1"}
    assert short_t == {"T8", "T9"}


def test_quintile_excludes_missing_market_cap():
    signal = pd.Series({"A": 0, "B": 1, "C": 2, "D": 3, "E": 4})
    market_cap = pd.Series({"A": 1.0, "C": 1.0, "D": 1.0, "E": 1.0})  # B missing
    long_t, short_t = quintile_long_short_tickers(signal, market_cap, n_groups=5)
    assert "B" not in long_t | short_t


def test_value_weighted_return_basic():
    tickers = {"A", "B"}
    returns = pd.Series({"A": 0.10, "B": 0.20})
    market_cap = pd.Series({"A": 100.0, "B": 300.0})
    # weights: A=0.25, B=0.75 -> 0.25*0.10 + 0.75*0.20 = 0.175
    assert value_weighted_return(tickers, returns, market_cap) == pytest.approx(0.175)


def test_value_weighted_return_nan_when_nothing_usable():
    assert pd.isna(value_weighted_return({"X"}, pd.Series({"Y": 0.1}), pd.Series({"Y": 1.0})))


def test_monthly_long_short_returns_end_to_end_persistent_loser_and_winner():
    dates = pd.to_datetime(["2020-01-31", "2020-02-29", "2020-03-31"])
    # 10 tickers, strictly distinct signal values every month (T0 lowest
    # .. T9 highest) so ranking is unambiguous -- with 8 tied at the same
    # value, pandas' average-rank tie-breaking pushes them all to the
    # same percentile and none land cleanly in either quintile.
    row = {f"T{i}": float(i) for i in range(10)}
    signal = pd.DataFrame([row, row, row], index=dates)
    returns = signal.copy()  # reuse shape; values don't need to match signal
    market_cap = pd.DataFrame(1.0, index=dates, columns=signal.columns)

    result = monthly_long_short_returns(signal, returns, market_cap, n_groups=5)

    assert list(result.index) == list(dates[1:])
    assert (result["n_long"] == 2).all()
    assert (result["n_short"] == 2).all()
