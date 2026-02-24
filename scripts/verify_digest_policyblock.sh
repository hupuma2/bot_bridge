#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

python3 tests/check_digest_policy_block.py
python3 -m py_compile scripts/digest_worker.py

echo "OK: digest policy_block baseline verified"
