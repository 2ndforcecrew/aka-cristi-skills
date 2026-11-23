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
    # SQLite URI mode=ro is read-only; immutable avoids sidecar writes.
    uri = path.resolve().as_uri() + "?mode=ro&immutable=1"
    with sqlite3.connect(uri, uri=True, timeout=2) as db:
        db.execute("PRAGMA query_only=ON")
        tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "tasks" not in tables:
            return []
        rows = db.execute("SELECT task_id, status FROM tasks ORDER BY rowid DESC LIMIT ?", (limit,)).fetchall()
        return [{"task_id": str(task_id), "status": str(status)} for task_id, status in rows]


def make_handler(db_path):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            route = urlsplit(self.path).path
            if route not in ("/health", "/api/tasks"):
                self.respond(404, {"error": "not_found"})
                return
            if route == "/health":
                self.respond(200, {"status": "ok", "mode": "read_only"})
                return
            try:
                tasks = task_summary(db_path)
            except (OSError, sqlite3.Error, ValueError):
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
