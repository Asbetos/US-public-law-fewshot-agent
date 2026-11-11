#!/bin/bash
# Full experiment. Every stage is resumable: re-running skips rows already
# labelled in the output file, so an interrupted run picks up where it stopped.
#
# Order is deliberate - the two test runs are the deliverable and go first. The
# thinking-mode A/B runs last and only needs the thinking-ON side, because the
# calibration rows are a subset of the test set, so the main run already contains
# the thinking-OFF control for exactly those rows.
set -euo pipefail
cd "$(dirname "$0")/.."

PY=/groups/brooksgrp/citizen_voice/workspace/.venv/bin/python
MODEL="${MODEL:-qwen3.6-27b-awq}"
BASE="${BASE:-http://127.0.0.1:8000/v1}"
CONC="${CONC:-8}"
STAGE="${1:-all}"

run() {  # run <question> <input> <output> [extra flags]
  local q=$1 in=$2 out=$3; shift 3
  echo "=== $q -> $out ==="
  $PY eval/run_batch.py --question "$q" --input-jsonl "$in" --output "$out" \
      --model "$MODEL" --base-url "$BASE" --concurrency "$CONC" "$@"
}

if [[ "$STAGE" == "test" || "$STAGE" == "all" ]]; then
  run q6 results/q6/test.jsonl results/q6/raw.jsonl
  run q1 results/q1/test.jsonl results/q1/raw.jsonl
  # Repair pass: resume treats an errored row as not-done, so running each
  # question again retries only the failures. Both observed failure modes need
  # more headroom than the main run's defaults:
  #   - context overflow on the densest sections  -> smaller section clip
  #   - a reply that reasons in circles past 768 tokens without closing its
  #     json block (1 row in 253; p90 is 285 tokens, so this is not systemic
  #     and raising the cap for everyone would only widen the tail)
  # 18,000 chars + 1,536 out still fits: 13,975 prefix + 18,000/1.09 + 1,536 < 32,768.
  echo "=== repair pass ==="
  REPAIR=(--max-tokens 1536 --max-section-chars 18000)
  run q6 results/q6/test.jsonl results/q6/raw.jsonl "${REPAIR[@]}"
  run q1 results/q1/test.jsonl results/q1/raw.jsonl "${REPAIR[@]}"
fi

if [[ "$STAGE" == "thinking" || "$STAGE" == "all" ]]; then
  # Q6 only: Q1's calibration slice holds just 6 positives, too few to compare on.
  run q6 results/q6/calibration.jsonl results/q6/calibration_think.jsonl --thinking --max-tokens 3072
fi

echo "=== scoring ==="
$PY eval/write_run_meta.py
$PY eval/collect_infra.py
$PY eval/score.py
$PY eval/compare_thinking.py || true
$PY eval/dashboard.py
