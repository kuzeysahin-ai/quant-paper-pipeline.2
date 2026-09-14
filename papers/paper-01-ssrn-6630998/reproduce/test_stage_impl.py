"""
Exercises reproduce_stage/verify_stage/sample_stage end to end against
synthetic CSVs (no live SEC/Alpaca calls -- industry_map is injected
directly, sidestepping industry_classification's network dependency).
"""
import pandas as pd
import pytest

# stage_impl adds the repo root to sys.path as an import-time side effect
# -- import it before pipeline.interface, or the latter 404s under pytest.
from stage_impl import reproduce_stage, sample_stage, verify_stage
from pipeline.interface import ReadExtraction, ReproduceResult


def _dummy_extraction(key_results=None):
    return ReadExtraction(
        title="t",
        authors=["a"],
        venue=None,
        year=None,
        data_sample="d",
        signals=[],
        portfolio_construction="p",
        key_results=key_results or [],
        central_claim="c",
        testability_notes="n",
        open_questions=[],
    )


def _write_synthetic_data(tmp_path):
    dates = pd.to_datetime(["2020-01-31", "2020-02-29", "2020-03-31"])
    tickers = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"]
    returns = pd.DataFrame(0.01, index=dates, columns=tickers)
    market_cap = pd.DataFrame(1_000_000.0, index=dates, columns=tickers)
    returns.to_csv(tmp_path / "returns.csv")
    market_cap.to_csv(tmp_path / "market_cap.csv")
    industry_map = pd.Series(
        {t: ("Tech" if i % 2 == 0 else "Energy") for i, t in enumerate(tickers)}
    )
    return industry_map


def test_reproduce_stage_missing_data_dir_raises_clear_error(tmp_path):
    with pytest.raises(FileNotFoundError, match="returns.csv"):
        reproduce_stage(_dummy_extraction(), tmp_path)


def test_reproduce_stage_end_to_end(tmp_path):
    industry_map = _write_synthetic_data(tmp_path)
    result = reproduce_stage(_dummy_extraction(), tmp_path, industry_map=industry_map)

    assert isinstance(result, ReproduceResult)
    assert result.paper_slug == "paper-01-ssrn-6630998"
    assert len(result.assumptions) > 0  # design decisions must be documented, not silent
    assert len(result.returns) == 2  # 3 months of data -> 2 holding-period observations


def test_verify_stage_skips_when_no_matching_row(tmp_path):
    industry_map = _write_synthetic_data(tmp_path)
    reproduce_result = reproduce_stage(_dummy_extraction(), tmp_path, industry_map=industry_map)

    verify_result = verify_stage(reproduce_result, _dummy_extraction(key_results=[]))
    assert verify_result.comparable is False
    assert verify_result.skip_reason is not None


def test_verify_stage_compares_when_row_present(tmp_path):
    industry_map = _write_synthetic_data(tmp_path)
    reproduce_result = reproduce_stage(_dummy_extraction(), tmp_path, industry_map=industry_map)

    extraction = _dummy_extraction(
        key_results=[
            {
                "label": "United States",
                "metric": "industry-adjusted reversal monthly return",
                "value": "0.34",
                "significance": "t=2.12",
            }
        ]
    )
    verify_result = verify_stage(reproduce_result, extraction)
    assert verify_result.comparable is True
    assert verify_result.paper_value == pytest.approx(0.34)
    assert verify_result.our_value is not None


def test_verify_stage_handles_empty_returns():
    empty_result = ReproduceResult(paper_slug="x", returns=pd.Series(dtype=float))
    verify_result = verify_stage(empty_result, _dummy_extraction())
    assert verify_result.comparable is False


def test_sample_stage_end_to_end(tmp_path):
    _write_synthetic_data(tmp_path)
    # sample_stage derives industries itself (no override param) -- but
    # since every ticker has identical returns/market caps here, the
    # quintile split degenerates to an all-tie rank; we only assert the
    # plumbing works end to end, not specific numeric output.
    import stage_impl

    stage_impl.get_industries = lambda tickers: pd.DataFrame(
        {"ticker": tickers, "industry": ["Tech" if i % 2 == 0 else "Energy" for i in range(len(tickers))]}
    )

    dummy_reproduce_result = ReproduceResult(paper_slug="paper-01-ssrn-6630998", returns=pd.Series(dtype=float))
    result = sample_stage(dummy_reproduce_result, tmp_path)

    assert result.paper_slug == "paper-01-ssrn-6630998"
    assert result.period_start != "n/a"
    assert "n_months" in result.summary_stats
