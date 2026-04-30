#!/usr/bin/env bash
# PostToolUse hook — captures evidence of self-verify script invocations
# across prd / plan / execution-loop.
#
# Purpose: every orchestrator/agent MUST invoke the computational sensors
# (plan_lint / lift_capabilities / plan_validator / gen_local_gate /
# ac_coverage / quality-gate). This hook writes an unforgeable JSON record
# of each invocation so we can audit that the required sensors actually ran.
#
# Trust model: writing to .traces/*.evidence.json is blocked for all agents
# by guard-evidence-paths.sh. Only this hook (a Claude Code runtime-triggered
# shell exec, outside the agent tool layer) can produce evidence. Therefore
# evidence is unforgeable by the agent.
#
# Input:  JSON on stdin (Claude Code PostToolUse schema) for tool_name=Bash.
# Output: docs/progress/.traces/{scope}-{agent}-{script}.evidence.json
#   Feature scope (reads current-context.json): {F}-R{R}-{agent}-{script}.evidence.json
#   Plan scope (orchestrator / planner, no feature): PLAN-{slug}-{agent}-{script}-{ts}.evidence.json
# All emitted files are chmod 444.

set -u

input=$(cat)
tool=$(printf '%s' "$input" | jq -r '.tool_name // ""')
[[ "$tool" != "Bash" ]] && exit 0

command_line=$(printf '%s' "$input" | jq -r '.tool_input.command // ""')

# Detect whitelisted self-verify script by substring. Extend here when new
# sensors join the harness. Unknown commands → silent exit 0.
script=""
case "$command_line" in
  *plan_lint.py*)         script="plan_lint" ;;
  *lift_capabilities.py*) script="lift_capabilities" ;;
  *plan_validator.py*)    script="plan_validator" ;;
  *gen_local_gate.sh*)    script="gen_local_gate" ;;
  *ac_coverage.py*)       script="ac_coverage" ;;
  *quality-gate.sh*)      script="quality_gate" ;;
  *) exit 0 ;;
esac

project_dir="${CLAUDE_PROJECT_DIR:-$(pwd)}"
evidence_dir="$project_dir/docs/progress/.traces"
mkdir -p "$evidence_dir"

ts_iso=$(date -u +%Y-%m-%dT%H:%M:%SZ)
ts_file=$(date -u +%Y%m%dT%H%M%SZ)
agent=$(printf '%s' "$input" | jq -r '.agent_type // ""')
[[ -z "$agent" ]] && agent="orchestrator"

# Read feature-scope context (execution-loop writes this before each phase).
feature=""
round=""
ctx="$evidence_dir/current-context.json"
if [[ -f "$ctx" ]]; then
  feature=$(jq -r '.feature // ""' "$ctx" 2>/dev/null)
  round=$(jq -r '.round // ""' "$ctx" 2>/dev/null)
fi

# Determine filename + scope tag.
if [[ -n "$feature" && -n "$round" ]]; then
  scope="feature"
  evidence_path="$evidence_dir/${feature}-R${round}-${agent}-${script}.evidence.json"
else
  # Plan-scope: derive batch slug from plan.md, else fall back to "batch".
  slug=""
  if [[ -f "$project_dir/specs/_batch/plan.md" ]]; then
    slug=$(grep -m1 -E '^- Slug:' "$project_dir/specs/_batch/plan.md" \
            | sed -E 's/^- Slug:\s*//' | tr -cd 'a-zA-Z0-9_-' )
  fi
  [[ -z "$slug" ]] && slug="batch"
  scope="plan"
  evidence_path="$evidence_dir/PLAN-${slug}-${agent}-${script}-${ts_file}.evidence.json"
fi

# Extract exit code + stdout. Claude Code PostToolUse Bash schema varies;
# try the most common fields in order, default empty.
tool_response_raw=$(printf '%s' "$input" | jq -c '.tool_response // {}')
exit_code=$(printf '%s' "$tool_response_raw" | jq -r '
  .exit_code // .exitCode // .returncode // .code // 0
' 2>/dev/null)
[[ -z "$exit_code" || "$exit_code" == "null" ]] && exit_code=0

stdout_content=$(printf '%s' "$tool_response_raw" | jq -r '
  if type == "string" then .
  elif type == "object" then (.stdout // .output // .content // "")
  else "" end
' 2>/dev/null)

stderr_content=$(printf '%s' "$tool_response_raw" | jq -r '.stderr // ""' 2>/dev/null)

# Parse canonical "status":"PASS"|"FAIL" from stdout JSON if applicable.
# Covers plan_lint, plan_validator, ac_coverage which emit JSON first line.
status_field=""
status_field=$(printf '%s' "$stdout_content" | head -100 | jq -r '.status // ""' 2>/dev/null)
[[ "$status_field" == "null" ]] && status_field=""

git_head=$(git -C "$project_dir" rev-parse HEAD 2>/dev/null || echo "")
git_branch=$(git -C "$project_dir" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")

# Replace existing evidence file if any (immutable once written).
if [[ -f "$evidence_path" ]]; then
  chmod 644 "$evidence_path" 2>/dev/null || true
  rm -f "$evidence_path"
fi

# Cap stdout capture at ~64KB to avoid runaway evidence files on chatty scripts.
max_bytes=65536
stdout_captured=$(printf '%s' "$stdout_content" | head -c "$max_bytes")
truncated=false
if [[ $(printf '%s' "$stdout_content" | wc -c | tr -d ' ') -gt $max_bytes ]]; then
  truncated=true
fi

jq -n \
  --arg script      "$script" \
  --arg agent       "$agent" \
  --arg scope       "$scope" \
  --arg feature     "$feature" \
  --arg round       "$round" \
  --arg ts          "$ts_iso" \
  --arg head        "$git_head" \
  --arg branch      "$git_branch" \
  --arg cmd         "$command_line" \
  --argjson exit_code $(printf '%s' "$exit_code" | grep -oE '^-?[0-9]+' || echo 0) \
  --arg stdout      "$stdout_captured" \
  --arg stderr      "$stderr_content" \
  --arg status      "$status_field" \
  --argjson truncated $([[ "$truncated" == true ]] && echo true || echo false) \
  '{
    schemaVersion: 1,
    script: $script,
    agent: $agent,
    scope: $scope,
    feature: (if $feature == "" then null else $feature end),
    round: (if $round == "" then null else ($round | tonumber? // null) end),
    timestamp: $ts,
    git: { head: $head, branch: $branch },
    command: $cmd,
    result: {
      exitCode: $exit_code,
      status: (if $status == "" then null else $status end),
      stdout: $stdout,
      stderr: $stderr,
      stdoutTruncated: $truncated
    }
  }' > "$evidence_path"

chmod 444 "$evidence_path" 2>/dev/null || true
exit 0
