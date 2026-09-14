"""
Read stage automation.

This turns a paper's extracted text into a structured extraction via a
PROGRAMMATIC Claude API call -- no live conversation required. This is
the actual automation the owner asked for on 2026-09-14: everything before
this was a human (Claude Code, in chat) reading PDFs and writing notes by
hand, which is functionally identical to pasting a paper into a chat and
asking for a summary. This script is a callable, reusable artifact --
point it at a new paper folder and it runs, no live conversation needed.

Human review is still expected on the output -- this produces a first-pass
draft, not a verified read. Per CLAUDE.md: "Read aşaması ... ilk denemede
tam doğru çıkmayabilir, bu normal." Compare the output against a manual
read before trusting it for a new paper; it was validated against the
already-manually-read papers #1 and #2 (see STATUS.md).

Usage:
    .venv\\Scripts\\python.exe -m pipeline.read_stage papers/paper-02-groot-huij-zhou-2012

Requires ANTHROPIC_API_KEY in .env -- separate from any Claude Code
session credential; this script calls the API directly and on its own,
so it needs its own key. Costs real money per call (Claude Opus 5:
$5/$25 per MTok input/output) -- a ~40-page paper's extracted text is
roughly 15-20K input tokens, so each run costs on the order of
$0.10-0.30. Not free the way the conversational reading was.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv
from pypdf import PdfReader

load_dotenv()

MODEL = "claude-opus-5"

# Kept intentionally in the JSON Schema structured-outputs subset: basic
# types (incl. null via a type array), enum/object/array, and
# additionalProperties: false on every object. No minLength/minimum/regex
# constraints, no recursive $ref -- those aren't supported.
EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "authors": {"type": "array", "items": {"type": "string"}},
        "venue": {
            "type": ["string", "null"],
            "description": "Journal/working paper venue, e.g. 'Journal of Banking & Finance 36 (2012)'",
        },
        "year": {"type": ["integer", "null"]},
        "data_sample": {
            "type": "string",
            "description": "Data source, sample period, and universe filters -- as specific as the paper states, not a generic description",
        },
        "signals": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "definition": {
                        "type": "string",
                        "description": "The exact formula/rule in words, not just a label",
                    },
                    "formation_period": {"type": "string"},
                },
                "required": ["name", "definition", "formation_period"],
                "additionalProperties": False,
            },
        },
        "portfolio_construction": {
            "type": "string",
            "description": "Long/short rule, weighting scheme, rebalancing frequency, and any non-obvious construction details (entry/exit rules, holding period, skip days, etc.)",
        },
        "key_results": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "label": {
                        "type": "string",
                        "description": "Which subset/variant/universe this result row is for",
                    },
                    "metric": {"type": "string"},
                    "value": {"type": "string"},
                    "significance": {"type": ["string", "null"]},
                },
                "required": ["label", "metric", "value", "significance"],
                "additionalProperties": False,
            },
        },
        "central_claim": {"type": "string"},
        "testability_notes": {
            "type": "string",
            "description": (
                "Given daily/monthly US equity data from 2016 onward, no "
                "options data, no point-in-time fundamentals, no tick data "
                "-- what parts of THIS paper's specific design are and are "
                "not testable? Be concrete about what's missing, not generic."
            ),
        },
        "open_questions": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Ambiguities or underspecified details a reproduction would have to guess at -- do not silently resolve these, list them",
        },
    },
    "required": [
        "title",
        "authors",
        "venue",
        "year",
        "data_sample",
        "signals",
        "portfolio_construction",
        "key_results",
        "central_claim",
        "testability_notes",
        "open_questions",
    ],
    "additionalProperties": False,
}

EXTRACTION_PROMPT = """You are doing the "Read" stage of a quant-paper reproduction pipeline: extracting exactly what a paper says, not summarizing loosely.

Rules:
- Quote or precisely paraphrase the paper's ACTUAL stated methodology -- not a generic description of "a typical study like this."
- For key_results, transcribe REAL numbers from tables/text. Never estimate, round, or infer a number that isn't stated somewhere in the text.
- If something is ambiguous or underspecified in the paper, say so in open_questions -- do not silently fill the gap with your own assumption anywhere else in the output.
- testability_notes must be specific to what's actually in THIS paper (its actual signals, its actual universe) evaluated against the stated data constraint -- not generic boilerplate about data limitations in general.

Paper text follows:

