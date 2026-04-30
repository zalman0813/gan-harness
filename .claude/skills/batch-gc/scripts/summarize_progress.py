#!/usr/bin/env python3
"""Summarize docs/progress/F*-*.md into BATCH_SUMMARY.md.

Usage:
    python3 summarize_progress.py --out <path/to/BATCH_SUMMARY.md>
    [--feature-list <path>]  (default docs/feature-list.json)
    [--progress-dir <path>]  (default docs/progress)

Reads docs/feature-list.json for terminal state + per-feature round
numbers, then extracts a one-line headline from each feature's
progress file (F{NN}-progress-R{round}.md if present, else the
highest-round file).

Headline extraction order:
  1. Text under `## Outcome` heading, first non-empty line
  2. Text under `## Summary` heading, first non-empty line
  3. First non-empty paragraph of the file (trimmed to 80 chars)

Writes a markdown summary (see below). Does NOT delete anything.
Archive script handles deletion after this runs.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

HEADLINE_HEADINGS = ("Outcome", "Summary")
PROGRESS_FN_RE = re.compile(r"F(\d+)-progress-R(\d+)\.md$")
EVAL_FN_RE = re.compile(r"F(\d+)-eval-R(\d+)\.md$")


def _is_prose(line: str) -> bool:
    """Heuristic: line looks like human-readable prose (not markup)."""
    s = line.strip()
    if not s:
        return False
    if s.startswith("#"):
        return False      # heading
    if s.startswith("```") or s.startswith("~~~"):
        return False      # code fence delimiter
    if s.startswith("|"):
        return False      # markdown table row
    if s.startswith("-") or s.startswith("*") or s.startswith("+"):
        return False      # bullet list
    if s.startswith(">"):
        return False      # blockquote
    return True


def extract_headline(path: Path) -> str:
    """Extract ≤80-char one-liner from a progress/eval markdown file."""
    if not path.exists():
        return "(no progress file found)"
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    # Pass 1: prioritize headings.
    for heading in HEADLINE_HEADINGS:
        for i, line in enumerate(lines):
            if line.strip().startswith(f"## {heading}"):
                for body_line in lines[i + 1:]:
                    if _is_prose(body_line):
                        return trim(body_line.strip(), 80)
                break

    # Pass 2: first prose paragraph after any front-matter / H1 / metadata.
    in_front = False
    for line in lines:
        if line.strip().startswith("---"):
            in_front = not in_front
            continue
        if in_front:
            continue
        if _is_prose(line):
            return trim(line.strip(), 80)

    return "(no headline available)"


def trim(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def find_progress_file(progress_dir: Path, fid: str, round_no: int | None) -> Path:
    """Find the best progress file for feature `fid`.

    Prefers the specific round if given; falls back to the highest round
    present.
    """
    candidates = sorted(progress_dir.glob(f"{fid}-progress-R*.md"))
    if not candidates:
        return Path("/dev/null")  # Will trigger "(no progress file found)"
    if round_no is not None:
        exact = progress_dir / f"{fid}-progress-R{round_no}.md"
        if exact.exists():
            return exact
    # Fallback: highest R number
    return max(candidates, key=lambda p: int(PROGRESS_FN_RE.search(p.name).group(2)))


def infer_round(progress_dir: Path, fid: str) -> int | None:
    """Infer the terminal round number for fid by scanning progress files."""
    rounds = []
    for p in progress_dir.glob(f"{fid}-progress-R*.md"):
        m = PROGRESS_FN_RE.search(p.name)
        if m:
            rounds.append(int(m.group(2)))
    return max(rounds) if rounds else None


def has_infra_blocked(progress_dir: Path, fid: str) -> bool:
    """Check eval files for `infraBlocked: true` flag."""
    for p in progress_dir.glob(f"{fid}-eval-R*.md"):
        if "infraBlocked: true" in p.read_text(encoding="utf-8"):
            return True
        if "infraBlocked = true" in p.read_text(encoding="utf-8"):
            return True
    return False


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True, help="output path for BATCH_SUMMARY.md")
    parser.add_argument("--feature-list", default="docs/feature-list.json")
    parser.add_argument("--progress-dir", default="docs/progress")
    parser.add_argument(
        "--slug",
        default=None,
        help="Authoritative slug (e.g. parsed via preflight.py --print-slug). "
             "When omitted, falls back to a best-effort parse of meta.source.",
    )
    args = parser.parse_args(argv)

    feature_list = Path(args.feature_list)
    progress_dir = Path(args.progress_dir)
    out_path = Path(args.out)

    try:
        data = json.loads(feature_list.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"ERROR: {feature_list} not found", file=sys.stderr)
        return 1

    if args.slug:
        slug = args.slug
    else:
        slug = (
            data.get("meta", {}).get("source", "unknown")
            .split("/")[-1]
            .replace(".md", "")
            .replace("_requirement", "")
            .replace("_", "-")
        )
    base_commit = data.get("meta", {}).get("baseCommit", "unknown")
    features = data.get("features", [])
    done = [f for f in features if f["status"] == "DONE"]
    blocked = [f for f in features if f["status"] == "BLOCKED"]

    today = dt.date.today().isoformat()

    rows = []
    for feat in features:
        fid = feat["id"]
        state = feat["status"]
        round_no = infer_round(progress_dir, fid)
        progress_path = find_progress_file(progress_dir, fid, round_no)
        headline = extract_headline(progress_path)
        if has_infra_blocked(progress_dir, fid):
            headline = f"{headline} (infraBlocked)"
        round_str = f"R{round_no}" if round_no else "—"
        rows.append(f"| {fid} | {state} | {round_str} | {headline} |")

    out = [
        f"# Batch Summary — {slug}",
        "",
        f"Base commit: `{base_commit}`",
        f"Completed: {today}",
        f"Features: {len(done)}/{len(features)} DONE, {len(blocked)} BLOCKED",
        "",
        "## Feature Outcomes",
        "",
        "| Feature | State | Round | Headline |",
        "|---|---|---|---|",
        *rows,
        "",
        "## Notes",
        "",
        "- Proposals applied: see DREAM-gen.md and DREAM-eval.md `## Applied` sections for the full audit trail.",
        "",
    ]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(out), encoding="utf-8")
    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
