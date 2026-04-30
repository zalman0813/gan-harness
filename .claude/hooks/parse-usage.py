#!/usr/bin/env python3
"""Extract token usage, cost, and context % from a Claude Code subagent transcript.

Parses the JSONL transcript produced by generator/evaluator agents and
computes aggregate token metrics with cost estimation.

Usage:
    python3 parse-usage.py --transcript /path/to/agent.jsonl \
                           --agent-type generator \
                           --feature F03 \
                           --round 1 \
                           [--output-json /path/to/usage.json] \
                           [--output-md /path/to/trace.md]

When --output-md is given, appends a "## Token Usage" section to the file.
When --output-json is given, writes a structured JSON metrics file.
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# Pricing per million tokens (USD) — April 2026
MODEL_PRICING = {
    "claude-opus-4-6": {
        "input": 15.00,
        "output": 75.00,
        "cache_read": 1.50,
        "cache_write": 18.75,
        "context_window": 200_000,
        "extended_context": 1_000_000,
    },
    "claude-sonnet-4-6": {
        "input": 3.00,
        "output": 15.00,
        "cache_read": 0.30,
        "cache_write": 3.75,
        "context_window": 200_000,
        "extended_context": 1_000_000,
    },
    "claude-haiku-4-5": {
        "input": 0.80,
        "output": 4.00,
        "cache_read": 0.08,
        "cache_write": 1.00,
        "context_window": 200_000,
        "extended_context": 200_000,
    },
}

# Fallback for unknown models
DEFAULT_PRICING = {
    "input": 3.00,
    "output": 15.00,
    "cache_read": 0.30,
    "cache_write": 3.75,
    "context_window": 200_000,
    "extended_context": 200_000,
}


def normalize_model(model_str: str) -> str:
    """Normalize model string to pricing key."""
    if not model_str:
        return ""
    m = model_str.lower()
    for key in MODEL_PRICING:
        # Match partial names like "claude-sonnet-4-6-20260401"
        if key in m or key.replace("-", "") in m.replace("-", ""):
            return key
    # Try common patterns
    if "opus" in m:
        return "claude-opus-4-6"
    if "sonnet" in m:
        return "claude-sonnet-4-6"
    if "haiku" in m:
        return "claude-haiku-4-5"
    return model_str


def parse_usage(transcript_path: str) -> dict:
    """Parse JSONL transcript and aggregate token usage."""
    totals = {
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_read_input_tokens": 0,
        "cache_creation_input_tokens": 0,
    }
    api_calls = 0
    models_seen = set()
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

            # Only process assistant messages with usage
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

            # Track peak context usage (input + cache_read is the effective
            # context size for that API call)
            effective_input = inp + cache_read + cache_create
            if effective_input > peak_input:
                peak_input = effective_input

    # Determine primary model
    primary_model = ""
    if models_seen:
        primary_model = sorted(models_seen, key=lambda m: m)[0]

    model_key = normalize_model(primary_model)
    pricing = MODEL_PRICING.get(model_key, DEFAULT_PRICING)

    # Cost calculation
    total_input = totals["input_tokens"]
    total_output = totals["output_tokens"]
    total_cache_read = totals["cache_read_input_tokens"]
    total_cache_create = totals["cache_creation_input_tokens"]

    cost_input = (total_input / 1_000_000) * pricing["input"]
    cost_output = (total_output / 1_000_000) * pricing["output"]
    cost_cache_read = (total_cache_read / 1_000_000) * pricing["cache_read"]
    cost_cache_create = (total_cache_create / 1_000_000) * pricing["cache_write"]
    cost_total = cost_input + cost_output + cost_cache_read + cost_cache_create

    # Context percentage (peak input relative to context window)
    # Use extended context if peak exceeds standard window
    context_limit = pricing["context_window"]
    if peak_input > context_limit:
        context_limit = pricing["extended_context"]
    context_pct = round(100 * peak_input / context_limit, 1) if context_limit else 0

    return {
        "model": primary_model,
        "model_key": model_key,
        "api_calls": api_calls,
        "tokens": {
            "input": total_input,
            "output": total_output,
            "cache_read": total_cache_read,
            "cache_creation": total_cache_create,
            "total": (
                total_input + total_output + total_cache_read + total_cache_create
            ),
        },
        "cost": {
            "input": round(cost_input, 4),
            "output": round(cost_output, 4),
            "cache_read": round(cost_cache_read, 4),
            "cache_creation": round(cost_cache_create, 4),
            "total": round(cost_total, 4),
        },
        "context": {
            "peak_tokens": peak_input,
            "window_limit": context_limit,
            "usage_pct": context_pct,
        },
        "timing": {
            "first_message": first_ts,
            "last_message": last_ts,
        },
    }


def render_markdown_section(metrics: dict, agent_type: str) -> str:
    """Render token usage as a Markdown section."""
    t = metrics["tokens"]
    c = metrics["cost"]
    ctx = metrics["context"]
    label = "Generator" if agent_type == "generator" else "Evaluator"

    lines = [
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
        f"Context: {ctx['peak_tokens']:,} / {ctx['window_limit']:,} "
        f"({ctx['usage_pct']}%)",
        "",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Extract token usage from Claude Code subagent transcript"
    )
    parser.add_argument(
        "--transcript", required=True, help="Path to JSONL transcript"
    )
    parser.add_argument(
        "--agent-type",
        required=True,
        choices=["generator", "evaluator"],
    )
    parser.add_argument("--feature", required=True, help="Feature ID")
    parser.add_argument("--round", required=True, type=int, help="Round number")
    parser.add_argument(
        "--output-json", help="Path for JSON metrics output"
    )
    parser.add_argument(
        "--output-md", help="Markdown file to append usage section to"
    )
    args = parser.parse_args()

    if not Path(args.transcript).exists():
        print(f"Transcript not found: {args.transcript}", file=sys.stderr)
        sys.exit(1)

    metrics = parse_usage(args.transcript)
    metrics["feature"] = args.feature
    metrics["round"] = args.round
    metrics["agent_type"] = args.agent_type
    metrics["extracted_at"] = datetime.now().isoformat()

    # Write JSON metrics
    if args.output_json:
        Path(args.output_json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output_json).write_text(
            json.dumps(metrics, indent=2, ensure_ascii=False)
        )
        print(f"Usage JSON: {args.output_json}")

    # Append to trace Markdown
    if args.output_md and Path(args.output_md).exists():
        md_section = render_markdown_section(metrics, args.agent_type)
        with open(args.output_md, "a") as f:
            f.write(md_section)
        print(f"Usage appended to: {args.output_md}")

    # Always print summary to stdout
    t = metrics["tokens"]
    c = metrics["cost"]
    ctx = metrics["context"]
    print(
        f"{args.agent_type} R{args.round}: "
        f"{t['total']:,} tokens, ${c['total']:.4f}, "
        f"context {ctx['usage_pct']}%"
    )


if __name__ == "__main__":
    main()
