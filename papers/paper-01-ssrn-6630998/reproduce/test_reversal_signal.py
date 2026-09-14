import numpy as np
import pandas as pd
import pytest

from reversal_signal import industry_adjusted_reversal_signal, leave_one_out_industry_mean


def test_leave_one_out_excludes_self():
    row = pd.Series({"A": 0.10, "B": 0.20, "C": 0.30, "D": -0.05})
    industry = pd.Series({"A": "Tech", "B": "Tech", "C": "Tech", "D": "Energy"})
    loo = leave_one_out_industry_mean(row, industry)
    # A's peers are B, C -> mean = 0.25
    assert loo["A"] == pytest.approx(0.25)
    # B's peers are A, C -> mean = 0.20
    assert loo["B"] == pytest.approx(0.20)
    # C's peers are A, B -> mean = 0.15
    assert loo["C"] == pytest.approx(0.15)
    # D is alone in Energy -> no peers -> NaN
    assert pd.isna(loo["D"])


def test_leave_one_out_missing_return_or_industry_excluded():
    row = pd.Series({"A": 0.10, "B": np.nan, "C": 0.30})
    industry = pd.Series({"A": "Tech", "B": "Tech", "C": "Tech"})
    loo = leave_one_out_industry_mean(row, industry)
    # B has no return -> excluded from group, doesn't pollute A/C's means,
    # and B itself is NaN in the output
    assert pd.isna(loo["B"])
    # A's only remaining peer is C -> mean = 0.30
    assert loo["A"] == pytest.approx(0.30)


def test_industry_adjusted_signal_matches_definition():
    returns = pd.DataFrame(
        {
            "A": [0.10, 0.05],
            "B": [0.20, 0.00],
            "C": [0.30, -0.10],
        },
        index=pd.to_datetime(["2020-01-31", "2020-02-29"]),
    )
    industry = pd.Series({"A": "Tech", "B": "Tech", "C": "Tech"})
    sig = industry_adjusted_reversal_signal(returns, industry)

    # Jan: A's peers B,C -> mean 0.25 -> signal = 0.10 - 0.25 = -0.15
    assert sig.loc["2020-01-31", "A"] == pytest.approx(-0.15)
    # Jan: C's peers A,B -> mean 0.15 -> signal = 0.30 - 0.15 = 0.15
    assert sig.loc["2020-01-31", "C"] == pytest.approx(0.15)
