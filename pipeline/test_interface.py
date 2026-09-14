"""
Confirms the pipeline interface actually dispatches to real per-paper
implementations -- not just that the functions exist, but that calling
them through pipeline.interface reaches paper #1's real
reproduce_stage/verify_stage/sample_stage and produces a real result.
"""
import pandas as pd
import pytest

from pipeline.interface import (
    ReadExtraction,
    ReproduceResult,
    SampleResult,
    VerifyResult,
    _PAPERS_DIR,
    reproduce_stage,
    sample_stage,
    verify_stage,
)

PAPER_01_DIR = _PAPERS_DIR / "paper-01-ssrn-6630998"


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
    tickers = [f"T{i}" for i in range(10)]
    returns = pd.DataFrame(0.01, index=dates, columns=tickers)
    market_cap = pd.DataFrame(1_000_000.0, index=dates, columns=tickers)
    returns.to_csv(tmp_path / "returns.csv")
    market_cap.to_csv(tmp_path / "market_cap.csv")


def test_reproduce_stage_dispatches_to_paper_01(tmp_path):
    _write_synthetic_data(tmp_path)

    # Tickers T0..T9 are fake and won't resolve via SEC's ticker->CIK
    # map, so they all default to industry="Other" -- exercises the
    # dispatch path with no live network call (ticker_cik.json is
    # already cached on disk from earlier testing; a lookup miss never
    # reaches the per-CIK SEC endpoint).
    result = reproduce_stage(_dummy_extraction(), tmp_path, PAPER_01_DIR)

    assert isinstance(result, ReproduceResult)
    assert result.paper_slug == "paper-01-ssrn-6630998"
    assert len(result.returns) == 2  # 3 months of data -> 2 holding-period observations
    assert len(result.assumptions) > 0  # documented, not silently assumed


def test_verify_stage_dispatches_via_paper_slug(tmp_path):
    _write_synthetic_data(tmp_path)
    reproduce_result = reproduce_stage(_dummy_extraction(), tmp_path, PAPER_01_DIR)

    result = verify_stage(reproduce_result, _dummy_extraction(key_results=[]))
    assert isinstance(result, VerifyResult)
    assert result.comparable is False  # no matching row in an empty key_results


def test_sample_stage_dispatches_via_paper_slug(tmp_path):
    _write_synthetic_data(tmp_path)
    reproduce_result = reproduce_stage(_dummy_extraction(), tmp_path, PAPER_01_DIR)

    result = sample_stage(reproduce_result, tmp_path)
    assert isinstance(result, SampleResult)
    assert result.paper_slug == "paper-01-ssrn-6630998"


def test_dispatch_to_unimplemented_paper_fails_loudly():
    fake_paper_dir = _PAPERS_DIR / "paper-99-does-not-exist"
    with pytest.raises(FileNotFoundError, match="stage_impl.py"):
        reproduce_stage(_dummy_extraction(), data_dir=None, paper_dir=fake_paper_dir)


def test_result_dataclasses_construct_with_stated_fields():
    VerifyResult(comparable=False, skip_reason="no period overlap")
    SampleResult(
        paper_slug="paper-00-dummy",
        period_start="2016-01-01",
        period_end="2026-01-01",
        returns=None,
    )
