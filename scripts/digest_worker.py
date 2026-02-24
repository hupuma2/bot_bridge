#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys
import shutil

BASE = Path.home() / ".openclaw" / "bot_bridge"
QUEUE_DIR = BASE / "data" / "queue"
SESS_DIR = BASE / "data" / "sessions"
SUM_DIR = BASE / "data" / "summaries"
AUDIT_DIR = BASE / "data" / "audit"
SMTP = BASE / "scripts" / "smtp_sender.py"
DLP_SCAN = BASE / "security" / "bin" / "dlp_scan.py"
QUAR_DIR = BASE / "data" / "quarantine"

def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def append_audit(event_type: str, payload: dict):
    p = AUDIT_DIR / f"audit-{datetime.now().strftime('%Y%m%d')}.jsonl"
    rec = {"ts": now_iso(), "event": event_type, **payload}
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def classify_send_error(errmsg: str) -> str:
    t = (errmsg or "").lower()
    if "invalidsecondfactor" in t or "application-specific password required" in t:
        return "auth_failure"
    if "badcredentials" in t or "username and password not accepted" in t:
        return "auth_failure"
    if "keychain" in t and ("not found" in t or "could not be found" in t):
        return "credential_missing"
    if any(x in t for x in [
        "timeout", "temporarily unavailable", "connection reset",
        "broken pipe", "try again later", " 421 ", " 450 ", " 451 ", " 452 "
    ]):
        return "transient"
    if "dlp_blocked_or_scan_fail" in (errmsg or "").lower():
        return "policy_block"

    return "unknown"

def retry_limit_for(kind: str) -> int:
    if kind == "auth_failure":
        return 1
    if kind == "credential_missing":
        return 0
    if kind == "transient":
        return 3
    if kind == "policy_block":
        return 0

    return 2

def queue_meta_path(qpath: Path) -> Path:
    return qpath.with_suffix(qpath.suffix + ".meta.json")

def load_queue_meta(qpath: Path) -> dict:
    mp = queue_meta_path(qpath)
    if mp.exists():
        try:
            return json.loads(mp.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"retry_count": 0, "last_error_kind": None}

def save_queue_meta(qpath: Path, meta: dict):
    mp = queue_meta_path(qpath)
    mp.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

def quarantine_queue_file(qpath: Path, reason: str, errmsg: str):
    QUAR_DIR.mkdir(parents=True, exist_ok=True)
    dst = QUAR_DIR / qpath.name
    shutil.move(str(qpath), str(dst))
    mp = queue_meta_path(qpath)
    if mp.exists():
        shutil.move(str(mp), str(QUAR_DIR / mp.name))
    append_audit("digest_quarantined", {
        "queue_file": qpath.name,
        "reason": reason,
        "err": (errmsg or "")[:1000]
    })

def summarize_session(sess: dict) -> dict:
    msgs = sess.get("messages", [])
    user_msgs = [m for m in msgs if m.get("role") == "user"]
    bot_msgs = [m for m in msgs if m.get("role") != "user"]

    last_user = user_msgs[-1]["text"][:500] if user_msgs else ""
    commands = []
    for m in msgs:
        t = m.get("text","")
        if t.startswith("/") or t in ("status","gateway_listener","host_health","launchd_gateway","gateway_logs","bootcheck_logs"):
            commands.append(t[:120])

    summary = {
        "session_id": sess["id"],
        "channel": sess["channel"],
        "user_id": sess["user_id"],
        "created_at": sess.get("created_at"),
        "ended_at": sess.get("ended_at", sess.get("updated_at")),
        "end_reason": sess.get("end_reason", "unknown"),
        "message_count": sess.get("message_count", len(msgs)),
        "highlights": [
            f"Session ended by: {sess.get('end_reason', 'unknown')}",
            f"User messages: {len(user_msgs)}",
            f"Bot messages: {len(bot_msgs)}",
            f"Last user message: {last_user}" if last_user else "No user message"
        ],
        "commands_seen": commands[:20]
    }
    return summary

