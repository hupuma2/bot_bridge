# bot_bridge

Local bot bridge runtime and scripts.

## Stable baseline
- Tag: `v0.1.1-digest-policyblock-verify`
- DLP scan failures are classified as `policy_block`
- `policy_block` retries disabled (`retry_limit = 0`)
- Repo-local baseline verify script added: `scripts/verify_digest_policyblock.sh`

## Quick checks

### 1) Repo-local baseline verify (preferred)
./scripts/verify_digest_policyblock.sh

### 2) Shell helper (depends on ~/.zshrc)
oc-test-digest-classify

### 3) Fallback direct regression check
python3 tests/check_digest_policy_block.py

### 4) Python syntax check
python3 -m py_compile scripts/digest_worker.py

## Key files
- `scripts/digest_worker.py`
- `tests/test_digest_worker_error_classify.py`
- `tests/check_digest_policy_block.py`
- `scripts/verify_digest_policyblock.sh`

## Relevant commits
- `4d1cf3e` digest: classify DLP scan failures as policy_block and disable retries
- `02ba8ce` chore: add repo-local baseline verification script

## Notes
- Runtime data/logs/tmp are local artifacts and ignored by `.gitignore`
- Shell helpers depend on local `~/.zshrc`
