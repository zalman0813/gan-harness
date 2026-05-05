#!/usr/bin/env python3
"""block_pretool.py — Claude PreToolUse hook: enforce adversarial separation.

Each agent grades the ARTIFACT against the RUBRIC it owns. Reading the
private prompt/handbook/output of agents on the other side of the gate
produces "teach to the test" (generator side) or "preference leakage"
(evaluator side). Shared skills (deep-module-handbook, planner-handbook,
stack skills) are NOT blocked — they are project ground truth.

Active agent matrix:
    codebase-fact-finder -> blindfolded from specs/_batch/prd.md and
                            specs/_batch/_research-queue.md / _research-findings
    planner              -> no denials (single-agent self-verify)
    generator            -> forbidden from .claude/agents/evaluator.md and
                            .claude/skills/evaluator-handbook/
    evaluator            -> forbidden from .claude/agents/generator.md and
                            .claude/skills/generator-handbook/

Input:  Claude Code PreToolUse JSON on stdin
Output: permissionDecision=deny JSON when blocking; silent exit 0 otherwise.
"""
from __future__ import annotations

import json
import re
import sys

LEAKABLE_TOOLS = {"Read", "Grep", "Glob", "Bash"}

RULES: dict[str, tuple[str, str] | None] = {
    "codebase-fact-finder": (
        r"specs/_batch/prd\.md"
        r"|specs/_batch/_research-queue\.md"
        r'|specs/_batch/_research-findings(/|"|$)',
        "codebase-fact-finder is blindfolded from specs/_batch/prd.md and "
        "_research-queue.md. CRISPY discipline: documentarian must not see "
        "the ticket. Report what IS in the codebase with file:line evidence; "
        "opinions and goal-shaped framing leak when the ticket is visible.",
    ),
    "planner": None,
    "generator": (
        r"\.claude/agents/evaluator\.md"
        r'|\.claude/skills/evaluator-handbook(/|"|$)'
        r"|\.git/hooks/",
        "Generator is forbidden from reading evaluator-private paths "
        "(.claude/agents/evaluator.md, .claude/skills/evaluator-handbook/) "
        "and the project's git hooks (.git/hooks/). The pre-commit hook is "
        "the single enforcement point and must remain opaque — fix from "
        "commit stderr (the failing tool's own output), not by reading the "
        "gate source. Shared skills (deep-module-handbook, planner-handbook, "
        "stack skills) are allowed.",
    ),
    "evaluator": (
        r"\.claude/agents/generator\.md"
        r'|\.claude/skills/generator-handbook(/|"|$)'
        r"|\.git/hooks/",
        "Evaluator is forbidden from reading generator-private paths "
        "(.claude/agents/generator.md, .claude/skills/generator-handbook/) "
        "and the project's git hooks (.git/hooks/). Grade the artefact "
        "(feature spec + generator trace + git diff + your own probes) "
        "independently — do not anchor on the generator's worldview or the "
        "gate's internal logic. Shared skills are allowed.",
    ),
}


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    if event.get("tool_name") not in LEAKABLE_TOOLS:
        return 0
    rule = RULES.get(event.get("agent_type", ""))
    if rule is None:
        return 0
    forbidden_regex, reason = rule
    blob = json.dumps(event.get("tool_input", {}))
    if re.search(forbidden_regex, blob):
        json.dump(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": reason,
                }
            },
            sys.stdout,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
