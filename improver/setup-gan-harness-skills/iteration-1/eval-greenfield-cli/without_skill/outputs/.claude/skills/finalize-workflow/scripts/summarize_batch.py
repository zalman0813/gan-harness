#!/usr/bin/env python3
"""Summarize a completed batch into BATCH_SUMMARY.md.

Reads two sources:
  1. specs/_batch/feature-list.json — terminal status per feature, batch_slug, base_commit
  2. specs/_batch/_evals/F{NN}-R{N}.json — per-round evaluator verdicts (verdict + eval_feedback.overall)

progress.tsv is NOT consulted: once every feature.status is terminal in
feature-list.json, the JSON has the same status plus richer detail.
Reading both risks drift.

Output: a flat markdown summary suitable for archival under
specs/completed/{slug}/BATCH_SUMMARY.md.

Usage:
  summarize_batch.py --out <path> [--feature-list specs/_batch/feature-list.json]
                                  [--evals-dir specs/_batch/_evals]

Exit:
  0 OK
  1 IO / parse error
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

EVAL_FN_RE = re.compile(r"^F(\d+)-R(\d+)\.json$")


def latest_eval(evals_dir: Path, fid: str) -> tuple[int | None, str, str]:
    """Return (max_round, verdict, overall_note) for feature `fid`. Empty
    strings if no eval files exist."""
    rounds: list[tuple[int, Path]] = []
    for p in evals_dir.glob(f"{fid}-R*.json"):
        m = EVAL_FN_RE.match(p.name)
        if m:
            rounds.append((int(m.group(2)), p))
    if not rounds:
        return None, "", ""

    max_round, max_path = max(rounds, key=lambda x: x[0])
    try:
        data = json.loads(max_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return max_round, "", ""

    verdict = str(data.get("verdict", ""))
    overall = str(data.get("eval_feedback", {}).get("overall", ""))
    overall = overall.replace("\n", " ").replace("\t", " ").strip()
    if len(overall) > 80:
        overall = overall[:79].rstrip() + "…"
    return max_round, verdict, overall


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--feature-list", default="specs/_batch/feature-list.json")
    ap.add_argument("--evals-dir", default="specs/_batch/_evals")
    args = ap.parse_args(argv)

    fl = Path(args.feature_list)
    evals_dir = Path(args.evals_dir)
    out_path = Path(args.out)

    try:
        data = json.loads(fl.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"ERROR: {fl} not found", file=sys.stderr)
        return 1
    except json.JSONDecodeError as exc:
        print(f"ERROR: {fl} is not valid JSON: {exc}", file=sys.stderr)
        return 1

    slug = data.get("batch_slug", "unknown")
    base_commit = data.get("base_commit", "unknown")
    features = data.get("features", [])
    today = dt.date.today().isoformat()

    by_status: dict[str, int] = {"passed": 0, "deferred": 0, "blocked-by-ancestor": 0}
    rows = []
    for feat in features:
        fid = feat.get("id", "?")
        status = feat.get("status", "?")
        by_status[status] = by_status.get(status, 0) + 1

        if evals_dir.is_dir():
            round_no, verdict, overall = latest_eval(evals_dir, fid)
        else:
            round_no, verdict, overall = None, "", ""
        round_str = f"R{round_no}" if round_no else "—"
        verdict_str = verdict or "—"
        headline = overall or "_(no eval JSON)_"
        rows.append(f"| {fid} | {status} | {round_str} | {verdict_str} | {headline} |")

    out = [
        f"# Batch Summary — {slug}",
        "",
        f"Base commit: `{base_commit}`",
        f"Completed: {today}",
        f"Features: {len(features)} total — "
        f"{by_status.get('passed', 0)} passed, "
        f"{by_status.get('deferred', 0)} deferred, "
        f"{by_status.get('blocked-by-ancestor', 0)} blocked-by-ancestor",
        "",
        "## Feature outcomes",
        "",
        "| Feature | Status | Last round | Verdict | Headline |",
        "|---|---|---|---|---|",
        *rows,
        "",
        "_Per-round evaluator JSONs preserved under `_evals/`; per-round traces under `_traces/`; full progress log in `progress.tsv`._",
        "",
    ]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(out), encoding="utf-8")
    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
