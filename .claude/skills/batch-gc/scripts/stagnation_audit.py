#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Harness Stagnation Audit — V2.3 Item 7.

Retrospective scanner over docs/archive/* + current batch, surfaces:
  - Agents/skills with zero invocations across recent batches
  - Retry distribution per feature (how often R2+ happens)
  - BLOCKED / DONE ratio (planner calibration signal)
  - Evaluator layer verdict aggregation

Output: docs/harness-stagnation-report.md (human-readable) and
        docs/harness-stagnation.json (machine-readable, optional).

Usage:
    uv run .claude/skills/batch-gc/scripts/stagnation_audit.py
    python3 .claude/skills/batch-gc/scripts/stagnation_audit.py --json

"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]  # .claude/skills/batch-gc/scripts/ -> project root
ARCHIVE_DIR = ROOT / "docs" / "archive"
CURRENT_FEATURE_LIST = ROOT / "docs" / "feature-list.json"
CURRENT_PROGRESS = ROOT / "docs" / "progress"
AGENTS_DIR = ROOT / ".claude" / "agents"
SKILLS_DIR = ROOT / ".claude" / "skills"


# File-name pattern for per-round progress artefacts.
# Examples matched: F02-progress-R1.md, F10-eval-R2.md, F03-gen-trace-R1.md
ROUND_FILE_RE = re.compile(r"^(F\d+)-[a-z\-]+-R(\d+)\.md$")

# Layer verdict row inside eval markdown tables.
# Matches rows like: | 1. Static Analysis | PASS | ... | or | 5a. Visual Smoke Check | N/A | ...
LAYER_VERDICT_RE = re.compile(
    r"\|\s*(\d[a-z]?)\.\s*[^|]+?\|\s*(PASS|FAIL|N/A|BLOCKED)\s*\|",
    re.IGNORECASE,
)


@dataclass
class BatchReport:
    slug: str
    is_current: bool = False
    total_features: int = 0
    done: int = 0
    blocked: int = 0
    # feature_id -> max round observed
    rounds_per_feature: dict[str, int] = field(default_factory=dict)
    # "L{n}:{verdict}" -> count (across all eval files in batch)
    layer_verdicts: Counter = field(default_factory=Counter)
    # agent file stem -> count of case-insensitive matches in progress files
    agent_mentions: Counter = field(default_factory=Counter)

    @property
    def blocked_ratio(self) -> float:
        denom = self.done + self.blocked
        return (self.blocked / denom) if denom else 0.0

    @property
    def round_distribution(self) -> Counter:
        return Counter(self.rounds_per_feature.values())


def collect_agents() -> list[str]:
    """Return agent file stems (excluding archived)."""
    if not AGENTS_DIR.exists():
        return []
    return sorted(p.stem for p in AGENTS_DIR.glob("*.md"))


def collect_skills() -> list[str]:
    """Return skill directory names."""
    if not SKILLS_DIR.exists():
        return []
    return sorted(p.name for p in SKILLS_DIR.iterdir() if p.is_dir())


def build_agent_matcher(agents: list[str]) -> re.Pattern[str]:
    """Build a regex that matches any agent name (hyphen or space separator, case-insensitive).

    Matches @spec-auditor, Spec-Auditor, spec_auditor, "Spec Auditor", etc.
    Longest names first to prevent `Auditor` eating `Plan-Auditor`.
    """
    if not agents:
        return re.compile(r"(?!x)x")  # never matches
    sorted_agents = sorted(agents, key=len, reverse=True)
    patterns = []
    for a in sorted_agents:
        parts = a.split("-")
        # allow hyphen, underscore, or space between parts
        patterns.append(r"[-_ ]".join(re.escape(p) for p in parts))
    return re.compile(r"(?<![A-Za-z])(?:@)?(" + "|".join(patterns) + r")(?![A-Za-z])", re.IGNORECASE)


def canonicalize_agent_match(raw: str, agents: list[str]) -> str | None:
    """Map a regex capture back to its canonical agent stem."""
    normalized = re.sub(r"[-_ ]+", "-", raw.lower())
    for a in agents:
        if a.lower() == normalized:
            return a
    return None


def scan_batch(
    feature_list_path: Path,
    progress_dir: Path,
    slug: str,
    is_current: bool,
    agents: list[str],
    matcher: re.Pattern[str],
) -> BatchReport:
    rep = BatchReport(slug=slug, is_current=is_current)

    # Feature list metadata
    if feature_list_path.exists():
        try:
            data = json.loads(feature_list_path.read_text())
            rep.total_features = data.get("meta", {}).get("totalFeatures", 0)
            for f in data.get("features", []):
                status = (f.get("status") or "").upper()
                if status == "DONE":
                    rep.done += 1
                elif status == "BLOCKED":
                    rep.blocked += 1
        except json.JSONDecodeError as e:
            print(f"[warn] {feature_list_path}: JSON decode error: {e}", file=sys.stderr)

    # Progress files
    if progress_dir.exists():
        for p in sorted(progress_dir.glob("*.md")):
            m = ROUND_FILE_RE.match(p.name)
            if m:
                fid, rnd = m.group(1), int(m.group(2))
                if rnd > rep.rounds_per_feature.get(fid, 0):
                    rep.rounds_per_feature[fid] = rnd

            try:
                text = p.read_text(errors="ignore")
            except OSError as e:
                print(f"[warn] cannot read {p}: {e}", file=sys.stderr)
                continue

            # Agent mentions
            for match in matcher.finditer(text):
                canonical = canonicalize_agent_match(match.group(1), agents)
                if canonical:
                    rep.agent_mentions[canonical] += 1

            # Layer verdicts (only eval files)
            if "-eval-" in p.name or p.name.startswith("AUDIT"):
                for lm in LAYER_VERDICT_RE.finditer(text):
                    layer = lm.group(1)
                    verdict = lm.group(2).upper().replace("/", "_")  # N/A -> N_A
                    rep.layer_verdicts[f"L{layer}:{verdict}"] += 1

    return rep


def discover_batches(agents: list[str], matcher: re.Pattern[str]) -> list[BatchReport]:
    reports: list[BatchReport] = []

    # Archived batches
    if ARCHIVE_DIR.exists():
        for batch_dir in sorted(ARCHIVE_DIR.iterdir()):
            if not batch_dir.is_dir():
                continue
            fl = batch_dir / "feature-list.json"
            pg = batch_dir / "progress"
            if not (fl.exists() or pg.exists()):
                continue
            reports.append(
                scan_batch(fl, pg, slug=batch_dir.name, is_current=False, agents=agents, matcher=matcher)
            )

    # Current in-flight batch
    if CURRENT_FEATURE_LIST.exists() or CURRENT_PROGRESS.exists():
        reports.append(
            scan_batch(
                CURRENT_FEATURE_LIST,
                CURRENT_PROGRESS,
                slug="CURRENT",
                is_current=True,
                agents=agents,
                matcher=matcher,
            )
        )

    return reports


# ---------- Rendering ----------

def render_markdown(reports: list[BatchReport], agents: list[str], skills: list[str]) -> str:
    md: list[str] = []
    md.append("# Harness Stagnation Audit")
    md.append("")
    md.append(f"- Batches scanned: **{len(reports)}**")
    md.append(f"- Agents in `.claude/agents/`: **{len(agents)}**")
    md.append(f"- Skills in `.claude/skills/`: **{len(skills)}**")
    md.append("")
    md.append("> Generated by `.claude/skills/batch-gc/scripts/stagnation_audit.py` (V2.3 Item 7).")
    md.append("> Interpretation discipline: zero-mention ≠ must-delete; it is a *prompt to ask* why the component exists.")
    md.append("")

    # ----- Section 1: agent invocation -----
    md.append("## 1. Agent invocation across batches")
    md.append("")
    agent_totals: Counter = Counter()
    agent_batches_hit: Counter = Counter()
    for r in reports:
        for a, c in r.agent_mentions.items():
            agent_totals[a] += c
            if c > 0:
                agent_batches_hit[a] += 1

    md.append("| Agent | Total mentions | Batches hit / total | Status |")
    md.append("|---|---:|:---:|---|")
    for a in agents:
        total = agent_totals.get(a, 0)
        hits = agent_batches_hit.get(a, 0)
        if total == 0:
            status = "⚠️ ZERO mentions"
        elif hits < len(reports) // 2:
            status = "🟡 Sparse"
        else:
            status = "🟢 OK"
        md.append(f"| `{a}` | {total} | {hits} / {len(reports)} | {status} |")
    md.append("")

    # ----- Section 2: retry distribution -----
    md.append("## 2. Retry distribution (max round per feature)")
    md.append("")
    md.append("| Batch | Total F | R1 | R2 | R3+ |")
    md.append("|---|---:|---:|---:|---:|")
    grand = Counter()
    for r in reports:
        dist = r.round_distribution
        r1 = dist.get(1, 0)
        r2 = dist.get(2, 0)
        r3 = sum(v for k, v in dist.items() if k >= 3)
        grand["R1"] += r1
        grand["R2"] += r2
        grand["R3+"] += r3
        md.append(f"| {r.slug} | {r.total_features} | {r1} | {r2} | {r3} |")
    total_rounds = sum(grand.values())
    if total_rounds:
        md.append(f"| **TOTAL** | — | {grand['R1']} | {grand['R2']} | {grand['R3+']} |")
    md.append("")

    # ----- Section 3: BLOCKED/DONE ratio -----
    md.append("## 3. BLOCKED vs DONE ratio")
    md.append("")
    md.append("| Batch | DONE | BLOCKED | Ratio | Flag |")
    md.append("|---|---:|---:|---:|---|")
    for r in reports:
        flag = " ⚠️ >20%" if r.blocked_ratio > 0.20 else ""
        md.append(f"| {r.slug} | {r.done} | {r.blocked} | {r.blocked_ratio:.1%} |{flag}")
    md.append("")

    # ----- Section 4: Layer verdict aggregation -----
    md.append("## 4. Evaluator layer verdicts (aggregated across all eval files)")
    md.append("")
    layer_agg: Counter = Counter()
    for r in reports:
        layer_agg.update(r.layer_verdicts)
    if layer_agg:
        # Group by layer
        by_layer: dict[str, Counter] = {}
        for key, count in layer_agg.items():
            layer, verdict = key.split(":", 1)
            by_layer.setdefault(layer, Counter())[verdict] += count
        md.append("| Layer | PASS | FAIL | N/A |")
        md.append("|---|---:|---:|---:|")
        for layer in sorted(by_layer):
            cs = by_layer[layer]
            md.append(f"| {layer} | {cs.get('PASS', 0)} | {cs.get('FAIL', 0)} | {cs.get('N_A', 0)} |")
    else:
        md.append("_No layer-verdict rows parsed. Either no eval files present or table format diverges._")
    md.append("")

    # ----- Section 5: Ratchet recommendations -----
    md.append("## 5. Ratchet recommendations")
    md.append("")
    unused = [a for a in agents if agent_totals.get(a, 0) == 0]
    if unused:
        md.append(f"- **{len(unused)} agent(s) with ZERO mentions** across {len(reports)} batches — ask whether each earns its spot:")
        for a in unused:
            md.append(f"  - `{a}` — verify by reading `.claude/agents/{a}.md` + grep wider paths; if genuinely unused ≥ 3 batches, move to `.claude/agents/_archived/`.")
    else:
        md.append("- ✅ Every agent has at least one mention.")
    md.append("")

    if total_rounds:
        r3_pct = grand["R3+"] / total_rounds
        if r3_pct < 0.02 and total_rounds >= 10:
            md.append(
                f"- **R3+ is only {r3_pct:.1%}** of rounds across {total_rounds} features — "
                "consider capping retry at 2 (Anthropic V1→V2 simplification pattern)."
            )
    md.append("")

    high_block = [r.slug for r in reports if r.blocked_ratio > 0.20]
    if high_block:
        md.append(
            f"- **Planner calibration signal**: batches with >20% BLOCKED: {', '.join(high_block)}. "
            "Inspect what planner over-scoped; feed into plan-dreamer capsules."
        )
    md.append("")

    md.append("---")
    md.append("")
    md.append("_End of report. Rerun after each `/consolidate` to track drift trend._")
    return "\n".join(md)


def render_json(reports: list[BatchReport], agents: list[str], skills: list[str]) -> str:
    # Build JSON manually: dataclasses.asdict() mis-handles Counter
    # (its constructor treats (k, v) tuples as elements, producing tuple keys).
    out = {
        "batches": [
            {
                "slug": r.slug,
                "is_current": r.is_current,
                "total_features": r.total_features,
                "done": r.done,
                "blocked": r.blocked,
                "blocked_ratio": round(r.blocked_ratio, 4),
                "rounds_per_feature": dict(r.rounds_per_feature),
                "round_distribution": {str(k): v for k, v in r.round_distribution.items()},
                "layer_verdicts": dict(r.layer_verdicts),
                "agent_mentions": dict(r.agent_mentions),
            }
            for r in reports
        ],
        "agents": agents,
        "skills": skills,
    }
    return json.dumps(out, indent=2, ensure_ascii=False)


def main() -> int:
    parser = argparse.ArgumentParser(description="Harness Stagnation Audit — V2.3 Item 7")
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "docs" / "harness-stagnation-report.md",
        help="Markdown report destination.",
    )
    parser.add_argument(
        "--json",
        type=Path,
        nargs="?",
        const=ROOT / "docs" / "harness-stagnation.json",
        help="Also emit machine-readable JSON at this path (default: docs/harness-stagnation.json).",
    )
    parser.add_argument("--stdout", action="store_true", help="Print markdown to stdout instead of writing.")
    args = parser.parse_args()

    agents = collect_agents()
    skills = collect_skills()
    matcher = build_agent_matcher(agents)

    reports = discover_batches(agents, matcher)
    if not reports:
        print("No archived or current batches found; nothing to audit.", file=sys.stderr)
        return 0

    md = render_markdown(reports, agents, skills)

    if args.stdout:
        sys.stdout.write(md)
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(md)
        print(f"Wrote markdown report: {args.output.relative_to(ROOT)}")

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(render_json(reports, agents, skills))
        print(f"Wrote JSON report:     {args.json.relative_to(ROOT)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
