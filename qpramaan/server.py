"""Loopback-only standard-library API. The local UI is an authorized lab harness."""
import argparse
import json
import mimetypes
import os
import secrets
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
from .attacks import SCENARIOS
from .experiments import run_experiment, execute_report
from .planner import plan
from .quantum import correctness
from .store import Store
from .trace import simulate_frame

ROOT = Path(__file__).resolve().parent.parent


def make_handler(store):
    class Handler(BaseHTTPRequestHandler):
        def json_response(self, value, status=200):
            data = json.dumps(value, allow_nan=False).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(data)

        def local_request(self):
            allowed = {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}
            if self.headers.get("Host", "") not in allowed:
                self.json_response({"error": "Loopback host required."}, 403)
                return False
            origin = self.headers.get("Origin")
            if origin and origin not in {"http://" + h for h in allowed}:
                self.json_response({"error": "Cross-origin request denied."}, 403)
                return False
            return True

        def do_GET(self):
            if not self.local_request():
                return
            path = urlparse(self.path).path
            if path == "/api/meta":
                return self.json_response({"name": "Q-PRAMAAN", "version": "1.0.0", "scenarios": SCENARIOS,
                                           "scope": "Local simulation and assurance laboratory"})
            if path == "/api/correctness":
                return self.json_response(correctness())
            if path == "/api/benchmark":
                bp = ROOT / "output" / "benchmark.json"
                return self.json_response(json.loads(bp.read_text(encoding="utf-8")) if bp.exists() else {"available": False})
            if path.startswith("/api/reports/"):
                report = store.get(path.rsplit("/", 1)[-1])
                return self.json_response(report if report else {"error": "Not found."}, 200 if report else 404)
            file = ROOT / "web" / ("index.html" if path == "/" else path.lstrip("/"))
            if file.resolve().parent != (ROOT / "web").resolve() or not file.is_file():
                return self.json_response({"error": "Not found."}, 404)
            data = file.read_bytes()
            self.send_response(200)
            mime = mimetypes.guess_type(str(file))[0]
            if file.suffix == ".woff2":
                mime = "font/woff2"
            self.send_header("Content-Type", mime or "application/octet-stream")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com data:; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(data)

        def do_POST(self):
            if not self.local_request():
                return
            if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                return self.json_response({"error": "JSON required."}, 415)
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 16384:
                    return self.json_response({"error": "Invalid request size."}, 413)
                body = json.loads(self.rfile.read(length))
                if not isinstance(body, dict):
                    raise ValueError("Expected an object.")
                if self.path == "/api/experiments":
                    return self.json_response(run_experiment(body, store), 201)
                if self.path == "/api/planner":
                    return self.json_response(plan(float(body.get("target", 1e-6)), int(body.get("budget", 1000000)),
                                                   str(body.get("model", "ideal"))))
                if self.path == "/api/execute":
                    return self.json_response(execute_report(str(body.get("id", "")), store))
                if self.path == "/api/trace":
                    return self.json_response(simulate_frame(
                        int(body.get("state", 0)),
                        int(body.get("branch", 0)),
                        int(body.get("pauli", 0)),
                        int(body.get("basis", 0))
                    ))
                return self.json_response({"error": "Not found."}, 404)
            except (ValueError, TypeError, OverflowError) as e:
                return self.json_response({"error": str(e)}, 400)
            except KeyError:
                return self.json_response({"error": "Experiment not found."}, 404)
            except Exception:
                import traceback
                traceback.print_exc()
                return self.json_response({"error": "Experiment failed; see local server log."}, 500)

        def log_message(self, fmt, *args):
            print(fmt % args, flush=True)
    return Handler


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--database", default=str(ROOT / "data" / "qpramaan.sqlite"))
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(Store(args.database)))
    print(f"Q-PRAMAAN ready: http://127.0.0.1:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()


if __name__ == "__main__":
    main()
