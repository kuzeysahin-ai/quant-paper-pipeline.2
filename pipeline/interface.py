"""
The fixed four-stage pipeline contract: Read -> Reproduce -> Verify -> Sample.

Built 2026-09-14 as a skeleton, before any paper's Reproduce/Verify/Sample
logic existed. As of the same day, all four stages now DISPATCH to real
per-paper implementations -- this module doesn't contain strategy logic
itself, it routes to it, the same way read_stage always delegated to
pipeline/read_stage.py. A paper implements the contract by providing
papers/<paper_slug>/reproduce/stage_impl.py with matching function
signatures (see papers/paper-01-ssrn-6630998/reproduce/stage_impl.py as
the reference). Calling any stage for a paper that hasn't implemented
stage_impl.py fails loudly with FileNotFoundError naming exactly what's
missing -- not a silent no-op.

pipeline/run.py is the orchestrator that calls all four stages in
sequence for one paper -- see that file to actually run the pipeline
end to end, rather than calling these functions one at a time by hand.

Why this is an exception to "don't generalize before 3+ papers": that
CLAUDE.md guidance is about STRATEGY code (how a specific paper's signal
and portfolio construction works) -- it does not apply to the pipeline
shape itself, which is identical for every paper from day one. See
pipeline/README.md.

Note: papers/paper-02-groot-huij-zhou-2012/reproduce/strategy.py
(SmartReversalSimulator) predates this interface and does not implement
stage_impl.py -- dispatching to that paper_slug will raise
FileNotFoundError until/unless it's adapted. Paper #1 (Stosik & Zaremba)
is the first, and so far only, real implementation.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parent.parent
_PAPERS_DIR = _REPO_ROOT / "papers"


# ---------------------------------------------------------------------
# Dispatch: load a paper's reproduce/stage_impl.py by paper_dir/paper_slug.
#
# Uses importlib.util (not a dotted `import papers.x.reproduce.stage_impl`)
# because paper directory names contain hyphens, which aren't valid in
# Python package/module names.
#
# KNOWN LIMITATION: stage_impl.py files import their sibling modules
# (e.g. industry_classification, portfolio, reversal_signal) by bare
# name, which only resolves if that paper's reproduce/ directory is on
# sys.path -- this function adds it. If a second paper implements this
# interface with a same-named sibling module (e.g. another paper also
# has a portfolio.py with different contents), Python's sys.modules
# caching means whichever loads first in a process wins that bare name,
# process-wide. Not a problem with only paper #1 implemented; revisit
# (e.g. per-paper module aliasing) if and when a second paper does.
# ---------------------------------------------------------------------


def _load_paper_stage_impl(paper_dir: Path):
    module_path = paper_dir / "reproduce" / "stage_impl.py"
    if not module_path.exists():
        raise FileNotFoundError(
            f"No reproduce/stage_impl.py for paper {paper_dir.name!r} "
            f"(looked at {module_path}). Every paper implementing the "
            f"pipeline interface needs this file -- see "
            f"papers/paper-01-ssrn-6630998/reproduce/stage_impl.py as "
            f"the reference implementation."
        )

    module_name = f"_paper_stage_impl__{paper_dir.name.replace('-', '_')}"
    if module_name in sys.modules:
        return sys.modules[module_name]

    reproduce_dir_str = str(module_path.parent)
    if reproduce_dir_str not in sys.path:
        sys.path.insert(0, reproduce_dir_str)

    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------
# Stage 1: Read
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


def read_stage(paper_dir: Path, force: bool = False) -> ReadExtraction:
    """
    Extract structured methodology + results from a paper's PDF.

    Delegates to pipeline.read_stage.run_read_stage -- see that module
    for the actual Claude API call and schema.

    Reuses paper_dir/read_extraction_auto.json when present and
    force=False, instead of calling the API again: read_stage.py's Claude
    API call costs real money per run (see its docstring), and
    pipeline/run.py is expected to be re-invoked often while iterating on
    Reproduce/data wiring -- re-extracting every single run would be
    pointless spend for a document that hasn't changed.
    """
    cache_path = paper_dir / "read_extraction_auto.json"
    if cache_path.exists() and not force:
        data = json.loads(cache_path.read_text(encoding="utf-8"))
        return ReadExtraction(**data)

    from pipeline.read_stage import run_read_stage

    data = run_read_stage(paper_dir)
    return ReadExtraction(**data)


# ---------------------------------------------------------------------
# Stage 2: Reproduce
# ---------------------------------------------------------------------


@dataclass
class ReproduceResult:
    """Output of building a paper's strategy mechanism from its Read
    extraction and running it against market data."""

    paper_slug: str  # matches the papers/paper-0N-* folder name
    returns: Any  # pandas.Series/DataFrame of period returns -- loosely
    # typed here so this interface module doesn't require pandas as a
    # hard import; real implementations use it.
    positions: Any | None = None  # optional: per-period holdings, for diagnostics
    assumptions: list[str] = field(
        default_factory=list
    )  # design decisions NOT explicit in the paper -- document, don't
    # silently assume (see CLAUDE.md's rigor principle).
    notes: str = ""


def reproduce_stage(
    extraction: ReadExtraction, data_dir: Path, paper_dir: Path
) -> ReproduceResult:
    """
    Build the paper's strategy mechanism (signal + portfolio
    construction) from its Read-stage extraction, and run it against
    market data found in `data_dir`.

    Dispatches to papers/<paper_dir.name>/reproduce/stage_impl.py's
    reproduce_stage -- that file's docstring documents its own data_dir
    contract (which varies per paper: what files it expects, what shape).
    """
    module = _load_paper_stage_impl(paper_dir)
    return module.reproduce_stage(extraction, data_dir)


# ---------------------------------------------------------------------
# Stage 3: Verify
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

    Dispatches by reproduce_result.paper_slug (no separate paper_dir
    argument needed -- Reproduce already fixed which paper this is).

    Per CLAUDE.md: expect most papers NOT to replicate at their published
    effect size (Hou/Xue/Zhang: ~65% of 452 published anomalies lose
    significance under tighter tests) -- a failed or skipped Verify is a
    real finding, not a bug to fix.
    """
    paper_dir = _PAPERS_DIR / reproduce_result.paper_slug
    module = _load_paper_stage_impl(paper_dir)
    return module.verify_stage(reproduce_result, extraction)


# ---------------------------------------------------------------------
# Stage 4: Sample
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

    Dispatches by reproduce_result.paper_slug, same as verify_stage.
    """
    paper_dir = _PAPERS_DIR / reproduce_result.paper_slug
    module = _load_paper_stage_impl(paper_dir)
    return module.sample_stage(reproduce_result, data_dir)
