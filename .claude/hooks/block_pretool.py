#!/usr/bin/env python3
"""block_pretool.py — Claude PreToolUse hook.

Two enforcement dimensions:

1. **Read-side adversarial separation** (v1, retained):
   Each agent grades its own ARTIFACT against the RUBRIC it owns. Reading the
   private prompt of agents on the other side of the gate produces "teach to
   the test" (generator side) or "preference leakage" (evaluator side).
   Shared skills (deep-module-handbook, escalation, stack skills) are NOT
   blocked — they are project ground truth.

   Active agent matrix:
       codebase-fact-finder -> blindfolded from specs/_*/prd.md, _research-queue.md
       planner              -> no denials (single-agent self-verify)
       generator            -> forbidden from .claude/agents/evaluator.md
       evaluator            -> forbidden from .claude/agents/generator.md

2. **Write-side immutability** (v3.8 new):
   - specs/_epic/spec.md is immutable after /init. Only the planner agent may
     write/edit it. generator/evaluator/codebase-fact-finder are denied.
   - specs/_epic/contracts.jsonl is append-only. Edit / NotebookEdit are
     always denied (any agent). Write is allowed (the agent that writes is
     expected to read first then write the whole file with one extra line;
     contract_lint validates the result).
   - Bash commands that target these paths via redirect (>), sed -i, tee, etc.
     are denied for the same agents.

Input:  Claude Code PreToolUse JSON on stdin
Output: permissionDecision=deny JSON when blocking; silent exit 0 otherwise.
"""
from __future__ import annotations

import json
import re
import sys

# ─── Read-side leakage rules (v1) ────────────────────────────────────────────

LEAKABLE_TOOLS = {"Read", "Grep", "Glob", "Bash"}

LEAK_RULES: dict[str, tuple[str, str] | None] = {
    "codebase-fact-finder": (
        r"specs/_(batch|epic)/prd\.md"
        r"|specs/_(batch|epic)/_research-queue\.md"
        r'|specs/_(batch|epic)/_research-findings(/|"|$)'
        r"|specs/_(batch|epic)/spec\.md",
        "codebase-fact-finder is blindfolded from the planner's intent artifacts "
        "(spec.md / prd.md / _research-queue.md). CRISPY discipline: the "
        "documentarian must not see the ticket. Report what IS in the codebase "
        "with file:line evidence; opinions and goal-shaped framing leak when "
        "the ticket is visible.",
    ),
    "planner": None,
    "generator": (
        r"\.claude/agents/evaluator\.md"
        r"|\.git/hooks/",
        "Generator is forbidden from reading evaluator-private paths "
        "(.claude/agents/evaluator.md) and the project's git hooks "
        "(.git/hooks/). The pre-commit hook is the single enforcement "
        "point and must remain opaque — fix from commit stderr (the "
        "failing tool's own output), not by reading the gate source. "
        "Shared skills (deep-module-handbook, escalation, stack skills) "
        "are allowed.",
    ),
    "evaluator": (
        r"\.claude/agents/generator\.md"
        r"|\.git/hooks/",
        "Evaluator is forbidden from reading generator-private paths "
        "(.claude/agents/generator.md) and the project's git hooks "
        "(.git/hooks/). Grade the artefact (spec + sprint contract + "
        "transcript-slice + git diff + your own probes) independently — "
        "do not anchor on the generator's worldview or the gate's "
        "internal logic. Shared skills are allowed.",
    ),
}

# ─── Write-side immutability rules (v3.8) ────────────────────────────────────

WRITE_TOOLS = {"Write", "Edit", "NotebookEdit"}

# Path matcher for spec.md (v3.8 epic dir). Matches the literal path exposed
# in tool_input["file_path"].
SPEC_PATH_RE = re.compile(r"specs/_epic/spec\.md$")

# Path matcher for contracts.jsonl.
CONTRACTS_PATH_RE = re.compile(r"specs/_epic/contracts\.jsonl$")

# Agents that may NEVER write/edit spec.md. (planner is the only writer; runs
# during /init only.)
SPEC_WRITE_DENIED_AGENTS = {"generator", "evaluator", "codebase-fact-finder"}

SPEC_WRITE_DENY_REASON = (
    "specs/_epic/spec.md is immutable through /loop. Only the planner agent "
    "writes it (during /init); generator and evaluator read but never modify. "
    "If the spec is wrong, raise the issue via contract amendment "
    "(generator) or contract review feedback (evaluator); a true spec "
    "rewrite is a fresh /init in a new epic."
)

