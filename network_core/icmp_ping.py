"""RFC 792 Echo Request/Reply over one shared real simulated IPv4/ARP/L2 state.

PING_REPLY requires TWO actual datagram deliveries, not a connected graph or
single outbound path. No synthetic RTT, ICMP Time Exceeded, or default route.
"""
from __future__ import annotations

from .icmp import ICMPEcho, ICMP_ECHO_REQUEST, ICMP_ECHO_REPLY
from .ipv4 import IPv4Trace
from .ipv4_packet import ICMP_PROTOCOL
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

        def result(status: str, meaning: str, reply: dict | None = None) -> dict:
            return {
                "status": status,
                "meaning": meaning,
                "request": request,
                "reply": reply,
                "identifier": identifier,
                "sequence": sequence,
                "replyMatched": status == "REPLIED",
                "rttMs": None,
                "ephemeral": True,
                "macTables": self.trace.fabric.learned_mac_tables(),
            }

        if request["status"] != "DELIVERED":
            return result("REQUEST_FAILED",
                          f"Echo Request not delivered ({request['status']}); no reply generated.")

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
