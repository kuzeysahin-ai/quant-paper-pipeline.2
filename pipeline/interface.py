"""
The fixed four-stage pipeline contract: Read -> Reproduce -> Verify -> Sample.

Built 2026-09-14, deliberately BEFORE writing any specific paper's
Reproduce/Verify/Sample logic. This is the interface, not the
implementation -- function names, input/output types, and one-line
responsibilities are fixed now so that every future paper is "a module
written against this contract," not something that has to be re-explained
from scratch each time.

Status of each stage as of this file's creation:
  - read_stage      REAL implementation, see pipeline/read_stage.py
  - reproduce_stage SKELETON ONLY -- raises NotImplementedError
  - verify_stage    SKELETON ONLY -- raises NotImplementedError
  - sample_stage    SKELETON ONLY -- raises NotImplementedError

Why this is an exception to "don't generalize before 3+ papers": that
CLAUDE.md guidance is about STRATEGY code (how a specific paper's signal
and portfolio construction works) -- it does not apply to the pipeline
shape itself, which is identical for every paper from day one. See
pipeline/README.md.

Note: papers/paper-02-groot-huij-zhou-2012/reproduce/strategy.py
(SmartReversalSimulator) predates this interface and does not conform to
it yet -- it was written before this skeleton existed. Leave it as-is for
now; adapt it to this contract if/when work on paper #2 resumes. The
paper chosen next (paper #1, Stosik & Zaremba) is the first one built
directly against this interface.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------
# Stage 1: Read
# Real implementation: pipeline/read_stage.py. Re-exported here only so
# its output type sits next to the other three stages' types in one
# place -- this module doesn't duplicate that logic.
# ---------------------------------------------------------------------


@dataclass
class ReadExtraction:
    """Structured output of the Read stage. Field names mirror
    read_stage.py's EXTRACTION_SCHEMA -- this dataclass is the typed
    contract the other three stages consume; read_stage.py's JSON output
    (read_extraction_auto.json) is loaded into this shape."""

    title: str
    authors: list[str]
    venue: str | None
    year: int | None
    data_sample: str
    signals: list[dict]  # [{name, definition, formation_period}, ...]
    portfolio_construction: str
    key_results: list[dict]  # [{label, metric, value, significance}, ...]
    central_claim: str
    testability_notes: str
    open_questions: list[str]


def read_stage(paper_dir: Path) -> ReadExtraction:
    """
    Extract structured methodology + results from a paper's PDF.

    REAL IMPLEMENTATION -- delegates to pipeline.read_stage.run_read_stage,
    then loads the result into a ReadExtraction. See that module for the
    actual Claude API call and schema.
    """
    from pipeline.read_stage import run_read_stage

    data = run_read_stage(paper_dir)
    return ReadExtraction(**data)


# ---------------------------------------------------------------------
# Stage 2: Reproduce -- SKELETON ONLY
# ---------------------------------------------------------------------


@dataclass
class ReproduceResult:
    """Output of building a paper's strategy mechanism from its Read
    extraction and running it against market data."""

    paper_slug: str  # matches the papers/paper-0N-* folder name
    returns: Any  # pandas.Series/DataFrame of period returns -- loosely
    # typed here so this interface module doesn't require pandas as a
    # hard import; the real implementation will use it.
    positions: Any | None = None  # optional: per-period holdings, for diagnostics
    assumptions: list[str] = field(
        default_factory=list
    )  # design decisions NOT explicit in the paper -- document, don't
    # silently assume (see CLAUDE.md's rigor principle). E.g. paper #2's
    # entry-skip-days interpretation, or paper #1's universe-membership
    # question, both belong here once that paper is reproduced.
    notes: str = ""


def reproduce_stage(extraction: ReadExtraction, data_dir: Path) -> ReproduceResult:
    """
    Build the paper's strategy mechanism (signal + portfolio
    construction) from its Read-stage extraction, and run it against
    market data found in `data_dir`.

    NOT IMPLEMENTED YET. Per-paper logic will live in
    papers/paper-0N-*/reproduce/ -- paper-specific for now, per CLAUDE.md
    ("don't generalize before 3+ papers"). This function is the fixed
    entry point that gets filled in when a paper is actually reproduced;
    exactly how a paper-specific module plugs into this signature
    (direct call, or a dispatch-by-paper_slug wrapper) is an open
    decision, deferred until there's a second real implementation to
    compare against the first.
    """
    raise NotImplementedError(
        "reproduce_stage: interface only, no implementation yet -- "
        "see papers/paper-0N-*/reproduce/ for in-progress per-paper work"
    )


# ---------------------------------------------------------------------
# Stage 3: Verify -- SKELETON ONLY
# ---------------------------------------------------------------------


@dataclass
class VerifyResult:
    """Comparison of a Reproduce-stage result against the paper's own
    published numbers, on the same sample period -- when that comparison
    is actually possible. `comparable=False` is a legitimate, expected
    outcome (not a failure): paper #2's sample ends in 2009, with zero
    overlap against Alpaca's 2016+ coverage, so no same-period comparison
    can ever be made for it. See that paper's read_notes.md."""

    comparable: bool
    skip_reason: str | None = None  # required explanation when comparable=False
    our_value: float | None = None
    paper_value: float | None = None
    within_tolerance: bool | None = None
    notes: str = ""


def verify_stage(
    reproduce_result: ReproduceResult, extraction: ReadExtraction
) -> VerifyResult:
    """
    Compare reproduce_result against the paper's own published numbers
    (extraction.key_results), on the same sample period, where possible.

    NOT IMPLEMENTED YET. Per CLAUDE.md: expect most papers NOT to
    replicate at their published effect size (Hou/Xue/Zhang: ~65% of
    452 published anomalies lose significance under tighter tests) -- a
    failed or skipped Verify is a real finding, not a bug to fix.
    """
    raise NotImplementedError("verify_stage: interface only, no implementation yet")


# ---------------------------------------------------------------------
# Stage 4: Sample -- SKELETON ONLY
# ---------------------------------------------------------------------


@dataclass
class SampleResult:
    """Result of running the reproduced strategy logic on CURRENT
    (2016+, via Alpaca) market data -- does the effect still show up
    today? Independent of whether Verify was possible at all."""

    paper_slug: str
    period_start: str
    period_end: str
    returns: Any  # pandas.Series/DataFrame, current-period returns
    summary_stats: dict = field(
        default_factory=dict
    )  # e.g. {"mean_monthly_return": ..., "sharpe": ...}
    notes: str = ""


def sample_stage(reproduce_result: ReproduceResult, data_dir: Path) -> SampleResult:
    """
    Re-run the reproduced strategy logic against current (2016+) market
    data via Alpaca and report whether the effect is still present.

    NOT IMPLEMENTED YET.
    """
    raise NotImplementedError("sample_stage: interface only, no implementation yet")
