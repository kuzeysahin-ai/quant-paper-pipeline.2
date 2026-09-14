"""
Exercises the orchestrator end to end: Read -> Reproduce -> Verify ->
Sample, one call, for paper #1. Read is monkeypatched (no
ANTHROPIC_API_KEY / real API spend needed for this test) -- Reproduce,
Verify, and Sample run for real against synthetic data, through the
actual dispatch mechanism in pipeline/interface.py.
"""
import pandas as pd

import pipeline.run as run_module
from pipeline.interface import ReadExtraction, _PAPERS_DIR

PAPER_01_DIR = _PAPERS_DIR / "paper-01-ssrn-6630998"


def _fake_extraction():
    return ReadExtraction(
        title="fake paper for orchestrator test",
        authors=["a"],
        venue=None,
        year=None,
        data_sample="d",
        signals=[],
        portfolio_construction="p",
        key_results=[],  # empty -> Verify will report comparable=False, not an error
        central_claim="c",
        testability_notes="n",
        open_questions=["one open question"],
    )


def _write_synthetic_data(data_dir):
    data_dir.mkdir(parents=True, exist_ok=True)
    dates = pd.to_datetime(["2020-01-31", "2020-02-29", "2020-03-31"])
    tickers = [f"T{i}" for i in range(10)]
    pd.DataFrame(0.01, index=dates, columns=tickers).to_csv(data_dir / "returns.csv")
    pd.DataFrame(1_000_000.0, index=dates, columns=tickers).to_csv(
        data_dir / "market_cap.csv"
    )


def test_run_pipeline_end_to_end(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    _write_synthetic_data(data_dir)

    monkeypatch.setattr(run_module, "read_stage", lambda paper_dir, force=False: _fake_extraction())

    result = run_module.run_pipeline(PAPER_01_DIR, data_dir=data_dir)

    assert result.extraction.title == "fake paper for orchestrator test"
    assert result.reproduce.paper_slug == "paper-01-ssrn-6630998"
    assert result.verify.comparable is False  # empty key_results -> nothing to compare against
    assert result.sample.paper_slug == "paper-01-ssrn-6630998"
