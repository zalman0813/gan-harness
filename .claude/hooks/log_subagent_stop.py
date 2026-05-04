#!/usr/bin/env python3
"""log_subagent_stop.py — Claude SubagentStop hook: write audit trail.

Pure logging hook (no validation). On every generator or evaluator
subagent stop, parse the JSONL transcript and write three audit files:

    1. specs/_batch/_traces/{F}-{prefix}-trace-R{N}.md   structured trace
    2. specs/_batch/_traces/{F}-{prefix}-usage-R{N}.json token usage / cost
    3. specs/_batch/progress.tsv                          one append-only row

Other agent_types (planner, codebase-fact-finder) exit silently.

Feature/round context comes from specs/_batch/_traces/current-context.json,
written by harness-loop before spawning each subagent. If absent (manual
spawn outside /execution-loop), the trace lands at
specs/_batch/_traces/<agent>-<ts>.md with no progress.tsv row.

This hook does NO validation — it just records. AC literal coverage is
verified by:
    - generator's pre-commit gate (gate_gen_precommit.py) at write time
    - evaluator's verdict process (per evaluator.md Principle #4) on review
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


# ---------------------------------------------------------------------------
# Trace parser (transcript JSONL → markdown + stats)
# ---------------------------------------------------------------------------

def _classify_step(tool_name: str) -> str:
    if tool_name in {"Read", "Grep", "Glob", "LS"}:
        return "read"
    if tool_name in {"Write", "Edit", "NotebookEdit"}:
        return "write"
    if tool_name == "Bash":
        return "command"
    lower = tool_name.lower()
    if any(k in lower for k in ("test", "analyze", "lint", "type")):
        return "verify"
    if any(k in lower for k in ("launch", "screenshot", "click", "scroll",
                                "browser", "playwright", "computer")):
        return "e2e"
    return "other"


def _summarize_tool_input(tool_name: str, inp: dict) -> str:
    if tool_name == "Read":
        path = inp.get("file_path", "?")
        offset = inp.get("offset")
        limit = inp.get("limit")
        suffix = ""
        if offset or limit:
            suffix = f" [{offset or 0}:{(offset or 0) + (limit or 0)}]"
        return f"Read {path}{suffix}"
    if tool_name == "Write":
        return f"Write {inp.get('file_path', '?')}"
    if tool_name == "Edit":
        return f"Edit {inp.get('file_path', '?')}"
    if tool_name == "Bash":
        cmd = inp.get("command", "?")
        if len(cmd) > 150:
            cmd = cmd[:147] + "..."
        return f"$ {cmd}"
    if tool_name == "Grep":
        return f"Grep '{inp.get('pattern', '?')}' in {inp.get('path', '.')}"
    if tool_name == "Glob":
        return f"Glob '{inp.get('pattern', '?')}'"
    if tool_name.startswith("mcp__"):
        return tool_name.split("__", 2)[-1] if tool_name.count("__") >= 2 else tool_name
    return tool_name


def _parse_transcript(transcript_path: str) -> dict:
    steps = []
    started = None
    ended = None
    with open(transcript_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            msg = obj.get("message", {})
            role = msg.get("role", "")
            content = msg.get("content", "")
            ts = obj.get("timestamp", "")
            if ts and not started:
                started = ts
            if ts:
                ended = ts
            if not isinstance(content, list):
                continue
            for block in content:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "tool_use" and role == "assistant":
                    tool_name = block.get("name", "")
                    tool_input = block.get("input", {})
                    steps.append({
                        "timestamp": ts,
                        "tool": tool_name,
                        "summary": _summarize_tool_input(tool_name, tool_input),
                        "phase": _classify_step(tool_name),
                    })
                if block.get("type") == "tool_result":
                    result_content = block.get("content", "")
                    if isinstance(result_content, str):
                        is_error = (
                            "error" in result_content.lower()[:100]
                            or "Error" in result_content[:100]
                            or "FAIL" in result_content[:200]
                        )
                        if is_error and steps:
                            steps[-1]["had_error"] = True
                            steps[-1]["error_snippet"] = (
                                result_content[:150].replace("\n", " ")
                            )
    return {"started": started, "ended": ended, "steps": steps}


def _compute_stats(steps: list) -> dict:
    phase_counts: dict[str, int] = {}
    for s in steps:
        phase_counts[s["phase"]] = phase_counts.get(s["phase"], 0) + 1
    error_steps = [s for s in steps if s.get("had_error")]
    files_read: set[str] = set()
    files_written: set[str] = set()
    commands_run: list[str] = []
    for s in steps:
        summary = s["summary"]
        if s["phase"] == "read" and summary.startswith("Read "):
            files_read.add(summary[5:].split("[")[0].strip())
        elif s["phase"] == "write":
            path = summary.split(" ", 1)[1] if " " in summary else ""
            files_written.add(path)
        elif s["phase"] == "command" and summary.startswith("$ "):
            commands_run.append(summary[2:])
    return {
        "total_steps": len(steps),
        "phase_counts": phase_counts,
        "error_count": len(error_steps),
        "errors": error_steps,
        "files_read": sorted(files_read),
        "files_written": sorted(files_written),
        "commands": commands_run,
    }


def _render_trace_markdown(agent_type: str, feature: str, round_num: int,
                           trace: dict, stats: dict) -> str:
    label = {"generator": "Generator", "evaluator": "Evaluator"}.get(
        agent_type, agent_type.capitalize()
    )
    lines = [
        f"# {label} Trace: {feature} — Round {round_num}",
        "",
        f"Extracted: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}",
        f"Session window: {trace['started'] or '?'} → {trace['ended'] or '?'}",
        f"Total tool calls: {stats['total_steps']}",
        f"Errors encountered: {stats['error_count']}",
        "",
        "## Phase breakdown",
        "",
        "| Phase | Count |",
        "|-------|-------|",
    ]
    for phase, count in sorted(stats["phase_counts"].items(), key=lambda x: -x[1]):
        lines.append(f"| {phase} | {count} |")
    lines.append("")
    if stats["files_read"]:
        lines += ["## Files read", ""] + [f"- {f}" for f in stats["files_read"]] + [""]
    if stats["files_written"]:
        lines += ["## Files written", ""] + [f"- {f}" for f in stats["files_written"]] + [""]
    if stats["commands"]:
        lines += ["## Commands run", ""] + [f"- `{cmd}`" for cmd in stats["commands"]] + [""]
    if stats["errors"]:
        lines += ["## Errors encountered", ""]
        for e in stats["errors"]:
            lines.append(f"- **{e['summary']}**")
            if e.get("error_snippet"):
                lines.append(f"  - `{e['error_snippet']}`")
        lines.append("")
    lines += ["## Step log", "", "| # | Phase | Tool call |", "|---|-------|-----------|"]
    for i, s in enumerate(trace["steps"], 1):
        err = " ❌" if s.get("had_error") else ""
        lines.append(f"| {i} | {s['phase']} | {s['summary']}{err} |")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# progress.tsv writer
# ---------------------------------------------------------------------------

def _read_evaluator_verdict(project_dir: str, feature: str, round_num: int) -> tuple[str, str]:
    p = Path(project_dir) / "specs/_batch/_evals" / f"{feature}-R{round_num}.json"
    if not p.is_file():
        return "", ""
    try:
        data = json.loads(p.read_text())
    except (json.JSONDecodeError, OSError):
        return "", ""
    verdict = str(data.get("verdict", ""))
    note = str(data.get("eval_feedback", {}).get("overall", "")).replace("\t", " ").replace("\n", " ")[:200]
    return verdict, note


def _git_head_short(project_dir: str) -> str:
    try:
        out = subprocess.run(
            ["git", "-C", project_dir, "rev-parse", "--short=7", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
        return out.stdout.strip() if out.returncode == 0 else ""
    except (subprocess.SubprocessError, OSError):
        return ""


def _append_progress_row(progress_tsv: Path, agent_type: str, feature: str,
                         round_num: int, stats: dict, project_dir: str) -> None:
    progress_tsv.parent.mkdir(parents=True, exist_ok=True)
    header = "ts\tfeature\tround\tagent\ttools\tfiles_w\terrors\tverdict\tcommit\tnote\n"
    if not progress_tsv.exists():
        progress_tsv.write_text(header)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    commit = _git_head_short(project_dir) if agent_type == "generator" else ""
    verdict, note = ("", "")
    if agent_type == "evaluator":
        verdict, note = _read_evaluator_verdict(project_dir, feature, round_num)
    row = (
        f"{ts}\t{feature}\t{round_num}\t{agent_type}"
        f"\t{stats['total_steps']}\t{len(stats['files_written'])}"
        f"\t{stats['error_count']}\t{verdict}\t{commit}\t{note}\n"
    )
    with progress_tsv.open("a") as f:
        f.write(row)


# ---------------------------------------------------------------------------
# Token usage + cost (per-round audit)
# ---------------------------------------------------------------------------

_MODEL_PRICING = {
    "claude-opus-4-6": {
        "input": 15.00, "output": 75.00,
        "cache_read": 1.50, "cache_write": 18.75,
        "context_window": 200_000, "extended_context": 1_000_000,
    },
    "claude-sonnet-4-6": {
        "input": 3.00, "output": 15.00,
        "cache_read": 0.30, "cache_write": 3.75,
        "context_window": 200_000, "extended_context": 1_000_000,
    },
    "claude-haiku-4-5": {
        "input": 0.80, "output": 4.00,
        "cache_read": 0.08, "cache_write": 1.00,
        "context_window": 200_000, "extended_context": 200_000,
    },
}
_DEFAULT_PRICING = {
    "input": 3.00, "output": 15.00,
    "cache_read": 0.30, "cache_write": 3.75,
    "context_window": 200_000, "extended_context": 200_000,
}


def _normalize_model(model_str: str) -> str:
    if not model_str:
        return ""
    m = model_str.lower()
    for key in _MODEL_PRICING:
        if key in m or key.replace("-", "") in m.replace("-", ""):
            return key
    if "opus" in m:
        return "claude-opus-4-6"
    if "sonnet" in m:
        return "claude-sonnet-4-6"
    if "haiku" in m:
        return "claude-haiku-4-5"
    return model_str


def _parse_usage(transcript_path: str) -> dict:
    totals = {
        "input_tokens": 0, "output_tokens": 0,
        "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0,
    }
    api_calls = 0
    models_seen: set[str] = set()
    peak_input = 0
    first_ts = None
    last_ts = None
    with open(transcript_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            ts = obj.get("timestamp")
            if ts and not first_ts:
                first_ts = ts
            if ts:
                last_ts = ts
            if obj.get("type") != "assistant":
                continue
            msg = obj.get("message", {})
            usage = msg.get("usage", {})
            if not usage:
                continue
            model = msg.get("model", "")
            if model:
                models_seen.add(model)
            api_calls += 1
            inp = usage.get("input_tokens", 0)
            out = usage.get("output_tokens", 0)
            cache_read = usage.get("cache_read_input_tokens", 0)
            cache_create = usage.get("cache_creation_input_tokens", 0)
            totals["input_tokens"] += inp
            totals["output_tokens"] += out
            totals["cache_read_input_tokens"] += cache_read
            totals["cache_creation_input_tokens"] += cache_create
            effective = inp + cache_read + cache_create
            if effective > peak_input:
                peak_input = effective
    primary_model = sorted(models_seen)[0] if models_seen else ""
    pricing = _MODEL_PRICING.get(_normalize_model(primary_model), _DEFAULT_PRICING)
    cost_in = (totals["input_tokens"] / 1_000_000) * pricing["input"]
    cost_out = (totals["output_tokens"] / 1_000_000) * pricing["output"]
    cost_cr = (totals["cache_read_input_tokens"] / 1_000_000) * pricing["cache_read"]
    cost_cc = (totals["cache_creation_input_tokens"] / 1_000_000) * pricing["cache_write"]
    cost_total = cost_in + cost_out + cost_cr + cost_cc
    context_limit = pricing["context_window"]
    if peak_input > context_limit:
        context_limit = pricing["extended_context"]
    context_pct = round(100 * peak_input / context_limit, 1) if context_limit else 0
    return {
        "model": primary_model,
        "model_key": _normalize_model(primary_model),
        "api_calls": api_calls,
        "tokens": {
            "input": totals["input_tokens"],
            "output": totals["output_tokens"],
            "cache_read": totals["cache_read_input_tokens"],
            "cache_creation": totals["cache_creation_input_tokens"],
            "total": sum(totals.values()),
        },
        "cost": {
            "input": round(cost_in, 4), "output": round(cost_out, 4),
            "cache_read": round(cost_cr, 4), "cache_creation": round(cost_cc, 4),
            "total": round(cost_total, 4),
        },
        "context": {
            "peak_tokens": peak_input,
            "window_limit": context_limit,
            "usage_pct": context_pct,
        },
        "timing": {"first_message": first_ts, "last_message": last_ts},
    }


def _render_usage_section(metrics: dict, agent_type: str) -> str:
    t = metrics["tokens"]
    c = metrics["cost"]
    ctx = metrics["context"]
    return "\n".join([
        "",
        "## Token Usage",
        "",
        f"Model: `{metrics['model']}` | API calls: {metrics['api_calls']}",
        "",
        "| Metric | Tokens | Cost (USD) |",
        "|--------|--------|------------|",
        f"| Input | {t['input']:,} | ${c['input']:.4f} |",
        f"| Output | {t['output']:,} | ${c['output']:.4f} |",
        f"| Cache Read | {t['cache_read']:,} | ${c['cache_read']:.4f} |",
        f"| Cache Creation | {t['cache_creation']:,} | ${c['cache_creation']:.4f} |",
        f"| **Total** | **{t['total']:,}** | **${c['total']:.4f}** |",
        "",
        f"Context: {ctx['peak_tokens']:,} / {ctx['window_limit']:,} ({ctx['usage_pct']}%)",
        "",
    ])


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

_PREFIX = {"generator": "gen", "evaluator": "eval"}


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0

    agent_type = event.get("agent_type", "")
    if agent_type not in _PREFIX:
        return 0
    transcript = event.get("agent_transcript_path", "")
    if not transcript or not Path(transcript).is_file():
        return 0

    project_dir = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    trace_dir = project_dir / "specs" / "_batch" / "_traces"
    trace_dir.mkdir(parents=True, exist_ok=True)

    context_file = trace_dir / "current-context.json"
    feature, round_int = "", 0
    if context_file.is_file():
        try:
            ctx = json.loads(context_file.read_text(encoding="utf-8"))
            feature = str(ctx.get("feature") or "")
            round_int = int(ctx.get("round") or 0)
        except (json.JSONDecodeError, OSError, ValueError):
            feature, round_int = "", 0

    prefix = _PREFIX[agent_type]
    trace = _parse_transcript(transcript)
    stats = _compute_stats(trace["steps"])

    if feature:
        out_md = trace_dir / f"{feature}-{prefix}-trace-R{round_int}.md"
        progress_tsv: Path | None = project_dir / "specs" / "_batch" / "progress.tsv"
        usage_json: Path | None = trace_dir / f"{feature}-{prefix}-usage-R{round_int}.json"
    else:
        ts = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        out_md = trace_dir / f"{agent_type}-{ts}.md"
        progress_tsv = None
        usage_json = None

    out_md.write_text(
        _render_trace_markdown(agent_type, feature or "PENDING", round_int, trace, stats),
        encoding="utf-8",
    )

    if progress_tsv is not None:
        try:
            _append_progress_row(progress_tsv, agent_type, feature, round_int,
                                 stats, str(project_dir))
        except OSError:
            pass

    if usage_json is not None:
        try:
            metrics = _parse_usage(transcript)
            metrics.update({
                "feature": feature, "round": round_int,
                "agent_type": agent_type,
                "extracted_at": _dt.datetime.now().isoformat(),
            })
            usage_json.write_text(
                json.dumps(metrics, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            with out_md.open("a", encoding="utf-8") as f:
                f.write(_render_usage_section(metrics, agent_type))
        except (OSError, KeyError, TypeError):
            pass
    else:
        sidecar = trace_dir / f"{agent_type}-latest.json"
        sidecar.write_text(
            json.dumps({
                "agent_type": agent_type,
                "timestamp": _dt.datetime.now().strftime("%Y%m%d-%H%M%S"),
                "session_id": event.get("session_id", ""),
                "trace_file": str(out_md),
            }, ensure_ascii=False),
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
