"""RFC 792 Echo Request/Reply over one shared real simulated IPv4/ARP/L2 state.

PING_REPLY requires TWO actual datagram deliveries, not a connected graph or
single outbound path. No synthetic RTT, ICMP Time Exceeded, or default route.
"""
from __future__ import annotations

from .icmp import ICMPEcho, ICMP_ECHO_REQUEST, ICMP_ECHO_REPLY
from .ipv4 import IPv4Trace
from .ipv4_packet import ICMP_PROTOCOL
from .icmp_errors import ICMPError, parse_icmp_message, ICMP_TIME_EXCEEDED, ICMP_DEST_UNREACHABLE
from .model import ProjectValidationError

_ECHO_PAYLOAD = b"echo-check"


class EchoExchange:
    """Single Echo Request followed by its validated Echo Reply when supported."""

    def __init__(self, project: dict):
        self.trace = IPv4Trace(project)

    def ping(self, source_node: str, source_port: str, destination_ipv4: str,
             ttl: int, identifier: int, sequence: int) -> dict:
        # Validate the concrete Echo identity before any simulated work.
        request_message = ICMPEcho(ICMP_ECHO_REQUEST, identifier, sequence, _ECHO_PAYLOAD)
        request = self.trace.send(
            source_node, source_port, destination_ipv4, ttl,
            protocol=ICMP_PROTOCOL, payload=request_message.serialize(),
        )

        def attempt_router_error() -> dict | None:
            event = request["routerErrorCandidate"]
            if event is None:
                return None
            if request["status"] not in ("TTL_EXPIRED", "NO_ROUTE"):
                raise ProjectValidationError("icmp: unexpected router-error trigger")
            expected_type = (ICMP_TIME_EXCEEDED if request["status"] == "TTL_EXPIRED"
                             else ICMP_DEST_UNREACHABLE)
            if event["icmpType"] != expected_type:
                raise ProjectValidationError("icmp: wrong router-error type for observed failure")
            quote = bytes.fromhex(event["quotedIpv4Hex"])
            generated = ICMPError(expected_type, 0, quote)
            decoded = ICMPError.parse(generated.serialize())
            if (decoded != generated or decoded.quoted_source != request["sourceIpv4"]
                    or decoded.quoted_destination != request["destinationIpv4"]):
                raise ProjectValidationError("icmp: router-error quote failed validation")

            router = event["router"]
            ingress_port = event["ingressPort"]
            if self.trace.nodes[router]["kind"] != "router" or (
                    (router, ingress_port) not in self.trace.interfaces):
                raise ProjectValidationError("icmp: error generation requires observed router ingress")
            # First implementation deliberately sources from the observed
            # ingress IP and requires a reverse route out of that same port.
            # If routing chooses another interface, do not fake delivery.
            error_trace = self.trace.send(
                router, ingress_port, request["sourceIpv4"], 64,
                protocol=ICMP_PROTOCOL, payload=generated.serialize())
            error_info = {
                "status": "NOT_DELIVERED",
                "type": expected_type,
                "code": 0,
                "sourceNode": router,
                "sourcePort": ingress_port,
                "quotedSourceIpv4": decoded.quoted_source,
                "quotedDestinationIpv4": decoded.quoted_destination,
                "quotedProtocol": decoded.quoted_protocol,
                "trace": error_trace,
            }
            if error_trace["status"] != "DELIVERED":
                return error_info
            delivered = error_trace["deliveredDatagram"]
            if (delivered is None or delivered["protocol"] != ICMP_PROTOCOL
                    or delivered["destinationIpv4"] != request["sourceIpv4"]
                    or error_trace["receiver"] != {"node": source_node, "port": source_port}):
                error_info["status"] = "MISMATCH"
                return error_info
            received_error = parse_icmp_message(bytes.fromhex(delivered["payloadHex"]))
            if received_error != decoded or not isinstance(received_error, ICMPError):
                error_info["status"] = "MISMATCH"
                return error_info
            error_info["status"] = "RECEIVED"
            return error_info

        def result(status: str, meaning: str, reply: dict | None = None,
                   icmp_error: dict | None = None) -> dict:
            return {
                "status": status,
                "meaning": meaning,
                "request": request,
                "reply": reply,
                "icmpError": icmp_error,
                "identifier": identifier,
                "sequence": sequence,
                "replyMatched": status == "REPLIED",
                "rttMs": None,
                "ephemeral": True,
                "macTables": self.trace.fabric.learned_mac_tables(),
            }

        if request["status"] != "DELIVERED":
            error = attempt_router_error()
            return result("REQUEST_FAILED",
                          f"Echo Request not delivered ({request['status']}); no Echo Reply generated. "
                          + (f"ICMP router error: {error['status']}." if error else
                             "No router ICMP error packet was generated."),
                          icmp_error=error)

        delivered = request["deliveredDatagram"]
        if delivered is None or delivered["protocol"] != ICMP_PROTOCOL or (
                delivered["sourceIpv4"] != request["sourceIpv4"] or
                delivered["destinationIpv4"] != request["destinationIpv4"]):
            raise ProjectValidationError("icmp: delivered request lacks validated IPv4 identity")
        arrived = ICMPEcho.parse(bytes.fromhex(delivered["payloadHex"]))
        if arrived != request_message:
            raise ProjectValidationError("icmp: request payload changed before endpoint reception")

        receiver = request["receiver"]
        if self.trace.nodes[receiver["node"]]["kind"] not in ("host", "router"):
            return result("RESPONDER_UNSUPPORTED",
                          "Only explicit host/router interfaces model an ICMP Echo responder; firewall policy is unsupported.")

        # Response is generated only AFTER the real Echo Request reached an
        # address/MAC-matching port. Send from that exact port; return routing
        # must exist explicitly and follow the very same IPv4Trace/ARP/Fabric.
        reply_message = arrived.reply()
        reply = self.trace.send(
            receiver["node"], receiver["port"], request["sourceIpv4"], ttl,
            protocol=ICMP_PROTOCOL, payload=reply_message.serialize(),
        )
        if reply["status"] != "DELIVERED":
            return result("REPLY_FAILED",
                          f"Echo Request arrived, but Echo Reply not delivered ({reply['status']}).",
                          reply)

        returned = reply["deliveredDatagram"]
        if (returned is None or returned["protocol"] != ICMP_PROTOCOL or
                returned["sourceIpv4"] != request["destinationIpv4"] or
                returned["destinationIpv4"] != request["sourceIpv4"] or
                reply["receiver"] != {"node": source_node, "port": source_port}):
            return result("REPLY_MISMATCH",
                          "Received reply IP identity or receiving interface did not match the request.",
                          reply)
        echo = ICMPEcho.parse(bytes.fromhex(returned["payloadHex"]))
        if echo != reply_message or echo.icmp_type != ICMP_ECHO_REPLY or (
                echo.identifier != identifier or echo.sequence != sequence or
                echo.payload != request_message.payload):
            return result("REPLY_MISMATCH",
                          "Reply type, checksum, identifier, sequence or data did not match.",
                          reply)
        return result("REPLIED",
                      "Valid ICMP Echo Reply returned over configured IPv4 routes, ARP, links and VLANs. "
                      "No RTT measurement, transport service or external connectivity implied.",
                      reply)
