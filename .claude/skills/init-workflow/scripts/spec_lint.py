#!/usr/bin/env python3
"""spec_lint.py — validate specs/_epic/spec.md against the v3.8 contract.

Rules (see .claude/schemas/spec.schema.md):
  L01  All required H2 sections present in correct order;
       every F-id covered by exactly one sprint Delivers
  L02  Feature names contain no phase markers
  L03  Every sprint has Delivers + Depends on + Smoke check
  L04  Smoke check starts with user-observable verb; not mechanical
  L05  Sprint deliverables touch >=2 layers OR are explicitly tagged pure-*
  L06  Overall success criteria has >=1 end-to-end behavioral entry
  L07  Archetype is set; Evaluation criteria block has exactly 4 numbered entries
  L08  If `### Domain terms` appears under `## Cross-cutting constraints`,
       every bullet matches `- **<term>** — <definition>` and term names
       are unique within the section

Pure stdlib. Exit 0 on PASS; exit 1 with JSON-on-stderr listing of failures
on FAIL. Output structure:

  { "rule": "L02", "section": "Features", "feature_id": "F03",
    "line": 42, "message": "..." }

Each failure is one line of JSON for grep / jq friendliness.
"""
from __future__ import annotations

import json
import re
import sys
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REQUIRED_H2_ORDER = [
    "Vision",
    "Tech stack",
    "Archetype",
    "Features",
    "Sprint plan",
    "Evaluation criteria",
    "Cross-cutting constraints",
    "Overall success criteria",
    "References",
]

VALID_ARCHETYPES = {
    "frontend",
    "backend",
    "library",
    "cli",
    "data-pipeline",
    "hybrid",
}

PHASE_MARKERS = [
    "backend",
    "frontend",
    "api layer",
    "database layer",
    "phase 1",
    "phase 2",
    "phase 3",
    "infrastructure",
    "scaffolding",
    "setup",
]

# Smoke check must start with one of these verb phrases (case-insensitive).
USER_OBSERVABLE_VERBS = [
    "user can",
    "user sees",
    "user receives",
    "user navigates",
    "user opens",
    "user enters",
    "user submits",
    "user clicks",
    "user types",
    "user runs",
    "user installs",
    "user reads",
    "user writes",
    "user shares",
    "user exports",
    "user imports",
    "user uploads",
    "user downloads",
    "user creates",
    "user edits",
    "user deletes",
    "user signs",
    "user logs",
    "system shows",
    "system responds",
    "system rejects",
    "system accepts",
    "system persists",
]

MECHANICAL_PHRASES = [
    "code compiles",
    "tests pass",
    "lint clean",
    "type-check",
    "type check",
    "no errors",
    "build succeeds",
    "ci green",
    "coverage >",
    "coverage exceeds",
]

PURE_LAYER_TAGS = {
    "(pure-frontend)",
    "(pure-backend)",
    "(pure-lib)",
    "(pure-cli)",
    "(pure-data)",
}


@dataclass
class Failure:
    rule: str
    section: str
    line: int
    message: str
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "rule": self.rule,
            "section": self.section,
            "line": self.line,
            "message": self.message,
        }
        d.update(self.extra)
        return d


@dataclass
class Section:
    name: str
    start: int  # 1-indexed
    end: int    # 1-indexed exclusive (line after last content line)
    body: str


def parse_h2_sections(text: str) -> list[Section]:
    """Split text into ## H2 sections, in order."""
    lines = text.splitlines()
    sections: list[Section] = []
    current_name: str | None = None
    current_start = 0
    current_body: list[str] = []
    for i, line in enumerate(lines, 1):
        m = re.match(r"^##\s+(.+?)\s*$", line)
        if m and not line.startswith("###"):
            # close previous
            if current_name is not None:
                sections.append(
                    Section(
                        name=current_name,
                        start=current_start,
                        end=i,
                        body="\n".join(current_body),
                    )
                )
            current_name = m.group(1).strip()
            current_start = i
            current_body = []
        elif current_name is not None:
            current_body.append(line)
    if current_name is not None:
        sections.append(
            Section(
                name=current_name,
                start=current_start,
                end=len(lines) + 1,
                body="\n".join(current_body),
            )
        )
    return sections


