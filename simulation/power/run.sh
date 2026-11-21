#!/usr/bin/env bash
# Run all power-stage simulations (ngspice) and regenerate simulation/power/results/.
# Requirements: ngspice >= 40 on PATH (apt install ngspice) and either uv
# (dependencies resolved from the script header) or python3 with numpy + matplotlib.
# Usage: simulation/power/run.sh [run.py options, e.g. --force, --only 01_]
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if ! command -v ngspice >/dev/null 2>&1; then
  echo "ngspice not found – install it first (e.g. sudo apt install ngspice)" >&2
  exit 2
fi
ngspice -v 2>/dev/null | grep -m1 -o 'ngspice-[0-9.]*' || true

if command -v uv >/dev/null 2>&1 && [[ "${NO_UV:-}" != "1" ]]; then
  exec uv run --script "$here/run.py" "$@"
fi
exec python3 "$here/run.py" "$@"
