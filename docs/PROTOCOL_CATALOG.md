# PROTOCOL-CATALOG — Cisco Packet Tracer och utökade protokoll
Status: SCOPE_ONLY; all implementations NOT_STARTED. Faktisk PT-binär och dess kompletta featurelista är NOT_VERIFIED. Officiell källa: https://tutorials.ptnetacad.net/help/default/intro.htm ; OT: https://tutorials.ptnetacad.net/help/default/industrial_otFeatures.htm .

## Cisco PT-funktioner – alla varianter och praktiska CLI-/GUI-underfall REQUIRED
- Ethernet 802.3, CSMA/CD (i PT:s modell), IEEE 802.1Q VLAN/trunk, STP/RSTP, VTP/DTP/PAgP, EtherChannel/LACP, multilayer switching, IP CEF, ARP.
- IPv4/IPv6, ICMP/ICMPv6, ND/SLAAC/RA, DHCP/DHCPv6, statisk och default routing, interVLAN.
- RIPv1/v2, EIGRP, OSPF single/multi-area, BGP, redistribution, policies och konvergens.
- TCP, UDP, DNS, HTTP/HTTPS, TFTP/FTP, SMTP/POP3, Telnet/SSH, VoIP/H.323, SNMP/NTP/Syslog.
- NAT/PAT/NATv6, ACL standard/extended/named, CBAC, zone firewall, IPS, GRE/IPsec/ISAKMP, AAA/RADIUS/TACACS, 802.1X där verifierat.
- WAN HDLC/SLARP/PPP/PPPoE/FrameRelay/DSL, 802.11 a/b/g/n och annan PT-stödd wireless/radio/cellular.
- QoS L2/L3, DiffServ, FIFO, Priority/Custom/Weighted-Fair Queuing, MQC/NBAR, NetFlow, CDP och PT-stödd management.
- PT9 industri: Modbus TCP, PROFINET, EtherNet/IP/CIP, OPC UA, IEC 61850, PTP/PRP, PLC/HMI/Historian/Cyber Observer, MCU/SBC och IoT script/protokoll.

Cisco anger uttryckligen betydande modellbegränsningar för flera protokoll. PT-output är jämförelse, inte standardsfacit. Varje variant ska ha konkret frame/packet/state/timer/error-orakel och fungerande device-/CLI-koppling.

## Mer än PT – efter käll- och gapsbevis
Kandidater: IS-IS, BFD, VRRP, MPLS/LDP, EVPN/VXLAN, SR-MPLS/SRv6, RESTCONF/NETCONF/gNMI, moderna Wi-Fi-varianter inklusive 802.11ax, QUIC/HTTP3, DNSSEC, DHCPv6 prefix delegation, RPKI, moderna OT-/TSN-/OPC UA-varianter och ytterligare protokoll som användare behöver. Dessa är extra ambitionsscope, INTE verifierat saknade i exakt aktuell Cisco-binär.

## Standardkällor
TCP RFC9293 https://www.rfc-editor.org/info/rfc9293/
IPv6 RFC8200 https://www.rfc-editor.org/info/rfc8200/
DHCPv6: RFC9915 (2026) ERSÄTTER RFC8415 https://www.rfc-editor.org/info/rfc9915/
OSPFv2 RFC2328 https://www.rfc-editor.org/info/rfc2328/
BGP4 RFC4271 https://www.rfc-editor.org/info/rfc4271/
DHCPv4 RFC2131 https://www.rfc-editor.org/info/rfc2131/
IEEE/IEC/ODVA-texter versions- och rättighetskontrolleras per implementation.

Krav per nytt protokoll: standardversion/errata, device/profile, parser/serializer, bytevektorer, state machine, timers/race, felexceptions, positiva/negativa/motsägande scenarier, metrik/budget, CLI state, exact commit SHA/CI och verifierad PT-run där paritet påstås. Dokumentation skapar aldrig VERIFIED_NATIVE.
