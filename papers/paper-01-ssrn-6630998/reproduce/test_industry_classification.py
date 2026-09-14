"""
Unit tests for the SIC -> FF12 mapping logic (pure function, no network).
Network-dependent behavior (SEC fetches, caching) is exercised manually --
see this folder's README.md -- rather than in the automated test suite,
so CI/repeated runs don't depend on SEC EDGAR being reachable.
"""
from industry_classification import sic_to_ff12


def test_known_boundaries():
    # Spot-checked against real tickers via SEC EDGAR (see README.md):
    # AAPL/MSFT sic=3571/7372 -> BusEq, JPM sic=6021 -> Money,
    # XOM sic=2911 -> Enrgy, KO sic=2080 -> NoDur, JNJ sic=2834 -> Hlth,
    # T sic=4813 -> Telcm, DUK sic=4931 -> Utils.
    assert sic_to_ff12(3571) == "BusEq"
    assert sic_to_ff12(7372) == "BusEq"
    assert sic_to_ff12(6021) == "Money"
    assert sic_to_ff12(2911) == "Enrgy"
    assert sic_to_ff12(2080) == "NoDur"
    assert sic_to_ff12(2834) == "Hlth"
    assert sic_to_ff12(4813) == "Telcm"
    assert sic_to_ff12(4931) == "Utils"


def test_range_edges_inclusive():
    # NoDur includes 0100-0999 -- check both boundary values land inside.
    assert sic_to_ff12(100) == "NoDur"
    assert sic_to_ff12(999) == "NoDur"
    # One past the boundary should NOT be NoDur (falls into Manuf's 2520-2589
    # only starting at 2520; 1000-1199 belongs to nothing listed -> Other).
    assert sic_to_ff12(1000) == "Other"


def test_missing_or_none_defaults_to_other():
    assert sic_to_ff12(None) == "Other"


def test_unmatched_sic_defaults_to_other():
    # SIC 1500 (general building construction) has no FF12 range listed --
    # it belongs in the "Other" catch-all group, by design (see FF12_RANGES
    # docstring: group 12 has no explicit ranges in the source file).
    assert sic_to_ff12(1500) == "Other"