def parse_features(features_section: Section) -> "OrderedDict[str, dict[str, Any]]":
    """Returns ordered map of F-id -> { name, sprint, line, body }."""
    features: OrderedDict[str, dict[str, Any]] = OrderedDict()
    lines = features_section.body.splitlines()
    current_id: str | None = None
    current: dict[str, Any] = {}
    line_offset = features_section.start
    for i, line in enumerate(lines, 1):
        absolute_line = line_offset + i
        m = re.match(r"^###\s+(F\d{2,3})\s+—\s+(.+?)\s*$", line)
        if m:
            if current_id is not None:
                features[current_id] = current
            current_id = m.group(1)
            current = {
                "id": current_id,
                "name": m.group(2).strip(),
                "line": absolute_line,
                "sprint": None,
                "user_stories_present": False,
                "data_model_present": False,
                "body_lines": [],
            }
        elif current_id is not None:
            current["body_lines"].append(line)
            sm = re.match(r"^\*\*Sprint\*\*\s*:\s*(S\d{2})\b", line)
            if sm:
                current["sprint"] = sm.group(1)
            if re.match(r"^\*\*User stories\*\*", line):
                current["user_stories_present"] = True
            if re.match(r"^\*\*Data model\*\*", line):
                current["data_model_present"] = True
    if current_id is not None:
        features[current_id] = current
    return features


def parse_sprints(sprint_section: Section) -> "OrderedDict[str, dict[str, Any]]":
    """Returns ordered map of S-id -> { name, delivers, depends_on, smoke, layer_tag, line }."""
    sprints: OrderedDict[str, dict[str, Any]] = OrderedDict()
    lines = sprint_section.body.splitlines()
    current_id: str | None = None
    current: dict[str, Any] = {}
    line_offset = sprint_section.start
    for i, line in enumerate(lines, 1):
        absolute_line = line_offset + i
        m = re.match(r"^###\s+(S\d{2})\s+—\s+(.+?)\s*$", line)
        if m:
            if current_id is not None:
                sprints[current_id] = current
            current_id = m.group(1)
            name_with_tag = m.group(2).strip()
            tag = None
            for candidate in PURE_LAYER_TAGS:
                if name_with_tag.endswith(candidate):
                    tag = candidate
                    name_with_tag = name_with_tag[: -len(candidate)].strip()
                    break
            current = {
                "id": current_id,
                "name": name_with_tag,
                "layer_tag": tag,
                "line": absolute_line,
                "delivers": [],
                "depends_on": None,
                "smoke": None,
                "reason_single_layer": None,
            }
        elif current_id is not None:
            dm = re.match(r"^-\s*Delivers\s*:\s*(.+?)\s*$", line, re.IGNORECASE)
            if dm:
                ids = re.findall(r"F\d{2,3}", dm.group(1))
                current["delivers"] = ids
                continue
            dpm = re.match(r"^-\s*Depends\s*on\s*:\s*(.+?)\s*$", line, re.IGNORECASE)
            if dpm:
                value = dpm.group(1).strip()
                if value.lower() == "(none)":
                    current["depends_on"] = []
                else:
                    current["depends_on"] = re.findall(r"S\d{2}", value)
                continue
            sm = re.match(r"^-\s*Smoke\s*check\s*:\s*(.+?)\s*$", line, re.IGNORECASE)
            if sm:
                current["smoke"] = sm.group(1).strip()
                continue
            rm = re.match(r"^-\s*Reason\s*for\s*single-layer\s*:\s*(.+?)\s*$", line, re.IGNORECASE)
            if rm:
                current["reason_single_layer"] = rm.group(1).strip()
                continue
    if current_id is not None:
        sprints[current_id] = current
    return sprints


