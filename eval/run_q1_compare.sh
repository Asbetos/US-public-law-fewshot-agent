#!/bin/bash
# The Q1 two-coder study, stage by stage. Every stage is resumable: re-running
# a labelling stage skips rows already done and retries rows that errored.
#
#   ./eval/run_q1_compare.sh sample        # draw the 3,000 sections (once; attaches final labels)
#   ./eval/run_q1_compare.sh final-labels  # re-read the final reconciled labels into the sample
#   ./eval/run_q1_compare.sh qwen          # main Qwen run + repair pass (vLLM must be up)
#   ./eval/run_q1_compare.sh qwen-flat     # 300-row prompt-form check
#   ./eval/run_q1_compare.sh claude-probe  # first 100 rows of the Claude run (usage, cost, timing)
#   ./eval/run_q1_compare.sh claude        # the full Claude run (resumes after the probe)
#   ./eval/run_q1_compare.sh claude-repeat # 100-row repeat for self-agreement
#   ./eval/run_q1_compare.sh compare       # statistics, two-coder sheet, disagreements, report
#   ./eval/run_q1_compare.sh dashboard     # self-contained HTML dashboard
#
# Claude route: with ANTHROPIC_API_KEY exported (or in $API_KEY_FILE, mode 600)
# the SDK bills the key - the Max plan's included monthly API credits; without
# it the subscription login is used and the runner paces itself on the limits.
set -euo pipefail
cd "$(dirname "$0")/.."

PY=/groups/brooksgrp/citizen_voice/workspace/.venv/bin/python
OUT=results/q1_panel3k
MODEL="${MODEL:-qwen3.6-27b-awq}"
BASE="${BASE:-http://127.0.0.1:8000/v1}"
CONC="${CONC:-8}"
CLAUDE_CONC="${CLAUDE_CONC:-2}"
API_KEY_FILE="${API_KEY_FILE:-${HOME:-/nonexistent}/.config/citizen_voice/anthropic_api_key}"
STAGE="${1:?stage required}"

qwen() {  # qwen <input> <output> [flags]
  local in=$1 out=$2; shift 2
  $PY eval/run_batch.py --question q1 --input-jsonl "$in" --output "$out" \
      --model "$MODEL" --base-url "$BASE" --concurrency "$CONC" \
      --confidence --logprobs --max-section-chars 0 "$@"
}

claude() {  # claude <input> <output> [flags]
  local in=$1 out=$2; shift 2
  if [[ -z "${ANTHROPIC_API_KEY:-}" && -r "$API_KEY_FILE" ]]; then
    export ANTHROPIC_API_KEY="$(tr -d '[:space:]' < "$API_KEY_FILE")"
  fi
  env -u CLAUDECODE $PY eval/run_claude.py --input-jsonl "$in" --output "$out" \
      --concurrency "$CLAUDE_CONC" "$@"
}

case "$STAGE" in
  sample)        $PY eval/make_panel_sample.py ;;
  final-labels)  $PY eval/final_labels.py ;;
  qwen)          qwen $OUT/sample.jsonl $OUT/qwen_raw.jsonl
                 echo "=== repair pass (retries errored rows with more headroom) ==="
                 qwen $OUT/sample.jsonl $OUT/qwen_raw.jsonl --max-tokens 1536 ;;
  qwen-flat)     qwen $OUT/sample_flat300.jsonl $OUT/qwen_flat300.jsonl --flat
                 qwen $OUT/sample_flat300.jsonl $OUT/qwen_flat300.jsonl --flat --max-tokens 1536 ;;
  claude-probe)  claude $OUT/sample.jsonl $OUT/claude_raw.jsonl --limit 100 ;;
  claude)        claude $OUT/sample.jsonl $OUT/claude_raw.jsonl ;;
  claude-repeat) claude $OUT/sample_repeat100.jsonl $OUT/claude_repeat.jsonl ;;
  compare)       $PY eval/compare_models.py ;;
  dashboard)     $PY eval/compare_dashboard.py ;;
  *) echo "unknown stage: $STAGE" >&2; exit 2 ;;
esac
