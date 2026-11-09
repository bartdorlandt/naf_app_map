# /// script
# requires-python = ">=3.15"
# dependencies = []
# ///
"""NAF framework app mapper: tiny stdlib server. Opens/saves any .json file on this machine."""
import json
import os
import tempfile
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

PORT = int(os.environ.get("PORT", 8080))
STATIC_DIR = Path(__file__).parent / "static"
CONFIG = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "naf-app-map" / "config.json"
BLOCKS = ["presentation", "intent", "orchestrator", "observability", "executor", "collector"]
MAX_RECENT = 10
# reject requests whose Host isn't local: blocks DNS-rebinding sites from reading/writing your files
ALLOWED_HOSTS = {f"localhost:{PORT}", f"127.0.0.1:{PORT}"}


def empty():
    return {"blocks": {b: [] for b in BLOCKS}, "sort": {b: "asc" for b in BLOCKS}}


def json_path(p):
    f = Path(p).expanduser()
    if not f.is_absolute() or f.suffix != ".json":
        raise ValueError(f"need an absolute path to a .json file, got {p!r}")
    return f.resolve()


def check_map(data, what):
    # refuse unrelated JSON (package.json, …) so it is never read into, written as, or overwritten by a map
    if not isinstance(data, dict) or not isinstance(data.get("blocks"), dict):
        raise ValueError(f"{what} is not a NAF app map (no 'blocks' object)")
    return data


def load_map(f):
    return check_map(json.loads(f.read_text()), f)


def recent():
    try:
        files = json.loads(CONFIG.read_text()).get("recent", [])
    except (OSError, ValueError):
        files = []
    return [f for f in files if Path(f).is_file()]


def remember(f):
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    files = [str(f)] + [r for r in recent() if r != str(f)]
    CONFIG.write_text(json.dumps({"recent": files[:MAX_RECENT]}, indent=2))


def browse(d):
    d = Path(d or Path.home()).expanduser().resolve()
    entries = [e for e in d.iterdir() if not e.name.startswith(".")]
    return {
        "dir": str(d),
        "parent": str(d.parent) if d.parent != d else None,
        "dirs": sorted((e.name for e in entries if e.is_dir()), key=str.lower),
        "files": sorted((e.name for e in entries if e.is_file() and e.suffix == ".json"), key=str.lower),
    }


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
        if self.headers.get("Host") not in ALLOWED_HOSTS:
            self.send_json({"error": "forbidden host"}, 403)
            return None, None
        u = urlparse(self.path)
        return u.path, {k: v[0] for k, v in parse_qs(u.query).items()}

    def do_GET(self):
        path, q = self.route()
        if path is None:
            return
        try:
            if path == "/api/recent":
                return self.send_json({"recent": recent()})
            if path == "/api/browse":
                return self.send_json(browse(q.get("dir")))
            if path == "/api/state":
                f = json_path(q.get("path", ""))
                data = load_map(f)
                remember(f)
                return self.send_json({"path": str(f), "state": data})
        except (ValueError, OSError) as e:
            return self.send_json({"error": str(e)}, 400)
        super().do_GET()

    def do_PUT(self):
        path, q = self.route()
        if path is None:
            return
        if path != "/api/state":
            return self.send_json({"error": "not found"}, 404)
        try:
            f = json_path(q.get("path", ""))
            if q.get("create") and f.exists():
                return self.send_json({"error": f"{f} already exists"}, 409)
            if f.exists():
                load_map(f)  # only ever overwrite files that are already NAF maps
            data = check_map(json.loads(self.rfile.read(int(self.headers["Content-Length"]))), "request body") if not q.get("create") else empty()
            # mkstemp: unique name, O_EXCL (never follows a planted symlink); replace is atomic, so no half-written file
            fd, tmp = tempfile.mkstemp(dir=f.parent, prefix=f".{f.name}.", suffix=".tmp")
            try:
                with os.fdopen(fd, "w") as fh:
                    fh.write(json.dumps(data, indent=2) + "\n")
                os.chmod(tmp, f.stat().st_mode if f.exists() else 0o644)  # mkstemp makes it 0600
                os.replace(tmp, f)
            except BaseException:
                os.unlink(tmp)
                raise
            remember(f)
            self.send_json({"path": str(f), "state": data})
        except (ValueError, OSError) as e:
            self.send_json({"error": str(e)}, 400)


if __name__ == "__main__":
    print(f"serving on http://localhost:{PORT}, recent files in {CONFIG}", flush=True)
    with HTTPServer(("127.0.0.1", PORT), Handler) as server:
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nstopped", flush=True)