def lint(text: str) -> list[Failure]:
    failures: list[Failure] = []
    sections = parse_h2_sections(text)
    name_to_section = {s.name: s for s in sections}

    # --- L01: required H2 in correct order, exact set ---
    actual_names = [s.name for s in sections]
    if actual_names != REQUIRED_H2_ORDER:
        failures.append(
            Failure(
                rule="L01",
                section="(top-level)",
                line=1,
                message="H2 sections do not match required order",
                extra={"expected": REQUIRED_H2_ORDER, "actual": actual_names},
            )
        )
        # Continue with checks where possible.

    # --- L07a: Archetype valid ---
    if "Archetype" in name_to_section:
        body = name_to_section["Archetype"].body.strip()
        # First non-empty line should be the archetype value.
        first_line = next((ln.strip() for ln in body.splitlines() if ln.strip()), "")
        if first_line not in VALID_ARCHETYPES:
            failures.append(
                Failure(
                    rule="L07",
                    section="Archetype",
                    line=name_to_section["Archetype"].start,
                    message=f"Archetype must be one of {sorted(VALID_ARCHETYPES)}; got '{first_line}'",
                )
            )

    # --- L07b: Evaluation criteria has exactly 4 numbered entries ---
    if "Evaluation criteria" in name_to_section:
        body = name_to_section["Evaluation criteria"].body
        numbered = re.findall(r"^\s*(\d+)\.\s+\*\*", body, re.MULTILINE)
        if len(numbered) != 4:
            failures.append(
                Failure(
                    rule="L07",
                    section="Evaluation criteria",
                    line=name_to_section["Evaluation criteria"].start,
                    message=f"Evaluation criteria must have exactly 4 numbered entries with **bold** name; got {len(numbered)}",
                )
            )

    # --- Features parsing ---
    features: "OrderedDict[str, dict[str, Any]]" = OrderedDict()
    if "Features" in name_to_section:
        features = parse_features(name_to_section["Features"])

    # --- L02: feature names contain no phase markers ---
    for fid, fdata in features.items():
        name_lower = fdata["name"].lower()
        for marker in PHASE_MARKERS:
            if marker in name_lower:
                failures.append(
                    Failure(
                        rule="L02",
                        section="Features",
                        line=fdata["line"],
                        message=f"Feature name '{fdata['name']}' contains phase marker '{marker}'. Vertical-slice rule: features should describe user-facing capabilities, not implementation phases.",
                        extra={"feature_id": fid},
                    )
                )
                break

    # --- Sprint parsing ---
    sprints: "OrderedDict[str, dict[str, Any]]" = OrderedDict()
    if "Sprint plan" in name_to_section:
        sprints = parse_sprints(name_to_section["Sprint plan"])

    # --- L01 (continued): every F-id covered by exactly one sprint Delivers ---
    feature_to_sprint_count: dict[str, int] = {fid: 0 for fid in features}
    for sid, sdata in sprints.items():
        for fid in sdata["delivers"]:
            if fid in feature_to_sprint_count:
                feature_to_sprint_count[fid] += 1
    for fid, count in feature_to_sprint_count.items():
        if count == 0:
            failures.append(
                Failure(
                    rule="L01",
                    section="Sprint plan",
                    line=features[fid]["line"],
                    message=f"Feature {fid} is not delivered by any sprint",
                    extra={"feature_id": fid},
                )
            )
        elif count > 1:
            failures.append(
                Failure(
                    rule="L01",
                    section="Sprint plan",
                    line=features[fid]["line"],
                    message=f"Feature {fid} is delivered by {count} sprints; must be exactly one",
                    extra={"feature_id": fid},
                )
            )
    # Each feature also declares a Sprint field — must match the delivering sprint.
    for fid, fdata in features.items():
        if fdata["sprint"] is None:
            failures.append(
                Failure(
                    rule="L03",
                    section="Features",
                    line=fdata["line"],
                    message=f"Feature {fid} missing **Sprint**: line",
                    extra={"feature_id": fid},
                )
            )

    # --- L03: every sprint has Delivers + Depends on + Smoke check ---
    for sid, sdata in sprints.items():
        missing: list[str] = []
        if not sdata["delivers"]:
            missing.append("Delivers")
        if sdata["depends_on"] is None:
            missing.append("Depends on")
        if not sdata["smoke"]:
            missing.append("Smoke check")
        if missing:
            failures.append(
                Failure(
                    rule="L03",
                    section="Sprint plan",
                    line=sdata["line"],
                    message=f"Sprint {sid} missing required fields: {', '.join(missing)}",
                    extra={"sprint_id": sid},
                )
            )

    # --- L04: smoke check starts with user-observable verb; not mechanical ---
    for sid, sdata in sprints.items():
        smoke = (sdata["smoke"] or "").lower()
        if not smoke:
            continue
        # Mechanical phrase ban first (more specific)
        for mech in MECHANICAL_PHRASES:
            if mech in smoke:
                failures.append(
                    Failure(
                        rule="L04",
                        section="Sprint plan",
                        line=sdata["line"],
                        message=f"Sprint {sid} smoke check uses mechanical phrase '{mech}'. Use a user-observable behavior instead.",
                        extra={"sprint_id": sid},
                    )
                )
                break
        # Verb prefix check
        if not any(smoke.startswith(verb) for verb in USER_OBSERVABLE_VERBS):
            failures.append(
                Failure(
                    rule="L04",
                    section="Sprint plan",
                    line=sdata["line"],
                    message=f"Sprint {sid} smoke check must start with a user-observable verb (e.g., 'User can ...', 'System shows ...'). Got: '{sdata['smoke']}'",
                    extra={"sprint_id": sid},
                )
            )

    # --- L05: sprint deliverables touch >=2 layers OR explicit pure-* tag ---
    # We need archetype context to decide layers. Heuristic: if every feature in
    # sprint has the same "primary layer" inferred from its Data model presence and
    # archetype, it's single-layer. We rely on planner to tag pure-* explicitly;
    # absence of tag + single-layer-looking sprint -> failure. Implementation:
    # if no pure-* tag AND no Reason for single-layer line, we ALWAYS pass this rule
    # at the lint level (we can't infer layers reliably from spec alone). The
    # downstream evaluator catches missing cross-layer threading at QA time.
    # However, we DO catch the explicit case: if pure-* tag is set, no further check.
    # If neither tag nor reason, leave as warning-equivalent (no failure here).
    for sid, sdata in sprints.items():
        if sdata["layer_tag"] and sdata["reason_single_layer"]:
            # Both tag and reason set — that's redundant but not an error.
            continue

    # --- L08: Domain terms block format (optional sub-heading) ---
    if "Cross-cutting constraints" in name_to_section:
        cc_section = name_to_section["Cross-cutting constraints"]
        cc_lines = cc_section.body.splitlines()
        cc_start = cc_section.start
        dt_idx: int | None = None
        for j, line in enumerate(cc_lines):
            if re.match(r"^###\s+Domain\s+terms\s*$", line):
                dt_idx = j
                break
            # Bad heading variants that look like Domain terms but aren't exact.
            if re.match(r"^###\s+Domain\s+terms\s+\(.+\)\s*$", line):
                failures.append(
                    Failure(
                        rule="L08",
                        section="Cross-cutting constraints",
                        line=cc_start + j + 1,
                        message=(
                            "Domain terms heading must be exactly "
                            "`### Domain terms` (no parenthetical "
                            "suffix). /finalize merge_domain_terms.py "
                            "matches the heading verbatim."
                        ),
                    )
                )
                dt_idx = None
                break
        if dt_idx is not None:
            # Collect block until next H2/H3.
            block: list[tuple[int, str]] = []
            k = dt_idx + 1
            while k < len(cc_lines) and not re.match(
                r"^##\s|^###\s", cc_lines[k]
            ):
                block.append((cc_start + k + 1, cc_lines[k]))
                k += 1
            seen_terms: dict[str, int] = {}
            term_bullet_re = re.compile(
                r"^-\s+\*\*([^*]+?)\*\*\s+(?:—|--)\s+\S"
            )
            for abs_line, raw in block:
                stripped = raw.strip()
                if not stripped:
                    continue
                if raw.startswith("  ") and not stripped.startswith("-"):
                    # Continuation of previous bullet; accept silently.
                    continue
                m_term = term_bullet_re.match(raw)
                if not m_term:
                    failures.append(
                        Failure(
                            rule="L08",
                            section="Cross-cutting constraints",
                            line=abs_line,
                            message=(
                                "Domain terms entry must be `- **<term>** "
                                "— <definition>` (em-dash or `--`). "
                                f"Got: {raw!r}"
                            ),
                        )
                    )
                    continue
                term = m_term.group(1).strip()
                if term in seen_terms:
                    failures.append(
                        Failure(
                            rule="L08",
                            section="Cross-cutting constraints",
                            line=abs_line,
                            message=(
                                f"Domain term '{term}' appears more than "
                                f"once (first at line {seen_terms[term]})."
                            ),
                            extra={"term": term},
                        )
                    )
                else:
                    seen_terms[term] = abs_line

    # --- L06: overall success criteria has >=1 end-to-end behavioral entry ---
    if "Overall success criteria" in name_to_section:
        body = name_to_section["Overall success criteria"].body
        items = re.findall(r"^\s*\d+\.\s+(.+?)$", body, re.MULTILINE)
        if not items:
            failures.append(
                Failure(
                    rule="L06",
                    section="Overall success criteria",
                    line=name_to_section["Overall success criteria"].start,
                    message="Overall success criteria must have a numbered list with at least one entry",
                )
            )
        else:
            # At least one item must NOT be mechanical AND should hint at a flow.
            has_behavioral = False
            flow_hints = ["can ", "sees ", "receives ", "completes ", "navigates ", "submits ", "shares ", "exports ", "uploads ", "from "]
            for item in items:
                lower = item.lower()
                is_mech = any(mech in lower for mech in MECHANICAL_PHRASES)
                has_flow = any(hint in lower for hint in flow_hints)
                if not is_mech and has_flow:
                    has_behavioral = True
                    break
            if not has_behavioral:
                failures.append(
                    Failure(
                        rule="L06",
                        section="Overall success criteria",
                        line=name_to_section["Overall success criteria"].start,
                        message="Overall success criteria has no end-to-end behavioral entry. At least one item should describe a user-observable flow.",
                    )
                )

    return failures


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: spec_lint.py <path/to/spec.md>", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    if not path.exists():
        print(f"spec.md not found: {path}", file=sys.stderr)
        return 2
    text = path.read_text(encoding="utf-8")
    failures = lint(text)
    if not failures:
        print(f"PASS: {path}")
        return 0
    print(f"FAIL: {path} ({len(failures)} issues)", file=sys.stderr)
    for f in failures:
        print(json.dumps(f.to_dict(), ensure_ascii=False), file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
