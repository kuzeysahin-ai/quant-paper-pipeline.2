"""
Confirms the pipeline skeleton is real, importable code -- not just
prose. Each stub must exist with the right signature and fail loudly
(NotImplementedError), not silently return a fake result, until it's
actually implemented.
"""
import pytest

from pipeline.interface import (
    ReadExtraction,
    ReproduceResult,
    SampleResult,
    VerifyResult,
    reproduce_stage,
    sample_stage,
    verify_stage,
)


def _dummy_extraction() -> ReadExtraction:
    return ReadExtraction(
        title="t",
        authors=["a"],
        venue=None,
        year=None,
        data_sample="d",
        signals=[],
        portfolio_construction="p",
        key_results=[],
        central_claim="c",
        testability_notes="n",
        open_questions=[],
    )


def _dummy_reproduce_result() -> ReproduceResult:
    return ReproduceResult(paper_slug="paper-00-dummy", returns=None)


def test_reproduce_stage_is_a_deliberate_stub():
    with pytest.raises(NotImplementedError):
        reproduce_stage(_dummy_extraction(), data_dir=None)


def test_verify_stage_is_a_deliberate_stub():
    with pytest.raises(NotImplementedError):
        verify_stage(_dummy_reproduce_result(), _dummy_extraction())


def test_sample_stage_is_a_deliberate_stub():
    with pytest.raises(NotImplementedError):
        sample_stage(_dummy_reproduce_result(), data_dir=None)


def test_result_dataclasses_construct_with_stated_fields():
    # Not testing behavior (there isn't any yet) -- just that the I/O
    # contract types exist and hold the fields described in interface.py.
    VerifyResult(comparable=False, skip_reason="no period overlap")
    SampleResult(
        paper_slug="paper-00-dummy",
        period_start="2016-01-01",
        period_end="2026-01-01",
        returns=None,
    )
