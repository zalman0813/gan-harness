#!/bin/bash
# extract-trace.sh — SubagentStop hook
#
# Reads the subagent's JSONL transcript and extracts a structured
# Markdown trace file. Only processes generator and evaluator agents.
#
# Called by Claude Code's SubagentStop hook with JSON on stdin containing:
#   agent_type, agent_transcript_path, session_id, etc.
#
# The trace file is written to docs/progress/.traces/ and the harness-loop
# orchestrator is responsible for copying it to the correct F{NN}-*-trace-R{N}.md
# filename (since the hook doesn't know the feature ID or round number).

set -euo pipefail

# Read JSON input from stdin
INPUT=$(cat)

AGENT_TYPE=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('agent_type',''))" 2>/dev/null || echo "")
TRANSCRIPT=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('agent_transcript_path',''))" 2>/dev/null || echo "")
SESSION_ID=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('session_id',''))" 2>/dev/null || echo "")

# Only process generator, evaluator, and reflector agents
case "$AGENT_TYPE" in
  generator|evaluator|reflector) ;;
  *) exit 0 ;;
esac

# Validate transcript exists
if [ -z "$TRANSCRIPT" ] || [ ! -f "$TRANSCRIPT" ]; then
  exit 0
fi

# Read feature/round context written by harness-loop before spawning the agent
FEATURE=""
ROUND="0"
CONTEXT_FILE="docs/progress/.traces/current-context.json"
if [ -f "$CONTEXT_FILE" ]; then
  FEATURE=$(python3 -c "import json; print(json.load(open('$CONTEXT_FILE'))['feature'])" 2>/dev/null || echo "")
  ROUND=$(python3 -c "import json; print(json.load(open('$CONTEXT_FILE'))['round'])" 2>/dev/null || echo "0")
fi

# If context is available, write directly to final path — no rename needed
if [ -n "$FEATURE" ] && [ "$FEATURE" != "" ]; then
  PREFIX=$(echo "$AGENT_TYPE" | sed 's/generator/gen/;s/evaluator/eval/;s/reflector/reflect/')
  OUTPUT_FILE="docs/progress/${FEATURE}-${PREFIX}-trace-R${ROUND}.md"

  python3 .claude/hooks/parse-trace.py \
    --transcript "$TRANSCRIPT" \
    --agent-type "$AGENT_TYPE" \
    --feature "$FEATURE" \
    --round "$ROUND" \
    --output "$OUTPUT_FILE" 2>/dev/null || exit 0

  # Extract token usage metrics and append to trace
  USAGE_JSON="docs/progress/.traces/${FEATURE}-${PREFIX}-usage-R${ROUND}.json"
  python3 .claude/hooks/parse-usage.py \
    --transcript "$TRANSCRIPT" \
    --agent-type "$AGENT_TYPE" \
    --feature "$FEATURE" \
    --round "$ROUND" \
    --output-json "$USAGE_JSON" \
    --output-md "$OUTPUT_FILE" 2>/dev/null || true
else
  # Fallback: no context (manual agent spawn outside harness-loop)
  TRACE_DIR="docs/progress/.traces"
  mkdir -p "$TRACE_DIR"
  TIMESTAMP=$(date +%Y%m%d-%H%M%S)
  OUTPUT_FILE="$TRACE_DIR/${AGENT_TYPE}-${TIMESTAMP}.md"

  python3 .claude/hooks/parse-trace.py \
    --transcript "$TRANSCRIPT" \
    --agent-type "$AGENT_TYPE" \
    --feature "PENDING" \
    --round 0 \
    --output "$OUTPUT_FILE" 2>/dev/null || exit 0

  echo "{\"agent_type\": \"$AGENT_TYPE\", \"timestamp\": \"$TIMESTAMP\", \"session_id\": \"$SESSION_ID\", \"trace_file\": \"$OUTPUT_FILE\"}" \
    > "$TRACE_DIR/${AGENT_TYPE}-latest.json"

  # Extract token usage metrics for fallback case too
  USAGE_JSON="$TRACE_DIR/${AGENT_TYPE}-usage-${TIMESTAMP}.json"
  python3 .claude/hooks/parse-usage.py \
    --transcript "$TRANSCRIPT" \
    --agent-type "$AGENT_TYPE" \
    --feature "PENDING" \
    --round 0 \
    --output-json "$USAGE_JSON" \
    --output-md "$OUTPUT_FILE" 2>/dev/null || true
fi
