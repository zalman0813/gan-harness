#!/usr/bin/env python3
"""epic_status.py — derive epic state from spec.md + contracts.jsonl.

Replaces v1's progress.tsv as the canonical state view. There is no separate
state file in v3.8 — the active sprint, completion status, and "what's next"
all derive deterministically from these two files plus git history.

Usage:
    python epic_status.py [path-to-_epic-dir]    # default: specs/_epic/
    python epic_status.py --json                  # machine-readable output
    python epic_status.py --active-sprint         # print just active sprint id (e.g. S03)
    python epic_status.py --is-done               # exit 0 if epic done, 1 otherwise

Pure stdlib.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class SprintInfo:
    id: str
    name: str
    delivers: list[str]
    depends_on: list[str]
    smoke: str
    line: int
    # Derived from contracts.jsonl
    latest_phase: str | None = None  # agreed | completed | amended | None (no contract yet)
    latest_contract_id: str | None = None
    rounds_seen: int = 0  # how many rounds for this sprint (heuristic from _evals/)


def parse_sprints_from_spec(spec_path: Path) -> "OrderedDict[str, SprintInfo]":
    text = spec_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    sprints: OrderedDict[str, SprintInfo] = OrderedDict()

    in_sprint_plan = False
    current: SprintInfo | None = None
    for i, line in enumerate(lines, 1):
        if re.match(r"^##\s+Sprint plan\s*$", line):
            in_sprint_plan = True
            continue
        if in_sprint_plan and re.match(r"^##\s+\S", line):
            # Reached next H2; sprint plan section ended.
            if current is not None:
                sprints[current.id] = current
                current = None
            in_sprint_plan = False
            continue
        if not in_sprint_plan:
            continue
        m = re.match(r"^###\s+(S\d{2})\s+—\s+(.+?)\s*$", line)
        if m:
            if current is not None:
                sprints[current.id] = current
            current = SprintInfo(
                id=m.group(1),
                name=m.group(2).strip(),
                delivers=[],
                depends_on=[],
                smoke="",
                line=i,
            )
            continue
        if current is None:
            continue
        dm = re.match(r"^-\s*Delivers\s*:\s*(.+?)\s*$", line, re.IGNORECASE)
        if dm:
            current.delivers = re.findall(r"F\d{2,3}", dm.group(1))
            continue
        dpm = re.match(r"^-\s*Depends\s*on\s*:\s*(.+?)\s*$", line, re.IGNORECASE)
        if dpm:
            value = dpm.group(1).strip()
            if value.lower() != "(none)":
                current.depends_on = re.findall(r"S\d{2}", value)
            continue
        sm = re.match(r"^-\s*Smoke\s*check\s*:\s*(.+?)\s*$", line, re.IGNORECASE)
        if sm:
            current.smoke = sm.group(1).strip()
            continue
    if current is not None and in_sprint_plan:
        sprints[current.id] = current
    return sprints


def apply_contracts(
    sprints: "OrderedDict[str, SprintInfo]", contracts_path: Path
) -> None:
    """For each sprint, find the LATEST contract entry and stamp phase + contract_id."""
    if not contracts_path.exists():
        return
    # Build per-sprint latest entry
    per_sprint_latest: dict[str, dict[str, Any]] = {}
    with contracts_path.open(encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                # Surface to stderr but don't crash — corrupted line should be visible.
                print(
                    f"epic_status: malformed JSON in contracts.jsonl line {line_no}",
                    file=sys.stderr,
                )
                continue
            sid = entry.get("sprint")
            if not sid:
                continue
            # We use timestamp ordering; falls back to file order if absent.
            existing = per_sprint_latest.get(sid)
            if existing is None or entry.get("timestamp", "") >= existing.get(
                "timestamp", ""
            ):
                per_sprint_latest[sid] = entry
    for sid, entry in per_sprint_latest.items():
        if sid in sprints:
            sprints[sid].latest_phase = entry.get("phase")
            sprints[sid].latest_contract_id = entry.get("contract_id")


def count_rounds(sprints: "OrderedDict[str, SprintInfo]", evals_dir: Path) -> None:
    """Count rounds per sprint by scanning _evals/S{NN}-R{N}.json files."""
    if not evals_dir.exists():
        return
    for path in evals_dir.iterdir():
        m = re.match(r"^(S\d{2})-R(\d+)\.json$", path.name)
        if not m:
            continue
        sid = m.group(1)
        if sid in sprints:
            sprints[sid].rounds_seen = max(sprints[sid].rounds_seen, int(m.group(2)))


def determine_active(sprints: "OrderedDict[str, SprintInfo]") -> str | None:
    """Active sprint = lowest-id sprint that has not yet reached phase=completed
    AND whose Depends on are all completed.
    """
    completed_ids = {sid for sid, s in sprints.items() if s.latest_phase == "completed"}
    for sid, s in sprints.items():
        if s.latest_phase == "completed":
            continue
        if all(dep in completed_ids for dep in s.depends_on):
            return sid
    return None


def epic_done(sprints: "OrderedDict[str, SprintInfo]") -> bool:
    if not sprints:
        return False
    return all(s.latest_phase == "completed" for s in sprints.values())


def render_human(
    sprints: "OrderedDict[str, SprintInfo]",
    active: str | None,
    epic_slug: str | None,
) -> str:
    out: list[str] = []
    out.append(f"Epic: {epic_slug or '(unknown)'}")
    out.append(f"Sprints: {len(sprints)} planned")
    out.append("")
    for sid, s in sprints.items():
        if s.latest_phase == "completed":
            sym = "[done]"
        elif s.latest_phase in ("agreed", "amended"):
            sym = "[in-progress]"
        elif sid == active:
            sym = "[next]"
        else:
            sym = "[pending]"
        rounds = f" R{s.rounds_seen}" if s.rounds_seen else ""
        out.append(f"  {sid} {sym}{rounds}: {s.name}")
    out.append("")
    if epic_done(sprints):
        out.append("STATUS: epic done (all sprints completed)")
    elif active:
        out.append(f"STATUS: in-progress; active sprint = {active}")
    else:
        out.append("STATUS: blocked (no active sprint and not done — check Depends on)")
    return "\n".join(out)


def render_json(
    sprints: "OrderedDict[str, SprintInfo]",
    active: str | None,
    epic_slug: str | None,
) -> str:
    return json.dumps(
        {
            "epic_slug": epic_slug,
            "active_sprint": active,
            "epic_done": epic_done(sprints),
            "sprints": [
                {
                    "id": s.id,
                    "name": s.name,
                    "delivers": s.delivers,
                    "depends_on": s.depends_on,
                    "smoke": s.smoke,
                    "phase": s.latest_phase,
                    "contract_id": s.latest_contract_id,
                    "rounds_seen": s.rounds_seen,
                }
                for s in sprints.values()
            ],
        },
        indent=2,
    )


def extract_epic_slug(spec_path: Path) -> str | None:
    text = spec_path.read_text(encoding="utf-8")
    m = re.search(r"^#\s+Spec\s+—\s+(.+?)\s*$", text, re.MULTILINE)
    if m:
        return m.group(1).strip()
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Derive epic state from spec.md + contracts.jsonl")
    parser.add_argument(
        "epic_dir",
        nargs="?",
        default="specs/_epic",
        help="Epic directory (default: specs/_epic)",
    )
    parser.add_argument(
        "--json", action="store_true", help="Emit machine-readable JSON"
    )
    parser.add_argument(
        "--active-sprint",
        action="store_true",
        help="Print just the active sprint id (or empty string if done/blocked)",
    )
    parser.add_argument(
        "--is-done",
        action="store_true",
        help="Exit 0 if epic done, 1 otherwise; no output",
    )
    parser.add_argument(
        "--set-context",
        nargs=2,
        metavar=("FEATURE", "ROUND"),
        help="Write <epic_dir>/_traces/current-context.json {feature, round} "
             "so the SubagentStop hook keys traces + progress.tsv rows to "
             "sprint/round. Call immediately before spawning generator / "
             "evaluator.",
    )
    args = parser.parse_args()

    epic_dir = Path(args.epic_dir)

    if args.set_context:
        feature, round_raw = args.set_context
        try:
            round_int = int(round_raw)
        except ValueError:
            print(
                f"epic_status: --set-context ROUND must be an int, got "
                f"{round_raw!r}",
                file=sys.stderr,
            )
            return 2
        ctx_dir = epic_dir / "_traces"
        ctx_dir.mkdir(parents=True, exist_ok=True)
        (ctx_dir / "current-context.json").write_text(
            json.dumps({"feature": feature, "round": round_int}),
            encoding="utf-8",
        )
        return 0

    spec_path = epic_dir / "spec.md"
    contracts_path = epic_dir / "contracts.jsonl"
    evals_dir = epic_dir / "_evals"

    if not spec_path.exists():
        print(f"epic_status: spec.md not found at {spec_path}", file=sys.stderr)
        return 2

    sprints = parse_sprints_from_spec(spec_path)
    apply_contracts(sprints, contracts_path)
    count_rounds(sprints, evals_dir)
    active = determine_active(sprints)
    slug = extract_epic_slug(spec_path)

    if args.is_done:
        return 0 if epic_done(sprints) else 1

    if args.active_sprint:
        print(active or "")
        return 0

    if args.json:
        print(render_json(sprints, active, slug))
    else:
        print(render_human(sprints, active, slug))
    return 0


if __name__ == "__main__":
    sys.exit(main())