CONTRACTS_EDIT_DENY_REASON = (
    "specs/_epic/contracts.jsonl is append-only. Edit / NotebookEdit are "
    "blocked for all agents. To add a contract entry, read the existing file, "
    "then Write the entire file with the new line appended. Pre-existing "
    "lines must remain byte-identical."
)

# Bash command patterns that mutate a target file (rough but useful):
#   > <path>               (truncate / overwrite)
#   >> <path>              (append — generally allowed for jsonl, but we
#                           still want spec.md never appended)
#   sed -i ... <path>      (in-place edit)
#   tee <path>             (with or without -a)
#   cat ... > <path>       (covered by > rule)
#   mv anything <path>     (clobber)
BASH_MUTATION_PATTERNS = [
    r"(?<!>)>\s*\S",                     # `> path`  (single redirect)
    r">>\s*\S",                          # `>> path`
    r"\bsed\b[^|]*?-i\b",                # `sed -i ...`
    r"\btee\b\s+(?:-a\s+)?\S",           # `tee path` / `tee -a path`
    r"\bmv\b\s+\S+\s+\S",                # `mv src dst`
    r"\bcp\b\s+\S+\s+\S",                # `cp src dst`
]


def _bash_targets_path(command: str, target_re: re.Pattern[str]) -> bool:
    """Heuristic: does this bash command try to mutate the target path?

    True when the command contains both a mutation pattern and a token
    matching the target path regex.
    """
    if not target_re.search(command):
        return False
    for pat in BASH_MUTATION_PATTERNS:
        if re.search(pat, command):
            return True
    return False


def _check_write_immutability(
    agent_type: str, tool_name: str, tool_input: dict
) -> tuple[str, str] | None:
    """Returns (deny_reason, rule_id) if write should be denied; else None."""
    file_path = tool_input.get("file_path") or tool_input.get("notebook_path") or ""

    # Direct Write/Edit on spec.md
    if tool_name in WRITE_TOOLS and SPEC_PATH_RE.search(file_path):
        if agent_type in SPEC_WRITE_DENIED_AGENTS:
            return (SPEC_WRITE_DENY_REASON, "spec.immutable")
        return None  # planner or untyped: allow

    # Direct Edit/NotebookEdit on contracts.jsonl (Write is OK — append flow)
    if tool_name in {"Edit", "NotebookEdit"} and CONTRACTS_PATH_RE.search(file_path):
        return (CONTRACTS_EDIT_DENY_REASON, "contracts.append-only")

    # Bash mutations targeting spec.md
    if tool_name == "Bash":
        cmd = tool_input.get("command", "")
        if _bash_targets_path(cmd, SPEC_PATH_RE):
            if agent_type in SPEC_WRITE_DENIED_AGENTS:
                return (SPEC_WRITE_DENY_REASON, "spec.immutable.bash")
        if _bash_targets_path(cmd, CONTRACTS_PATH_RE):
            # contracts.jsonl: allow `>>` (append) and reject only mutating
            # forms (sed -i, tee without -a, mv, cp, > truncate).
            if re.search(r">>\s*\S", cmd) and not re.search(
                r"\bsed\b|\btee\b\s+(?!-a)|\bmv\b|\bcp\b", cmd
            ):
                return None  # plain `>> contracts.jsonl` — allowed
            return (CONTRACTS_EDIT_DENY_REASON, "contracts.append-only.bash")

    return None


def _check_read_leakage(
    agent_type: str, tool_name: str, tool_input: dict
) -> tuple[str, str] | None:
    """v1 read-side rules. Returns (deny_reason, rule_id) or None."""
    if tool_name not in LEAKABLE_TOOLS:
        return None
    rule = LEAK_RULES.get(agent_type)
    if rule is None:
        return None
    forbidden_regex, reason = rule
    blob = json.dumps(tool_input)
    if re.search(forbidden_regex, blob):
        return (reason, f"leak.{agent_type}")
    return None


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0

    tool_name = event.get("tool_name", "")
    tool_input = event.get("tool_input", {})
    agent_type = event.get("agent_type", "")

    # Write-side immutability runs first (more specific, applies to all agents).
    decision = _check_write_immutability(agent_type, tool_name, tool_input)
    if decision is None:
        # Fall through to read-side leakage check.
        decision = _check_read_leakage(agent_type, tool_name, tool_input)
    if decision is None:
        return 0

    reason, rule_id = decision
    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": f"[{rule_id}] {reason}",
            }
        },
        sys.stdout,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
