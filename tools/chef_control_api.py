"""Local-only, read-only CHEF task status API (stdlib, no paid model calls).

Start with: python -m tools.chef_control_api --db /private/state/chef.sqlite3
Only sanitized task metadata is exposed; no prompts, workspace paths or event evidence.
"""
import argparse
import json
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

MAX_RESULTS = 100


def task_summary(db_path, limit=50):
    """Read actual runtime task statuses without initializing or mutating the DB."""
    if not 1 <= limit <= MAX_RESULTS:
        raise ValueError("limit out of range")
    path = Path(db_path).expanduser()
    if not path.is_file() or path.is_symlink():
        raise FileNotFoundError("existing regular SQLite database required")
    # SQLite URI mode=ro prevents database writes; live updates remain visible.
    uri = path.resolve().as_uri() + "?mode=ro"
    with sqlite3.connect(uri, uri=True, timeout=2) as db:
        db.execute("PRAGMA query_only=ON")
        tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "tasks" not in tables:
            return []
        rows = db.execute("SELECT task_id, status FROM tasks ORDER BY rowid DESC LIMIT ?", (limit,)).fetchall()
        return [{"task_id": str(task_id), "status": str(status)} for task_id, status in rows]



def task_detail(db_path, task_id):
    """Allowlisted task timeline; never disclose prompts, raw logs or workspaces."""
    if not task_id or len(task_id) > 128 or not all(c.isalnum() or c in "-_" for c in task_id):
        raise ValueError("invalid task id")
    path = Path(db_path).expanduser()
    if not path.is_file() or path.is_symlink():
        raise FileNotFoundError("database missing")
    with sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, timeout=2) as db:
        db.execute("PRAGMA query_only=ON")
        tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "tasks" not in tables:
            return None
        row = db.execute("SELECT task_id,status FROM tasks WHERE task_id=?", (task_id,)).fetchone()
        if not row:
            return None
        events = []
        if "events" in tables:
            events = [{"role": role, "status": status, "timestamp": ts}
                      for role, status, ts in db.execute(
                          "SELECT role,status,timestamp FROM events WHERE task_id=? ORDER BY timestamp,rowid LIMIT ?",
                          (task_id, MAX_RESULTS))]
        attempts = []
        if "attempts" in tables:
            safe_reasons = {"timeout", "missing output or independent thread identity",
                            "read-only role modified deliverables", "FileNotFoundError",
                            "CalledProcessError", "OSError", "PermissionError"}
            for role, number, result in db.execute(
                    "SELECT role,attempt,result FROM attempts WHERE task_id=? ORDER BY rowid LIMIT ?",
                    (task_id, MAX_RESULTS)):
                try:
                    payload = json.loads(result)
                except (ValueError, TypeError):
                    payload = {}
                if not isinstance(payload, dict):
                    payload = {}
                attempts.append({"role": role, "attempt": number,
                                 "status": str(payload.get("status", "UNKNOWN"))[:40],
                                 "reason": payload.get("reason") if payload.get("reason") in safe_reasons else None,
                                 "has_patch_hash": isinstance(payload.get("patch_sha256"), str)})
        timestamps = [e["timestamp"] for e in events if isinstance(e["timestamp"], (float, int))]
        return {"task_id": row[0], "status": row[1], "events": events,
                "attempts": attempts,
                "elapsed_seconds": round(max(timestamps)-min(timestamps), 2) if timestamps else None,
                "retry": {"available": False, "reason": "requires authorized runtime execution"},
                "approval": {"available": False, "reason": "approval backend not configured"}}


def make_handler(db_path):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            route = urlsplit(self.path).path
            if route not in ("/", "/health", "/api/tasks") and not route.startswith("/api/tasks/"):
                self.respond(404, {"error": "not_found"})
                return
            if route == "/":
                try:
                    page = Path(__file__).with_name("chef_control_dashboard.html").read_bytes()
                except OSError:
                    self.respond(503, {"error": "dashboard_unavailable"})
                    return
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Security-Policy", "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'")
                self.send_header("Content-Length", str(len(page)))
                self.end_headers()
                self.wfile.write(page)
                return
            if route == "/health":
                self.respond(200, {"status": "ok", "mode": "read_only"})
                return
            try:
                if route.startswith("/api/tasks/"):
                    detail = task_detail(db_path, route.removeprefix("/api/tasks/"))
                    if detail is None:
                        self.respond(404, {"error": "task_not_found"})
                    else:
                        self.respond(200, detail)
                    return
                tasks = task_summary(db_path)
            except ValueError:
                self.respond(400, {"error": "invalid_request"})
                return
            except (OSError, sqlite3.Error):
                self.respond(503, {"error": "database_unavailable"})
                return
            self.respond(200, {"tasks": tasks, "count": len(tasks)})

        def respond(self, status, body):
            payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, format, *args):
            # Avoid leaking request paths or query parameters into terminal logs.
            pass

    return Handler


def main(argv=None):
    parser = argparse.ArgumentParser(description="CHEF local read-only task API")
    parser.add_argument("--db", required=True, help="Existing private runtime SQLite file")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args(argv)
    if not 1 <= args.port <= 65535:
        parser.error("port must be 1..65535")
    # Do not expose a bind-address option until auth and network threat model exist.
    server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(args.db))
    print(f"CHEF read-only API: http://127.0.0.1:{server.server_port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
