#!/usr/bin/env python3
"""summarize_batch.py — v3.8 finalize Phase 5 helper.

Reads specs/_epic/contracts.jsonl + specs/_epic/_evals/S{NN}-R{N}.json
and emits a single EPIC_SUMMARY.md suitable for archival under
specs/epics/<slug>/EPIC_SUMMARY.md.

Outputs one table per sprint (id, name, rounds, final-verdict, headline)
plus an overall summary line (sprints completed, total rounds).

Per-sprint state is derived deterministically:
  - sprint id + name + smoke come from spec.md (single source of truth)
  - phase (completed/agreed/...) comes from the LATEST contracts.jsonl
    entry for that sprint (by timestamp then file order)
  - verdict + headline come from the highest-numbered _evals/S{NN}-R{N}.json

Refuses to invent: if a sprint has no _evals entry, the table shows
"—" for round/verdict/headline rather than guessing.

Usage:
  summarize_batch.py --out <path>
                     [--epic-dir specs/_epic]

Exit:
  0 OK
  1 IO error
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

EVAL_FN_RE = re.compile(r"^(S\d{2})-R(\d+)\.json$")


@dataclass
class SprintRow:
    sid: str
    name: str
    smoke: str
    phase: str | None
    rounds_total: int
    final_verdict: str
    final_headline: str


def parse_spec_sprints(spec_path: Path) -> "OrderedDict[str, tuple[str, str]]":
    """Return {sid: (name, smoke)} in spec order."""
    text = spec_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    sprints: OrderedDict[str, tuple[str, str]] = OrderedDict()
    in_plan = False
    current_id: str | None = None
    current_name: str = ""
    current_smoke: str = ""
    for line in lines:
        if re.match(r"^##\s+Sprint plan\s*$", line):
            in_plan = True
            continue
        if in_plan and re.match(r"^##\s+\S", line):
            if current_id is not None:
                sprints[current_id] = (current_name, current_smoke)
                current_id = None
            in_plan = False
            continue
        if not in_plan:
            continue
        m = re.match(r"^###\s+(S\d{2})\s+—\s+(.+?)\s*$", line)
        if m:
            if current_id is not None:
                sprints[current_id] = (current_name, current_smoke)
            current_id = m.group(1)
            current_name = m.group(2).strip()
            current_smoke = ""
            continue
        sm = re.match(r"^-\s*Smoke\s*check\s*:\s*(.+?)\s*$", line, re.IGNORECASE)
        if sm and current_id is not None:
            current_smoke = sm.group(1).strip()
    if current_id is not None and in_plan:
        sprints[current_id] = (current_name, current_smoke)
    return sprints


def latest_phase_per_sprint(
    contracts_path: Path, sprint_ids: set[str]
) -> dict[str, str]:
    """Walk contracts.jsonl; return {sid: latest_phase}."""
    if not contracts_path.exists():
        return {}
    per_sprint: dict[str, dict[str, Any]] = {}
    with contracts_path.open(encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                print(
                    f"summarize_batch: malformed JSON in contracts.jsonl line {line_no}",
                    file=sys.stderr,
                )
                continue
            sid = entry.get("sprint")
            if not sid or sid not in sprint_ids:
                continue
            existing = per_sprint.get(sid)
            if existing is None or entry.get("timestamp", "") >= existing.get(
                "timestamp", ""
            ):
                per_sprint[sid] = entry
    return {sid: e.get("phase", "") for sid, e in per_sprint.items()}


def latest_eval(evals_dir: Path, sid: str) -> tuple[int, str, str]:
    """Return (max_round, verdict, headline). 0/empty if none."""
    if not evals_dir.is_dir():
        return 0, "", ""
    rounds: list[tuple[int, Path]] = []
    for p in evals_dir.glob(f"{sid}-R*.json"):
        m = EVAL_FN_RE.match(p.name)
        if m:
            rounds.append((int(m.group(2)), p))
    if not rounds:
        return 0, "", ""
    max_round, max_path = max(rounds, key=lambda x: x[0])
    try:
        data = json.loads(max_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return max_round, "", ""
    verdict = str(data.get("verdict", ""))
    headline = (
        str(data.get("eval_feedback", {}).get("overall", ""))
        or str(data.get("summary", ""))
    )
    headline = headline.replace("\n", " ").replace("\t", " ").strip()
    if len(headline) > 80:
        headline = headline[:79].rstrip() + "…"
    return max_round, verdict, headline


def build_rows(
    sprints: "OrderedDict[str, tuple[str, str]]",
    phases: dict[str, str],
    evals_dir: Path,
) -> list[SprintRow]:
    rows: list[SprintRow] = []
    for sid, (name, smoke) in sprints.items():
        rounds_total, verdict, headline = latest_eval(evals_dir, sid)
        rows.append(SprintRow(
            sid=sid,
            name=name,
            smoke=smoke,
            phase=phases.get(sid),
            rounds_total=rounds_total,
            final_verdict=verdict,
            final_headline=headline,
        ))
    return rows


def extract_epic_slug(spec_path: Path) -> str:
    text = spec_path.read_text(encoding="utf-8")
    m = re.search(r"^#\s+Spec\s+—\s+(.+?)\s*$", text, re.MULTILINE)
    return m.group(1).strip() if m else "(unknown)"


def render(rows: list[SprintRow], slug: str) -> str:
    today = dt.date.today().isoformat()
    completed = sum(1 for r in rows if r.phase == "completed")
    total_rounds = sum(r.rounds_total for r in rows)

    out: list[str] = [
        f"# Epic Summary — {slug}",
        "",
        f"Completed: {today}",
        f"Sprints: {len(rows)} planned, {completed} completed",
        f"Total evaluator rounds across all sprints: {total_rounds}",
        "",
        "## Sprint outcomes",
        "",
        "| Sprint | Name | Phase | Last round | Verdict | Headline |",
        "|---|---|---|---|---|---|",
    ]
    for r in rows:
        out.append(
            f"| {r.sid} | {r.name} | "
            f"{r.phase or '—'} | "
            f"{f'R{r.rounds_total}' if r.rounds_total else '—'} | "
            f"{r.final_verdict or '—'} | "
            f"{r.final_headline or '_(no eval JSON)_'} |"
        )
    out.append("")
    out.append(
        "_Per-round evaluator JSONs preserved under `_evals/`; per-round "
        "subagent transcripts under `_traces/`; full contract lifecycle "
        "in `contracts.jsonl`._"
    )
    out.append("")
    return "\n".join(out)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True)
    ap.add_argument("--epic-dir", default="specs/_epic")
    args = ap.parse_args(argv)

    epic_dir = Path(args.epic_dir)
    spec_path = epic_dir / "spec.md"
    contracts_path = epic_dir / "contracts.jsonl"
    evals_dir = epic_dir / "_evals"
    out_path = Path(args.out)

    if not spec_path.exists():
        print(f"ERROR: {spec_path} not found", file=sys.stderr)
        return 1

    slug = extract_epic_slug(spec_path)
    sprints = parse_spec_sprints(spec_path)
    if not sprints:
        print(
            f"ERROR: no sprints parsed from {spec_path} — empty Sprint plan?",
            file=sys.stderr,
        )
        return 1
    phases = latest_phase_per_sprint(contracts_path, set(sprints.keys()))
    rows = build_rows(sprints, phases, evals_dir)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(render(rows, slug), encoding="utf-8")
    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
