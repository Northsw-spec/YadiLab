"""Loopback-only local server, no third-party runtime dependencies."""
from __future__ import annotations

import argparse
import base64
from html import escape
import json
import mimetypes
import sys
import webbrowser
from threading import Event, Thread
from time import monotonic
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

from . import __version__, config
from .model import ProjectValidationError, topology_trace, validate_project
from .csv_import import import_csv_tables
from .xlsx_import import import_xlsx_workbook
from .ods_import import import_ods_workbook
from .import_inspection import inspect_source
from .spreadsheet_templates import template_bytes
from .spreadsheet_export import export_workbook
from .arp import ArpSession
from .dhcp import discover_offer, simulate_dora
from .dhcp_registry import DhcpSessionRegistry
from .dhcp_investigation import InvestigationRegistry
from .icmp_investigation import IcmpInvestigationRegistry
from .simulation import SimulationRegistry
from .session_idle import CLEANUP_INTERVAL_SECONDS, CLEANUP_JOIN_SECONDS
from .routing import ConnectedRoutingTable
from .ipv4 import IPv4Trace
from .icmp_ping import EchoExchange
from .troubleshooting import compare_link_fault, compare_fault
from .storage import ProjectConflictError, ProjectStore

WEB = Path(__file__).resolve().parent.parent / "web"
MAX_BODY = 8 * 1024 * 1024


class LabHTTPServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address: tuple[str, int], store: ProjectStore,
                 *, clock=monotonic, cleanup_interval: float = CLEANUP_INTERVAL_SECONDS):
        if address[0] != "127.0.0.1":
            raise ValueError("local HTTP server must bind to 127.0.0.1")
        if cleanup_interval <= 0:
            raise ValueError("cleanup interval must be positive")
        self.store = store
        self.simulations = SimulationRegistry(clock=clock)
        self.dhcp_sessions = DhcpSessionRegistry(clock=clock)
        self.investigations = InvestigationRegistry(clock=clock)
        self.icmp_investigations = IcmpInvestigationRegistry(clock=clock)
        self._cleanup_stop = Event()
        self._cleanup_interval = cleanup_interval
        super().__init__(address, Handler)
        self._cleanup_thread = Thread(target=self._cleanup_loop, name="session-idle-cleanup",
                                      daemon=True)
        self._cleanup_thread.start()

    def _cleanup_loop(self) -> None:
        while not self._cleanup_stop.wait(self._cleanup_interval):
            for registry in (self.simulations, self.dhcp_sessions,
                             self.investigations, self.icmp_investigations):
                registry.cleanup_expired()

    def server_close(self) -> None:
        self._cleanup_stop.set()
        self._cleanup_thread.join(timeout=CLEANUP_JOIN_SECONDS)
        super().server_close()
        if self._cleanup_thread.is_alive():
            raise RuntimeError("session cleanup worker did not stop")


