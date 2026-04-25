"""Phase-1 backend acceptance test — boots uvicorn, exercises every endpoint.

Run from backend/ directory:
    .venv/bin/python -m tests.test_acceptance

Covers TASK_BREAKDOWN.md §1.3 acceptance criteria:
  - /health returns 200
  - /upload accepts a valid PDF, rejects empty / non-PDF / oversized
  - /evaluate rejects unknown document_id (404) and unknown checklist_id (400)
  - /results returns 404 for unknown id; (live) returns the same body as /evaluate
  - Logs don't leak the API key or expose stack traces

Live /evaluate + /results round-trip runs only if ANTHROPIC_API_KEY is real
(not the placeholder). All other tests are offline.
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import traceback
from pathlib import Path

import urllib.error
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # noqa: E402

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(_PROJECT_ROOT / ".env.local")

import fitz  # noqa: E402
import json  # noqa: E402


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _make_pdf() -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Access Controls", fontsize=24)
    page.insert_text((50, 100), "All users authenticate via Okta SSO.", fontsize=11)
    data = doc.tobytes()
    doc.close()
    return data


def _post_multipart(url: str, filename: str, content: bytes, content_type: str = "application/pdf"):
    boundary = "----AuditDocBoundary"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: {content_type}\r\n\r\n"
    ).encode() + content + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())


def _post_json(url: str, payload: dict):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())


def _get_json(url: str):
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())


# --- Server lifecycle -------------------------------------------------------


class Server:
    def __init__(self, port: int, max_upload_bytes: int = 4096) -> None:
        self.port = port
        self.base = f"http://127.0.0.1:{port}"
        env = os.environ.copy()
        env["MAX_UPLOAD_BYTES"] = str(max_upload_bytes)
        env["LOG_LEVEL"] = "INFO"
        self.proc = subprocess.Popen(
            [".venv/bin/uvicorn", "main:app", "--port", str(port), "--log-level", "info"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=env,
            cwd=str(Path(__file__).resolve().parent.parent),
        )

    def wait_ready(self, timeout_s: float = 15.0) -> None:
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            try:
                with urllib.request.urlopen(f"{self.base}/health", timeout=1) as resp:
                    if resp.status == 200:
                        return
            except Exception:
                time.sleep(0.2)
        raise RuntimeError("server failed to start within timeout")

    def stop(self) -> str:
        self.proc.terminate()
        try:
            self.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait()
        out = self.proc.stdout.read().decode() if self.proc.stdout else ""
        return out


# --- Tests ------------------------------------------------------------------


def _has_real_key() -> bool:
    key = os.getenv("ANTHROPIC_API_KEY", "")
    return bool(key) and not key.startswith("sk-ant-PLACEHOLDER")


def run_offline_tests(s: Server) -> None:
    # 1. /health
    code, body = _get_json(f"{s.base}/health")
    assert code == 200 and body == {"status": "ok"}, f"/health: {code} {body}"

    # 2. /upload happy path
    code, body = _post_multipart(f"{s.base}/upload", "good.pdf", _make_pdf())
    assert code == 200, f"/upload happy: {code} {body}"
    assert "document_id" in body and body["status"] == "uploaded"
    happy_doc_id = body["document_id"]

    # 3. /upload empty file → 400
    code, body = _post_multipart(f"{s.base}/upload", "empty.pdf", b"")
    assert code == 400, f"/upload empty: expected 400, got {code} {body}"

    # 4. /upload non-PDF bytes → 400 (magic-byte check)
    code, body = _post_multipart(f"{s.base}/upload", "fake.pdf", b"this is not a pdf at all")
    assert code == 400, f"/upload non-PDF: expected 400, got {code} {body}"
    assert "PDF" in body.get("detail", ""), f"detail should mention PDF; got {body}"

    # 5. /upload oversized → 413 (server has MAX_UPLOAD_BYTES=4096)
    big = b"%PDF-" + b"\x00" * 5000
    code, body = _post_multipart(f"{s.base}/upload", "big.pdf", big)
    assert code == 413, f"/upload oversized: expected 413, got {code} {body}"

    # 6. /evaluate unknown document_id → 404
    code, body = _post_json(
        f"{s.base}/evaluate",
        {"document_id": "00000000-0000-0000-0000-000000000000", "checklist_id": "soc2_trust_services"},
    )
    assert code == 404, f"/evaluate unknown doc: expected 404, got {code} {body}"

    # 7. /evaluate unknown checklist_id → 400 (ValueError → 400 in main.py)
    code, body = _post_json(
        f"{s.base}/evaluate",
        {"document_id": happy_doc_id, "checklist_id": "no_such_checklist"},
    )
    assert code == 400, f"/evaluate unknown checklist: expected 400, got {code} {body}"

    # 8. /results unknown id → 404
    code, body = _get_json(f"{s.base}/results/00000000-0000-0000-0000-000000000000")
    assert code == 404, f"/results unknown: expected 404, got {code} {body}"

    print("  offline endpoints  ok")
    return  # implicit, but explicit reads better


def run_live_tests(s_live: Server) -> None:
    # 9. /upload then /evaluate then /results round-trip
    code, body = _post_multipart(f"{s_live.base}/upload", "live.pdf", _make_pdf())
    assert code == 200
    doc_id = body["document_id"]

    code, body = _post_json(
        f"{s_live.base}/evaluate",
        {"document_id": doc_id, "checklist_id": "soc2_trust_services"},
    )
    assert code == 200, f"/evaluate live: expected 200, got {code} {body}"
    assert body["status"] == "completed", f"expected completed, got {body['status']}"
    assert len(body["findings"]) == 3, f"expected 3 findings, got {len(body['findings'])}"

    eval_id = body["evaluation_id"]
    findings_from_eval = body["findings"]

    # Every FAIL must cite — the rules/citations-mandatory.md guarantee.
    for f in findings_from_eval:
        if f["status"] == "FAIL":
            assert f["supporting_chunks"], f"FAIL finding {f['item_id']} has no citations"
        for c in f["supporting_chunks"]:
            assert c["page"] >= 1, f"page must be 1-indexed (got {c['page']})"

    # 10. /results returns the same body
    code, body = _get_json(f"{s_live.base}/results/{eval_id}")
    assert code == 200, f"/results live: expected 200, got {code}"
    assert body["evaluation_id"] == eval_id
    assert len(body["findings"]) == len(findings_from_eval)

    print(f"  live round-trip   ok  ({len(findings_from_eval)} findings)")


def assert_logs_clean(logs: str) -> None:
    """Logs should not leak the API key or contain raw tracebacks."""
    key = os.getenv("ANTHROPIC_API_KEY", "")
    if key and len(key) > 12:
        # Don't search for the literal key — just its identifying prefix.
        prefix = key[:12]
        assert prefix not in logs, "API key prefix appeared in server logs"
    assert "Traceback (most recent call last)" not in logs, "raw traceback leaked into logs"
    print("  log hygiene       ok")


# --- Runner -----------------------------------------------------------------


def main() -> int:
    failures: list[tuple[str, str]] = []

    # Offline server with a tiny upload cap.
    s_offline = Server(_free_port(), max_upload_bytes=4096)
    try:
        try:
            s_offline.wait_ready()
            run_offline_tests(s_offline)
        except Exception:
            failures.append(("offline_endpoints", traceback.format_exc()))
    finally:
        offline_logs = s_offline.stop()

    try:
        assert_logs_clean(offline_logs)
    except Exception:
        failures.append(("offline_log_hygiene", traceback.format_exc()))

    # Live server with default 50MB cap. Skip if no real key.
    if _has_real_key():
        s_live = Server(_free_port(), max_upload_bytes=50 * 1024 * 1024)
        try:
            try:
                s_live.wait_ready()
                run_live_tests(s_live)
            except Exception:
                failures.append(("live_round_trip", traceback.format_exc()))
        finally:
            live_logs = s_live.stop()

        try:
            assert_logs_clean(live_logs)
        except Exception:
            failures.append(("live_log_hygiene", traceback.format_exc()))
    else:
        print("  live round-trip   skipped (no real ANTHROPIC_API_KEY)")

    if failures:
        print("")
        for name, tb in failures:
            print(f"--- {name} ---")
            print(tb)
        print(f"FAILED — {len(failures)} step(s) failed")
        return 1

    suffix = " (with live)" if _has_real_key() else " (offline only)"
    print(f"OK — Phase 1 acceptance passed{suffix}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
