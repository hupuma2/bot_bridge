#!/usr/bin/env bash
set -euo pipefail

BASE="$HOME/.openclaw/bot_bridge"

echo "=== digest classify patch ==="
rg -n 'dlp_blocked_or_scan_fail|policy_block|classify_send_error' "$BASE/scripts/digest_worker.py"
python3 "$BASE/tests/check_digest_policy_block.py"

echo
echo "=== py_compile ==="
python3 -m py_compile "$BASE/scripts/digest_worker.py"
echo "OK: py_compile"

echo
echo "=== queue counts ==="
QDIR="$BASE/data/queue"
if [[ -d "$QDIR" ]]; then
  q_count=$(find "$QDIR" -maxdepth 1 -type f -name '*.json' -not -name '*.meta.json' | wc -l | tr -d ' ')
  m_count=$(find "$QDIR" -maxdepth 1 -type f -name '*.meta.json' | wc -l | tr -d ' ')
  echo "queue files: $q_count"
  echo "queue meta : $m_count"
else
  echo "queue dir missing: $QDIR"
fi

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