class Handler(BaseHTTPRequestHandler):
    server: LabHTTPServer

    def _trusted_request(self) -> bool:
        # The listener is local, but a browser can be directed to it through
        # an attacker-controlled DNS name. Compare the literal authority with
        # the actual bound address and port before touching any API or file.
        authority = f"{self.server.server_address[0]}:{self.server.server_port}"
        hosts = self.headers.get_all("Host", [])
        origins = self.headers.get_all("Origin", [])
        sites = self.headers.get_all("Sec-Fetch-Site", [])
        allowed = (len(hosts) == 1 and hosts[0] == authority
                   and len(origins) <= 1
                   and (not origins or origins[0] == f"http://{authority}")
                   and len(sites) <= 1
                   and (not sites or sites[0] in ("same-origin", "none"))
                   and self.path.startswith("/") and not self.path.startswith("//"))
        if not allowed:
            self._json(HTTPStatus.FORBIDDEN, {
                "error": "FORBIDDEN", "message": "Local HTTP origin is not allowed"})
        return allowed

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
        if not self._trusted_request():
            return
        path = unquote(urlsplit(self.path).path)
        try:
            if path == "/api/health":
                self._json(200, {"app": config.APP_NAME, "version": __version__, "storage": "local"})
            elif path in ("/api/templates/xlsx", "/api/templates/ods"):
                extension = path.rsplit("/", 1)[1]
                payload = template_bytes(extension)
                mime = ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        if extension == "xlsx" else
                        "application/vnd.oasis.opendocument.spreadsheet")
                self.send_response(200)
                self.send_header("Content-Type", mime)
                self.send_header("Content-Disposition",
                                 f'attachment; filename="network-schema13-demo.{extension}"')
                self.send_header("Content-Length", str(len(payload)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.end_headers()
                self.wfile.write(payload)
            elif path == "/api/projects":
                self._json(200, {"projects": self.server.store.list()})
            elif path.startswith("/api/projects/"):
                self._json(200, self.server.store.read(path[len("/api/projects/"):]))
            elif path in ("/", "/index.html", "/app.js", "/model.js", "/canvas.js",
                          "/ui/dom.js", "/services/api.js", "/features/projects/persistence.js",
                          "/features/projects/transfer.js",
                          "/features/diagnostics/queries.js", "/features/diagnostics/presenters.js",
                          "/features/diagnostics/icmp-investigation-panel.js",
                          "/features/sessions/dhcp-investigation.js",
                          "/features/sessions/icmp-investigation.js",
                          "/features/sessions/dora-session.js",
                          "/features/sessions/simulation-session.js",
                          "/styles.css"):
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
        if not self._trusted_request():
            return
        # JSON is intentionally non-simple for browser CORS. Local scripts
        # without Origin remain supported; cross-site forms cannot submit.
        media_types = self.headers.get_all("Content-Type", [])
        media = media_types[0].split(";", 1)[0].strip().lower() if len(media_types) == 1 else ""
        if media != "application/json":
            self._json(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, {
                "error": "UNSUPPORTED_MEDIA_TYPE", "message": "Expected application/json"})
            return
        path = urlsplit(self.path).path
        try:
            body = self._read_json()
            if path == "/api/validate":
                self._json(200, {"project": validate_project(body)})
            elif path == "/api/import/csv":
                self._json(200, {"project": import_csv_tables(body)})
            elif path == "/api/import/inspect":
                self._json(200, inspect_source(body))
            elif path == "/api/import/xlsx":
                self._json(200, {"project": import_xlsx_workbook(body)})
            elif path == "/api/import/ods":
                self._json(200, {"project": import_ods_workbook(body)})
            elif path == "/api/export/spreadsheet":
                if not isinstance(body, dict) or set(body) != {"project", "format"}:
                    raise ProjectValidationError(
                        "spreadsheet export: expected exactly project and format")
                extension = body["format"]
                if not isinstance(extension, str) or extension not in ("xlsx", "ods"):
                    raise ProjectValidationError("spreadsheet export: expected format xlsx or ods")
                data = export_workbook(body["project"], extension)
                self._json(200, {
                    "filename": "network-documentation." + extension,
                    "contentBase64": base64.b64encode(data).decode("ascii"),
                })
            elif path == "/api/trace":
                if not isinstance(body, dict) or set(body) != {"project", "source", "target"}:
                    raise ProjectValidationError("trace: expected project, source, target")
                self._json(200, topology_trace(body["project"], body["source"], body["target"]))
            elif path == "/api/troubleshoot/fault":
                required = {"project", "sourceNode", "sourcePort", "destinationIpv4",
                            "ttl", "identifier", "sequence", "fault"}
                if not isinstance(body, dict) or set(body) != required:
                    raise ProjectValidationError(
                        "troubleshoot: expected project, sourceNode, sourcePort, "
                        "destinationIpv4, ttl, identifier, sequence, fault")
                # Identical canonical model and existing Echo/ARP/Ethernet
                # engine as the link-only route; no persistent mutation.
                self._json(200, compare_fault(
                    body["project"], body["sourceNode"], body["sourcePort"],
                    body["destinationIpv4"], body["ttl"], body["identifier"],
                    body["sequence"], body["fault"]))
            elif path == "/api/troubleshoot/link":
                required = {"project", "sourceNode", "sourcePort", "destinationIpv4",
                            "ttl", "identifier", "sequence", "linkId"}
                if not isinstance(body, dict) or set(body) != required:
                    raise ProjectValidationError(
                        "troubleshoot: expected project, sourceNode, sourcePort, "
                        "destinationIpv4, ttl, identifier, sequence, linkId"
                    )
                # Three isolated genuine Echo exchanges; neither user document
                # nor on-disk store can be modified by the comparison.
                self._json(200, compare_link_fault(
                    body["project"], body["sourceNode"], body["sourcePort"],
                    body["destinationIpv4"], body["ttl"], body["identifier"],
                    body["sequence"], body["linkId"]))
            elif path == "/api/icmp/echo":
                required = {"project", "sourceNode", "sourcePort", "destinationIpv4",
                            "ttl", "identifier", "sequence"}
                if not isinstance(body, dict) or set(body) != required:
                    raise ProjectValidationError(
                        "icmp echo: expected project, sourceNode, sourcePort, destinationIpv4, ttl, identifier, sequence"
                    )
                # A complete request/reply exchange through one Layer 3/ARP/
                # Ethernet instance. No stored session or project file writes.
                self._json(200, EchoExchange(body["project"]).ping(
                    body["sourceNode"], body["sourcePort"],
                    body["destinationIpv4"], body["ttl"],
                    body["identifier"], body["sequence"]))
            elif path == "/api/ipv4/trace":
                required = {"project", "sourceNode", "sourcePort", "destinationIpv4", "ttl"}
                if not isinstance(body, dict) or set(body) != required:
                    raise ProjectValidationError(
                        "ipv4 trace: expected project, sourceNode, sourcePort, destinationIpv4, ttl"
                    )
                # The request creates its own isolated ARP/Ethernet state.
                # No guessed links, cached results, file writes or ICMP echo.
                result = IPv4Trace(body["project"]).send(
                    body["sourceNode"], body["sourcePort"],
                    body["destinationIpv4"], body["ttl"])
                self._json(200, result)
            elif path == "/api/routing/connected":
                if not isinstance(body, dict) or set(body) != {"project", "nodeId", "destinationIpv4"}:
                    raise ProjectValidationError(
                        "routing: expected project, nodeId, destinationIpv4"
                    )
                # Query configured IPv4 connected prefixes ONLY. Never consult
                # graph paths, cached MAC/ARP entries, or invent IP forwarding.
                self._json(200, ConnectedRoutingTable(body["project"], body["nodeId"])
                           .lookup(body["destinationIpv4"]))
            elif path == "/api/icmp/investigation/start":
                required = {"project", "sourceNode", "sourcePort", "destinationIpv4", "ttl"}
                if not isinstance(body, dict) or set(body) != required:
                    raise ProjectValidationError(
                        "icmp investigation start: expected project, sourceNode, sourcePort, destinationIpv4, ttl")
                self._json(200, self.server.icmp_investigations.start(
                    body["project"], body["sourceNode"], body["sourcePort"],
                    body["destinationIpv4"], body["ttl"]))
            elif path == "/api/icmp/investigation/probe":
                required = {"sessionId", "project", "probe", "target"}
                if not isinstance(body, dict) or set(body) != required:
                    raise ProjectValidationError(
                        "icmp investigation probe: expected sessionId, project, probe, target")
                self._json(200, self.server.icmp_investigations.probe(
                    body["sessionId"], body["project"], body["probe"], body["target"]))
            elif path == "/api/icmp/investigation/diagnose":
                required = {"sessionId", "project", "diagnosis"}
                if not isinstance(body, dict) or set(body) != required:
                    raise ProjectValidationError(
                        "icmp investigation diagnose: expected sessionId, project, diagnosis")
                self._json(200, self.server.icmp_investigations.diagnose(
                    body["sessionId"], body["project"], body["diagnosis"]))
            elif path == "/api/icmp/investigation/repair":
                if not isinstance(body, dict) or set(body) != {"sessionId", "project"}:
                    raise ProjectValidationError(
                        "icmp investigation repair: expected sessionId, project")
                self._json(200, self.server.icmp_investigations.repair(
                    body["sessionId"], body["project"]))
            elif path == "/api/icmp/investigation/stop":
                if not isinstance(body, dict) or set(body) != {"sessionId"}:
                    raise ProjectValidationError(
                        "icmp investigation stop: expected sessionId")
                self._json(200, self.server.icmp_investigations.stop(body["sessionId"]))
            elif path == "/api/dhcp/investigation/start":
                required = {"project", "clientNode", "clientPort", "serverNode",
                            "serverPort", "poolStart", "poolEnd", "leaseSeconds"}
                if not isinstance(body, dict) or set(body) not in (
                        required, required | {"difficulty"}):
                    raise ProjectValidationError(
                        "investigation start: expected client/server, pool, leaseSeconds, project and optional difficulty")
                self._json(200, self.server.investigations.start(
                    body["project"], body["clientNode"], body["clientPort"],
                    body["serverNode"], body["serverPort"], body["poolStart"],
                    body["poolEnd"], body["leaseSeconds"],
                    body.get("difficulty", "T1_ONLY")))
            elif path == "/api/dhcp/investigation/advance":
                if not isinstance(body, dict) or set(body) != {
                        "sessionId", "project", "seconds"}:
                    raise ProjectValidationError(
                        "investigation advance: expected sessionId, project, seconds")
                self._json(200, self.server.investigations.advance(
                    body["sessionId"], body["project"], body["seconds"]))
            elif path == "/api/dhcp/investigation/probe":
                required = {"sessionId", "project", "probe", "target"}
                if not isinstance(body, dict) or set(body) != required:
                    raise ProjectValidationError("investigation probe: expected sessionId, project, probe and target")
                self._json(200, self.server.investigations.probe(
                    body["sessionId"], body["project"], body["probe"], body["target"]))
            elif path == "/api/dhcp/investigation/diagnose":
                required = {"sessionId", "project", "diagnosis"}
                if not isinstance(body, dict) or set(body) != required:
                    raise ProjectValidationError("investigation diagnosis: expected sessionId, project, diagnosis")
                self._json(200, self.server.investigations.diagnose(
                    body["sessionId"], body["project"], body["diagnosis"]))
            elif path == "/api/dhcp/investigation/repair":
                if not isinstance(body, dict) or set(body) != {"sessionId", "project"}:
                    raise ProjectValidationError("investigation repair: expected sessionId and project")
                self._json(200, self.server.investigations.repair(body["sessionId"], body["project"]))
            elif path == "/api/dhcp/investigation/stop":
                if not isinstance(body, dict) or set(body) != {"sessionId"}:
                    raise ProjectValidationError("investigation stop: expected sessionId")
                self._json(200, self.server.investigations.stop(body["sessionId"]))
            elif path == "/api/dhcp/session/start":
                required = {"project", "serverNode", "serverPort", "poolStart", "poolEnd"}
                if not isinstance(body, dict) or set(body) != required:
                    raise ProjectValidationError(
                        "dhcp session start: expected project, serverNode, serverPort, poolStart, poolEnd")
                self._json(200, self.server.dhcp_sessions.start(
                    body["project"], body["serverNode"], body["serverPort"],
                    body["poolStart"], body["poolEnd"]))
            elif path == "/api/dhcp/session/run":
                required = {"sessionId", "project", "clientNode", "clientPort",
                            "transactionId", "leaseSeconds"}
                if not isinstance(body, dict) or set(body) != required:
                    raise ProjectValidationError(
                        "dhcp session run: expected sessionId, project, clientNode, clientPort, transactionId, leaseSeconds")
                self._json(200, self.server.dhcp_sessions.run(
                    body["sessionId"], body["project"], body["clientNode"],
                    body["clientPort"], body["transactionId"], body["leaseSeconds"]))
            elif path == "/api/dhcp/session/port-fault":
                required = {"sessionId", "project", "nodeId", "portId", "disabled"}
                if not isinstance(body, dict) or set(body) != required:
                    raise ProjectValidationError(
                        "dhcp session port-fault: expected sessionId, project, nodeId, portId, disabled")
                self._json(200, self.server.dhcp_sessions.port_fault(
                    body["sessionId"], body["project"], body["nodeId"],
                    body["portId"], body["disabled"]))
            elif path == "/api/dhcp/session/vlan-fault":
                required = {"sessionId", "project", "nodeId", "portId", "vlanId"}
                if not isinstance(body, dict) or set(body) != required:
                    raise ProjectValidationError(
                        "dhcp session vlan-fault: expected sessionId, project, nodeId, portId, vlanId")
                self._json(200, self.server.dhcp_sessions.vlan_fault(
                    body["sessionId"], body["project"], body["nodeId"],
                    body["portId"], body["vlanId"]))
            elif path == "/api/dhcp/session/link-fault":
                required = {"sessionId", "project", "linkId", "disabled"}
                if not isinstance(body, dict) or set(body) != required:
                    raise ProjectValidationError(
                        "dhcp session link-fault: expected sessionId, project, linkId, disabled")
                self._json(200, self.server.dhcp_sessions.link_fault(
                    body["sessionId"], body["project"],
                    body["linkId"], body["disabled"]))
            elif path == "/api/dhcp/session/renew":
                required = {"sessionId", "project", "clientNode", "clientPort", "transactionId"}
                if not isinstance(body, dict) or set(body) != required:
                    raise ProjectValidationError(
                        "dhcp session renew: expected sessionId, project, clientNode, clientPort, transactionId")
                self._json(200, self.server.dhcp_sessions.renew(
                    body["sessionId"], body["project"], body["clientNode"],
                    body["clientPort"], body["transactionId"]))
            elif path == "/api/dhcp/session/advance":
                if not isinstance(body, dict) or set(body) != {"sessionId", "project", "seconds"}:
                    raise ProjectValidationError(
                        "dhcp session advance: expected sessionId, project, seconds")
                self._json(200, self.server.dhcp_sessions.advance(
                    body["sessionId"], body["project"], body["seconds"]))
            elif path == "/api/dhcp/session/reset":
                if not isinstance(body, dict) or set(body) != {"sessionId", "project"}:
                    raise ProjectValidationError("dhcp session reset: expected sessionId and project")
                self._json(200, self.server.dhcp_sessions.reset(
                    body["sessionId"], body["project"]))
            elif path == "/api/dhcp/session/stop":
                if not isinstance(body, dict) or set(body) != {"sessionId"}:
                    raise ProjectValidationError("dhcp session stop: expected sessionId")
                self._json(200, self.server.dhcp_sessions.stop(body["sessionId"]))
            elif path == "/api/dhcp/dora":
                required = {"project", "clientNode", "clientPort", "serverNode",
                            "serverPort", "poolStart", "poolEnd", "transactionId", "leaseSeconds"}
                if not isinstance(body, dict) or set(body) != required:
                    raise ProjectValidationError(
                        "dhcp dora: expected project, clientNode, clientPort, serverNode, "
                        "serverPort, poolStart, poolEnd, transactionId, leaseSeconds")
                # One isolated DORA session. Only a successful observed ACK
                # creates an in-memory simulated BOUND lease; no saved project
                # or host NIC configuration is modified.
                self._json(200, simulate_dora(
                    body["project"], body["clientNode"], body["clientPort"],
                    body["serverNode"], body["serverPort"], body["poolStart"],
                    body["poolEnd"], body["transactionId"], body["leaseSeconds"]))
            elif path == "/api/dhcp/discover-offer":
                required = {"project", "clientNode", "clientPort", "serverNode",
                            "serverPort", "proposedIpv4", "transactionId", "leaseSeconds"}
                if not isinstance(body, dict) or set(body) != required:
                    raise ProjectValidationError(
                        "dhcp: expected project, clientNode, clientPort, serverNode, "
                        "serverPort, proposedIpv4, transactionId and leaseSeconds")
                # DHCP bootstrap broadcast is intentionally bounded separately
                # from regular unicast IPv4 forwarding. One real L2 fabric.
                self._json(200, discover_offer(
                    body["project"], body["clientNode"], body["clientPort"],
                    body["serverNode"], body["serverPort"], body["proposedIpv4"],
                    body["transactionId"], body["leaseSeconds"]))
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

    def do_OPTIONS(self) -> None:
        # This local API deliberately offers no cross-origin CORS access.
        self._json(HTTPStatus.FORBIDDEN, {
            "error": "FORBIDDEN", "message": "CORS preflight is not allowed"})

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
