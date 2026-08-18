#!/usr/bin/env bash
# Run once after cloning:  bash scripts/install-hooks.sh
set -euo pipefail
root=$(git rev-parse --show-toplevel)
install -m 755 "$root/scripts/pre-commit" "$root/.git/hooks/pre-commit"
echo "installed .git/hooks/pre-commit"
