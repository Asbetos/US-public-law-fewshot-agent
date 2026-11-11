#!/bin/bash
# Start the local dashboard viewer (http://localhost:3000).
# Reads results/ live, so a browser refresh shows the current numbers.
set -euo pipefail
cd "$(dirname "$0")/../dashboard-app"
[ -d node_modules ] || npm install --no-audit --no-fund
exec npm run dev
