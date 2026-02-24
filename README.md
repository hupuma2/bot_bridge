# bot_bridge

Local bot bridge runtime and scripts.

## Stable baseline
- Tag: `v0.1.0-digest-policyblock`
- DLP scan failures are classified as `policy_block`
- `policy_block` retries disabled (`retry_limit = 0`)
- Minimal release healthcheck restored

## Quick checks

### 1) Digest classify regression (preferred)
oc-test-digest-classify

### 2) Digest classify regression (fallback direct)
python3 tests/check_digest_policy_block.py

### 3) Python syntax check
python3 -m py_compile scripts/digest_worker.py

### 4) Release healthcheck
./scripts/release_healthcheck.sh

## Key files
- `scripts/digest_worker.py`
- `tests/test_digest_worker_error_classify.py`
- `tests/check_digest_policy_block.py`
- `scripts/release_healthcheck.sh`

## Relevant commits
- `4d1cf3e` digest: classify DLP scan failures as policy_block and disable retries
- `0dbb8e6` chore: restore minimal release healthcheck script

## Notes
- Runtime data/logs/tmp are local artifacts and ignored by `.gitignore`
- Shell helpers depend on your local `~/.zshrc` configuration (e.g. `oc-test-digest-classify`)
