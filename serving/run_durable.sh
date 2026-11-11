#!/bin/bash
# Launch the labelling run so it outlives the SSH session that started it.
#
# nohup + & is usually enough here (logind's KillUserProcesses is false on this
# box, so the login session scope is not torn down on logout), but that is a
# host policy that can change under you. tmux is the belt-and-braces version and,
# more usefully, gives you something to attach to and watch.
#
#   ./serving/run_durable.sh            # start (or reattach to) the run
#   tmux attach -t fewshot              # watch it
#   Ctrl-b d                            # detach, leaving it running
#   tmux kill-session -t fewshot        # stop it
#
# Every stage is resumable, so re-running this after any interruption continues
# from the last completed row rather than starting over.
set -euo pipefail
cd "$(dirname "$0")/.."
SESSION="${SESSION:-fewshot}"
STAGE="${1:-test}"

if tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "session '$SESSION' already exists - attach with: tmux attach -t $SESSION"
  exit 0
fi

tmux new-session -d -s "$SESSION" -n run \
  "./eval/run_all.sh $STAGE 2>&1 | tee -a /groups/brooksgrp/citizen_voice/models/fullrun.log"
echo "started detached tmux session '$SESSION' (stage: $STAGE)"
echo "  watch:   tmux attach -t $SESSION      (Ctrl-b d to detach)"
echo "  or tail: tail -f /groups/brooksgrp/citizen_voice/models/fullrun.log"