---
{paper_text}
---
"""


def extract_text(paper_dir: Path) -> str:
    """Reuse extracted_text.txt if present (pattern used throughout this
    repo -- see CLAUDE.md's PDF handling note), else generate it from
    source.pdf via pypdf (poppler/pdftoppm isn't installed locally, so
    the Read tool's native PDF rendering isn't an option here either)."""
    txt_path = paper_dir / "extracted_text.txt"
    if txt_path.exists():
        return txt_path.read_text(encoding="utf-8")

    pdf_path = paper_dir / "source.pdf"
    if not pdf_path.exists():
        raise FileNotFoundError(
            f"Neither extracted_text.txt nor source.pdf found in {paper_dir}"
        )

    reader = PdfReader(str(pdf_path))
    pages = [
        f"--- PAGE {i + 1} ---\n{p.extract_text() or ''}"
        for i, p in enumerate(reader.pages)
    ]
    text = "\n\n".join(pages)
    txt_path.write_text(text, encoding="utf-8")
    return text


def run_read_stage(paper_dir: Path) -> dict:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print(
            "Missing ANTHROPIC_API_KEY in .env -- this script calls the "
            "Claude API directly (separate from any Claude Code session "
            "credential) and needs its own key. Get one at "
            "console.anthropic.com and add it to .env.",
            file=sys.stderr,
        )
        sys.exit(1)

    paper_text = extract_text(paper_dir)
    client = Anthropic(api_key=api_key)

    response = client.messages.create(
        model=MODEL,
        max_tokens=8000,
        output_config={
            "format": {"type": "json_schema", "schema": EXTRACTION_SCHEMA}
        },
        messages=[
            {
                "role": "user",
                "content": EXTRACTION_PROMPT.format(paper_text=paper_text),
            }
        ],
    )

    if response.stop_reason == "refusal":
        print(
            f"Claude declined this request (stop_reason=refusal, "
            f"category={getattr(response.stop_details, 'category', None)}).",
            file=sys.stderr,
        )
        sys.exit(1)
    if response.stop_reason == "max_tokens":
        print(
            "WARNING: response hit max_tokens -- extraction JSON may be "
            "truncated/invalid. Consider raising max_tokens.",
            file=sys.stderr,
        )

    text_block = next(b for b in response.content if b.type == "text")
    data = json.loads(text_block.text)

    out_json = paper_dir / "read_extraction_auto.json"
    out_json.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    out_md = paper_dir / "read_stage_auto.md"
    out_md.write_text(_render_markdown(data), encoding="utf-8")

    print(f"Wrote {out_json}")
    print(f"Wrote {out_md}")
    print(
        f"Usage: {response.usage.input_tokens} input / "
        f"{response.usage.output_tokens} output tokens"
    )
    return data


def _render_markdown(data: dict) -> str:
    lines = [
        f"# Read stage (automated, first pass): {data['title']}",
        "",
        "**Machine-generated by `pipeline/read_stage.py` -- not yet "
        "human-reviewed.** Treat as a draft; verify against the source "
        "PDF before relying on it for Reproduce, per CLAUDE.md's rigor "
        "principle.",
        "",
        f"**Authors:** {', '.join(data['authors'])}",
        f"**Venue:** {data.get('venue') or 'n/a'} ({data.get('year') or 'n/a'})",
        "",
        "## Central claim",
        data["central_claim"],
        "",
        "## Data & sample",
        data["data_sample"],
        "",
        "## Signals",
    ]
    for s in data["signals"]:
        lines.append(
            f"- **{s['name']}**: {s['definition']} (formation: {s['formation_period']})"
        )
    lines += [
        "",
        "## Portfolio construction",
        data["portfolio_construction"],
        "",
        "## Key results",
        "",
        "| Label | Metric | Value | Significance |",
        "|---|---|---|---|",
    ]
    for r in data["key_results"]:
        lines.append(
            f"| {r['label']} | {r['metric']} | {r['value']} | {r.get('significance') or ''} |"
        )
    lines += [
        "",
        "## Testability against our data (Alpaca, 2016+ US equities)",
        data["testability_notes"],
        "",
        "## Open questions / ambiguities",
    ]
    for q in data["open_questions"]:
        lines.append(f"- {q}")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python -m pipeline.read_stage <paper_dir>", file=sys.stderr)
        sys.exit(1)
    run_read_stage(Path(sys.argv[1]))
