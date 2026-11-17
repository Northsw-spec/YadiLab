"""Loopback-only local server, no third-party runtime dependencies."""
from __future__ import annotations

import argparse
from html import escape
import json
import mimetypes
import sys
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

from . import __version__, config
from .model import ProjectValidationError, topology_trace, validate_project
from .csv_import import import_csv_tables
from .arp import ArpSession
from .simulation import SimulationRegistry
from .storage import ProjectConflictError, ProjectStore

WEB = Path(__file__).resolve().parent.parent / "web"
MAX_BODY = 8 * 1024 * 1024


class LabHTTPServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address: tuple[str, int], store: ProjectStore):
        self.store = store
        self.simulations = SimulationRegistry()
        super().__init__(address, Handler)


class Handler(BaseHTTPRequestHandler):
    server: LabHTTPServer

    def _json(self, code: int, data: dict | list) -> None:
        body = json.dumps(data, ensure_ascii=False, allow_nan=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> object:
        try:
            size = int(self.headers.get("Content-Length", "-1"))
        except ValueError:
            raise ProjectValidationError("request: invalid Content-Length") from None
        if not 0 <= size <= MAX_BODY:
            raise ProjectValidationError("request: body missing or larger than 8 MiB")
        try:
            return json.loads(self.rfile.read(size))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ProjectValidationError("request: invalid JSON") from None

    def _respond_error(self, error: Exception) -> None:
        if isinstance(error, ProjectConflictError):
            self._json(HTTPStatus.CONFLICT, {"error": "CONFLICT", "message": str(error), "currentSha256": error.actual_hash})
        elif isinstance(error, ProjectValidationError):
            self._json(HTTPStatus.UNPROCESSABLE_ENTITY, {"error": "INVALID_PROJECT", "message": error.message})
        elif isinstance(error, FileNotFoundError):
            self._json(HTTPStatus.NOT_FOUND, {"error": "NOT_FOUND", "message": str(error)})
        else:
            self.log_error("unexpected server exception: %r", error)
            self._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "INTERNAL", "message": "Local operation failed"})

    def do_GET(self) -> None:
        path = unquote(urlsplit(self.path).path)
        try:
            if path == "/api/health":
                self._json(200, {"app": config.APP_NAME, "version": __version__, "storage": "local"})
            elif path == "/api/projects":
                self._json(200, {"projects": self.server.store.list()})
            elif path.startswith("/api/projects/"):
                self._json(200, self.server.store.read(path[len("/api/projects/"):]))
            elif path in ("/", "/index.html", "/app.js", "/model.js", "/canvas.js", "/styles.css"):
                filename = "index.html" if path == "/" else path[1:]
                data = (WEB / filename).read_bytes()
                if filename == "index.html":
                    # Escape the declarative product name at the HTML boundary.
                    data = data.replace(b"{{APP_NAME}}", escape(config.APP_NAME, quote=True).encode("utf-8"))
                mime = mimetypes.guess_type(filename)[0] or "application/octet-stream"
                self.send_response(200)
                self.send_header("Content-Type", mime + ("; charset=utf-8" if mime.startswith("text/") or mime == "text/javascript" else ""))
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(data)
            else:
                self._json(404, {"error": "NOT_FOUND", "message": "No such resource"})
        except Exception as e:
            self._respond_error(e)

    def do_POST(self) -> None:
        path = urlsplit(self.path).path
        try:
            body = self._read_json()
            if path == "/api/validate":
                self._json(200, {"project": validate_project(body)})
            elif path == "/api/import/csv":
                self._json(200, {"project": import_csv_tables(body)})
            elif path == "/api/trace":
                if not isinstance(body, dict) or set(body) != {"project", "source", "target"}:
                    raise ProjectValidationError("trace: expected project, source, target")
                self._json(200, topology_trace(body["project"], body["source"], body["target"]))
            elif path == "/api/diagnostics/arp":
                if not isinstance(body, dict) or set(body) != {"project", "sourceNode", "sourcePort", "targetIpv4"}:
                    raise ProjectValidationError("arp diagnostics: expected project, sourceNode, sourcePort, targetIpv4")
                # Every request is a new isolated simulation over the supplied
                # working document. No store read/write or shared runtime cache.
                session = ArpSession(body["project"])
                result = session.resolve(body["sourceNode"], body["sourcePort"], body["targetIpv4"])
                self._json(200, {
                    "result": result,
                    "arpTable": session.arp_table(body["sourceNode"], body["sourcePort"]),
                    "macTables": session.fabric.learned_mac_tables(),
                    "ephemeral": True,
                })
            elif path == "/api/simulation/start":
                if not isinstance(body, dict) or set(body) != {"project"}:
                    raise ProjectValidationError("simulation start: expected project")
                self._json(200, self.server.simulations.start(body["project"]))
            elif path == "/api/simulation/run":
                required = {"sessionId", "project", "operation", "sourceNode", "sourcePort", "target"}
                if not isinstance(body, dict) or set(body) != required:
                    raise ProjectValidationError("simulation run: expected sessionId, project, operation, sourceNode, sourcePort, target")
                if not all(isinstance(body[k], str) for k in
                           ("sessionId", "operation", "sourceNode", "sourcePort", "target")):
                    raise ProjectValidationError("simulation run: source/target/operation/sessionId must be strings")
                self._json(200, self.server.simulations.run(
                    body["sessionId"], body["project"], body["operation"],
                    body["sourceNode"], body["sourcePort"], body["target"]))
            elif path == "/api/simulation/reset":
                if not isinstance(body, dict) or set(body) != {"sessionId", "project"}:
                    raise ProjectValidationError("simulation reset: expected sessionId and project")
                self._json(200, self.server.simulations.reset(body["sessionId"], body["project"]))
            elif path == "/api/simulation/stop":
                if not isinstance(body, dict) or set(body) != {"sessionId"}:
                    raise ProjectValidationError("simulation stop: expected sessionId")
                self._json(200, self.server.simulations.stop(body["sessionId"]))
            elif path == "/api/save":
                if not isinstance(body, dict) or set(body) != {"filename", "project", "expectedSha256"}:
                    raise ProjectValidationError("save: expected filename, project, expectedSha256")
                self._json(200, self.server.store.save(body["filename"], body["project"], body["expectedSha256"]))
            else:
                self._json(404, {"error": "NOT_FOUND", "message": "No such endpoint"})
        except Exception as e:
            self._respond_error(e)

    def log_message(self, format: str, *args: object) -> None:
        sys.stderr.write(config.APP_NAME + ": " + (format % args) + "\n")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=f"{config.APP_NAME}: local canonical network lab")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--data-dir", type=Path, default=Path.home() / ".local" / "share" / "network-projects")
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args(argv)
    if not 0 <= args.port <= 65535:
        parser.error("port must be between 0 and 65535")
    server = LabHTTPServer(("127.0.0.1", args.port), ProjectStore(args.data_dir))
    url = f"http://127.0.0.1:{server.server_port}/"
    print(f"{config.APP_NAME} {__version__} at {url}", flush=True)
    print(f"Projects stored in {server.store.root}", flush=True)
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever(poll_interval=0.2)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