def format_email(summary: dict) -> str:
    lines = []
    lines.append("OpenClaw Bot Session Summary")
    lines.append("=" * 32)
    lines.append(f"Session ID: {summary['session_id']}")
    lines.append(f"Channel: {summary['channel']}")
    lines.append(f"User: {summary['user_id']}")
    lines.append(f"Created: {summary['created_at']}")
    lines.append(f"Ended: {summary['ended_at']}")
    lines.append(f"End reason: {summary['end_reason']}")
    lines.append(f"Message count: {summary['message_count']}")
    lines.append("")
    lines.append("Highlights:")
    for h in summary.get("highlights", []):
        lines.append(f"- {h}")
    if summary.get("commands_seen"):
        lines.append("")
        lines.append("Commands seen:")
        for c in summary["commands_seen"]:
            lines.append(f"- {c}")
    return "\n".join(lines) + "\n"

def process_one(qpath: Path):
    q = json.loads(qpath.read_text(encoding="utf-8"))
    if q.get("type") != "session_summary":
        return False

    sp = SESS_DIR / f"{q['session_id']}.json"
    if not sp.exists():
        append_audit("digest_skip_missing_session", {"queue_file": qpath.name, "session_id": q["session_id"]})
        q.unlink(missing_ok=True)
        return True

    sess = json.loads(sp.read_text(encoding="utf-8"))
    summary = summarize_session(sess)

    SUM_DIR.mkdir(parents=True, exist_ok=True)
    outp = SUM_DIR / f"{q['session_id']}.json"
    outp.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    body = format_email(summary)
    body_file = BASE / "tmp" / f"digest-{q['session_id']}.txt"
    body_file.parent.mkdir(parents=True, exist_ok=True)
    body_file.write_text(body, encoding="utf-8")

    subject = f"[OpenClaw Digest] {summary['channel']} session {summary['session_id']} ({summary['end_reason']})"

    # DLP scan before SMTP send
    try:
        _scan_input = f"SUBJECT: {subject}\n\n{body}"
        subprocess.run(
            [str(DLP_SCAN)],
            input=_scan_input,
            capture_output=True,
            text=True,
            check=True
        )
    except Exception as e:
        raise RuntimeError(f"DLP_BLOCKED_OR_SCAN_FAIL: {e}")

    p = subprocess.run(
        [str(SMTP), subject, str(body_file)],
        capture_output=True, text=True
    )

    if p.returncode == 0:
        append_audit("digest_sent", {"session_id": q["session_id"], "queue_file": qpath.name})
        qpath.unlink(missing_ok=True)
        body_file.unlink(missing_ok=True)
        return True
    else:
        errmsg = (p.stderr or p.stdout or "").strip()[:1000]
        append_audit("digest_send_fail", {
            "session_id": q["session_id"],
            "queue_file": qpath.name,
            "err": errmsg
        })

        kind = classify_send_error(errmsg)
        meta = load_queue_meta(qpath)
        meta["retry_count"] = int(meta.get("retry_count", 0)) + 1
        meta["last_error_kind"] = kind
        save_queue_meta(qpath, meta)

        limit = retry_limit_for(kind)
        if meta["retry_count"] > limit:
            quarantine_queue_file(qpath, reason=f"{kind}:retry_exceeded", errmsg=errmsg)
            body_file.unlink(missing_ok=True)
            return True

        return False

def main():
    n = 0
    for qpath in sorted(p for p in QUEUE_DIR.glob("*.json") if not p.name.endswith(".meta.json")):
        try:
            if process_one(qpath):
                n += 1
        except Exception as e:
            errmsg = f"ERROR: {e}"
            append_audit("digest_worker_error", {"queue_file": qpath.name, "msg": str(e)})

            kind = classify_send_error(errmsg)
            meta = load_queue_meta(qpath)
            meta["retry_count"] = int(meta.get("retry_count", 0)) + 1
            meta["last_error_kind"] = kind
            save_queue_meta(qpath, meta)

            limit = retry_limit_for(kind)
            if meta["retry_count"] > limit:
                quarantine_queue_file(qpath, reason=f"{kind}:retry_exceeded", errmsg=errmsg)
    print(f"processed={n}")

if __name__ == "__main__":
    main()
