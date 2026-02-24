#!/usr/bin/env bash
set -euo pipefail

BASE="$(cd "$(dirname "$0")/.." && pwd)"
cd "$BASE"

echo "=== digest classify patch ==="
rg -n 'def classify_send_error|dlp_blocked_or_scan_fail|policy_block' scripts/digest_worker.py || true

python3 tests/check_digest_policy_block.py

echo
echo "=== py_compile ==="
python3 -m py_compile scripts/digest_worker.py
echo "OK: py_compile"

echo
echo "=== queue counts ==="
QDIR="$BASE/data/queue"
MDIR="$BASE/data/queue_meta"
qcount=0
mcount=0
[[ -d "$QDIR" ]] && qcount="$(find "$QDIR" -maxdepth 1 -type f | wc -l | tr -d ' ')"
[[ -d "$MDIR" ]] && mcount="$(find "$MDIR" -maxdepth 1 -type f | wc -l | tr -d ' ')"
echo "queue files: $qcount"
echo "queue meta : $mcount"

echo
echo "=== quarantine list ==="
QRT="$BASE/data/quarantine"
if [[ -d "$QRT" ]]; then
  find "$QRT" -maxdepth 1 -type f | sort || true
else
  echo "quarantine dir missing: $QRT"
fi

echo
echo "=== recent digest events ==="
AUD="$BASE/data/audit/audit-$(date +%Y%m%d).jsonl"
if [[ -f "$AUD" ]]; then
  tail -n 200 "$AUD" | rg 'digest_quarantined|policy_block:retry_exceeded|digest_sent' || true
else
  echo "audit file missing: $AUD"
fi

echo
echo "OK"
