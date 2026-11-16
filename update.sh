#!/usr/bin/env sh
# AKA.CRISTI Skills — macOS / Linux one-command updater.
# Run from an existing, reviewed checkout: sh ./update.sh
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
if command -v python3 >/dev/null 2>&1; then
  exec python3 -m tools.update --interactive "$@"
fi
printf '%s\n' '[CHEF UPDATE][BLOCKED] Python 3.11+ is required.' >&2
exit 1
