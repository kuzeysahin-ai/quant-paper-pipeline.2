"""
The orchestrator: runs Read -> Reproduce -> Verify -> Sample for one
paper, in sequence, via a single command. This is what makes the four
stages an actual pipeline instead of four functions nobody calls in
order -- without this, wiring real data into reproduce_stage still
wouldn't be "automation," just a connected set of parts nobody runs
end to end.

Usage:
    .venv\\Scripts\\python.exe -m pipeline.run papers/paper-01-ssrn-6630998
    .venv\\Scripts\\python.exe -m pipeline.run papers/paper-01-ssrn-6630998 --data-dir papers/paper-01-ssrn-6630998/data
    .venv\\Scripts\\python.exe -m pipeline.run papers/paper-01-ssrn-6630998 --force-read

Requires:
  - ANTHROPIC_API_KEY in .env for the Read stage (skipped if
    read_extraction_auto.json already exists -- see interface.read_stage;
    pass --force-read to re-run it anyway).
  - papers/<paper>/reproduce/stage_impl.py implementing reproduce_stage/
    verify_stage/sample_stage (see pipeline/interface.py). Papers that
    don't have this yet (e.g. paper #2, as of 2026-09-14) will fail at
    the Reproduce step with a clear FileNotFoundError, not silently.
  - data_dir/returns.csv + data_dir/market_cap.csv for Reproduce/Sample
    (paper #1's exact contract; see that paper's stage_impl.py
    docstring). Nothing in this repo produces these from Alpaca/SEC yet
    -- see STATUS.md. Runs against real data will fail at the Reproduce
    step until that's built; this orchestrator doesn't paper over that.
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

from pipeline.interface import (
    ReadExtraction,
    ReproduceResult,
    SampleResult,
    VerifyResult,
    read_stage,
    reproduce_stage,
    sample_stage,
    verify_stage,
)


@dataclass
class PipelineRunResult:
    extraction: ReadExtraction
    reproduce: ReproduceResult
    verify: VerifyResult
    sample: SampleResult


def run_pipeline(
    paper_dir: Path, data_dir: Path | None = None, force_read: bool = False
) -> PipelineRunResult:
    data_dir = data_dir or (paper_dir / "data")
    slug = paper_dir.name

    print(f"=== [{slug}] Read ===")
    extraction = read_stage(paper_dir, force=force_read)
    print(f"  {extraction.title}")
    if extraction.open_questions:
        print(f"  {len(extraction.open_questions)} open question(s) flagged by Read")

    print(f"=== [{slug}] Reproduce ===")
    reproduce_result = reproduce_stage(extraction, data_dir, paper_dir)
    print(f"  {reproduce_result.notes}")
    for assumption in reproduce_result.assumptions:
        print(f"  assumption: {assumption}")

    print(f"=== [{slug}] Verify ===")
    verify_result = verify_stage(reproduce_result, extraction)
    if verify_result.comparable:
        tol_str = "within tolerance" if verify_result.within_tolerance else "OUTSIDE tolerance"
        print(
            f"  our={verify_result.our_value:.3f} "
            f"paper={verify_result.paper_value:.3f} ({tol_str})"
        )
    else:
        print(f"  skipped (not comparable): {verify_result.skip_reason}")

    print(f"=== [{slug}] Sample ===")
    sample_result = sample_stage(reproduce_result, data_dir)
    print(f"  {sample_result.period_start} to {sample_result.period_end}")
    print(f"  {sample_result.summary_stats}")

    return PipelineRunResult(
        extraction=extraction,
        reproduce=reproduce_result,
        verify=verify_result,
        sample=sample_result,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the full Read -> Reproduce -> Verify -> Sample pipeline for one paper."
    )
    parser.add_argument(
        "paper_dir", type=Path, help="e.g. papers/paper-01-ssrn-6630998"
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=None,
        help="Defaults to <paper_dir>/data",
    )
    parser.add_argument(
        "--force-read",
        action="store_true",
        help="Re-run the Read stage (calls the Claude API again, real cost) even if read_extraction_auto.json already exists",
    )
    args = parser.parse_args()

    if not args.paper_dir.exists():
        print(f"paper_dir not found: {args.paper_dir}", file=sys.stderr)
        sys.exit(1)

    try:
        run_pipeline(args.paper_dir, args.data_dir, force_read=args.force_read)
    except FileNotFoundError as e:
        # Reproduce/Sample raise this when either the paper hasn't
        # implemented stage_impl.py, or data_dir is missing its expected
        # files -- both are real, expected failure modes at this point
        # in the project (see this module's docstring), not bugs in the
        # orchestrator. Surface plainly rather than a raw traceback.
        print(f"\nPipeline stopped: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
