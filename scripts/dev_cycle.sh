#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

git pull --rebase
echo "Modify files, then run:"
echo "  git add <files>"
echo "  git commit -m \"...\""
echo "  make smoke"
echo "  git push"
