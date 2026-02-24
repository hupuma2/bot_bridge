import importlib.util
from pathlib import Path

P = Path.home() / ".openclaw/bot_bridge/scripts/digest_worker.py"
spec = importlib.util.spec_from_file_location("digest_worker", P)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

def test_classify_send_error_policy_block():
    msg = "ERROR: DLP_BLOCKED_OR_SCAN_FAIL: ... exit status 3."
    assert mod.classify_send_error(msg) == "policy_block"

def test_retry_limit_policy_block():
    assert mod.retry_limit_for("policy_block") == 0
