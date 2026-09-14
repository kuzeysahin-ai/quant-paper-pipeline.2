# pipeline/

Shared, reusable pipeline code -- as opposed to `papers/paper-0N-*/`, which
holds paper-specific content and paper-specific Reproduce code (per
CLAUDE.md's "don't generalize before 3+ papers" guidance for *strategy*
code).

**Read-stage automation is different from strategy code and doesn't wait
for 3+ papers** -- it's not a trading strategy, it's "extract structured
info from an academic paper PDF," which is the same operation for every
paper from day one. Built 2026-09-14 after the owner correctly pointed
out that everything up to that point (Claude Code reading PDFs and
writing notes in conversation) was not meaningfully different from
pasting a paper into a chat and asking for a summary -- there was no code
performing the Read stage, just a human (Claude Code) doing it live.

## `read_stage.py`

Takes a paper folder, extracts PDF text (reusing `extracted_text.txt` if
already present), calls the Claude API (`claude-opus-5`, structured JSON
output) with an extraction schema, and writes:

- `read_extraction_auto.json` -- structured data
- `read_stage_auto.md` -- human-readable version

```bash
.venv\Scripts\python.exe -m pipeline.read_stage papers/paper-0N-slug
```

Requires `ANTHROPIC_API_KEY` in `.env` (separate credential from any
Claude Code session -- see `.env.example`). Real cost per run, not free:
~$0.10-0.30 per paper at Claude Opus 5 rates for a ~40-page PDF.

**Not yet validated against a real API call** (needs the owner's API
key) -- next step is running it on paper #2 and diffing the output
against the manually-written `papers/paper-02-groot-huij-zhou-2012/read_notes.md`
to check whether the automated first pass is actually trustworthy.

**Still requires human review of the output** -- this is a first-pass
draft generator, not a fully autonomous, unsupervised Read stage. Per
CLAUDE.md: extraction "won't be fully correct on the first attempt;
that's normal, not a failure."

## `interface.py`

The fixed four-stage contract: `read_stage`, `reproduce_stage`,
`verify_stage`, `sample_stage` -- names, input/output dataclasses, and
one-line responsibilities, in one place. Built 2026-09-14 **before**
writing any specific paper's Reproduce/Verify/Sample logic, on purpose:
every paper from here on is a module written against this contract, not
something that needs re-explaining from scratch.

- `read_stage` delegates to `read_stage.py` (real, calls the Claude API).
  Reuses `read_extraction_auto.json` if present instead of re-calling the
  API every run (`force=True` to override).
- `reproduce_stage` / `verify_stage` / `sample_stage` **dispatch** to
  `papers/<paper_slug>/reproduce/stage_impl.py` -- loaded dynamically via
  `importlib` (paper directory names have hyphens, invalid in a dotted
  Python import). A paper implements the contract by providing that file
  with matching function signatures. Dispatching to a paper without one
  raises `FileNotFoundError` naming exactly what's missing -- loud
  failure, not a silent no-op or fake result.
- Paper #1 (Stosik & Zaremba) is the first, and so far only, real
  implementation -- see `papers/paper-01-ssrn-6630998/reproduce/`.
  Paper #2's `reproduce/strategy.py` predates the interface and has no
  `stage_impl.py`; dispatching to it fails loudly until/unless that gets
  built.
- `pipeline/test_interface.py` proves the dispatch actually reaches
  paper #1's real code (not stubs) end to end, against synthetic data.

## `run.py` -- the orchestrator

Runs all four stages in sequence for one paper, via one command:

```bash
.venv\Scripts\python.exe -m pipeline.run papers/paper-01-ssrn-6630998
```

This is the piece that makes the interface an actual pipeline rather
than four functions nobody calls in order. `pipeline/test_run.py`
exercises it end to end (Read monkeypatched to skip the real API call;
Reproduce/Verify/Sample run for real through the dispatch mechanism
above, against synthetic data).
