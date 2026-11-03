"""NAF framework app mapper: tiny stdlib server. One JSON file per state in DATA_DIR."""
import json
import os
import re
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

DATA_DIR = Path(os.environ.get("DATA_DIR", "data"))
STATIC_DIR = Path(__file__).parent / "static"
LAST = DATA_DIR / ".last"
NAME_RE = re.compile(r"^[\w.-]+\.json$")
BLOCKS = ["presentation", "intent", "orchestrator", "observability", "executor", "collector"]


def safe(name):
    if not name or not NAME_RE.match(name):
        raise ValueError(f"invalid file name: {name!r} (use letters, digits, _ . -, ending in .json)")
    return DATA_DIR / name


def empty():
    return {"blocks": {b: [] for b in BLOCKS}, "sort": {b: "asc" for b in BLOCKS}}


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(STATIC_DIR), **kw)

    def send_json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def route(self):
        u = urlparse(self.path)
        return u.path, parse_qs(u.query).get("file", [""])[0]

    def do_GET(self):
        path, name = self.route()
        try:
            if path == "/api/files":
                last = LAST.read_text().strip() if LAST.exists() else ""
                files = sorted(p.name for p in DATA_DIR.glob("*.json"))
                return self.send_json({"files": files, "last": last if last in files else ""})
            if path == "/api/state":
                f = safe(name)
                if not f.exists():
                    return self.send_json(empty())
                LAST.write_text(name)
                return self.send_json(json.loads(f.read_text()))
        except ValueError as e:
            return self.send_json({"error": str(e)}, 400)
        super().do_GET()

    def do_PUT(self):
        path, name = self.route()
        if path != "/api/state":
            return self.send_json({"error": "not found"}, 404)
        try:
            f = safe(name)
            data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            tmp = f.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, indent=2) + "\n")
            os.replace(tmp, f)  # atomic: no half-written state on crash
            LAST.write_text(name)
            self.send_json({"ok": True})
        except (ValueError, json.JSONDecodeError) as e:
            self.send_json({"error": str(e)}, 400)


if __name__ == "__main__":
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    port = int(os.environ.get("PORT", 8080))
    print(f"serving on :{port}, data in {DATA_DIR.resolve()}")
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()
