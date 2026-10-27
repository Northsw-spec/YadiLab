# YadiLab Living Topology & Visual Simulation Specification v1.0

**Status:** AUTHORITATIVE ARCHITECTURE ADDENDUM — UI / topology / visualization layer  
**Applies to:** YadiLab v1.1.0 and later unless explicitly superseded  
**Does not modify:** YadiLab v1.0.0 VERIFIED PRODUCT RELEASE bytes or hash  
**Does not replace:** YadiLab Masterprompt v1.3 VERIFIED  
**Relationship to v1.0.1:** v1.0.1 remains a narrow topology overlap/layout bug-fix release candidate; the visual expansion defined here belongs to v1.1.0+.

---

## 1. Architectural role

YadiLab Masterprompt v1.3 remains the authoritative contract for product truth, schemas, engines, determinism, offline operation, fault injection, evidence, state and security semantics.

This document is the authoritative contract for **how that truth is projected into the main topology / visual simulation surface**.

The presentation layer MUST NOT invent state merely to make the interface look active. It visualizes only:

- declared scenario state;
- deterministic engine decisions;
- modeled protocol state;
- deterministic fault state;
- evidence produced by YadiLab;
- explicit configured/inferred/expected state when provenance is shown;
- future live-connector state only when a connector explicitly supplies it.

The relationship is:

```text
SCENARIO / FAULT / OBSERVATION STATE
              ↓
        YADILAB ENGINES
              ↓
    DETERMINISTIC EVENT MODEL
              ↓
    VISUAL PROJECTION LAYER
              ↓
 LIVING TOPOLOGY / JOURNEY / TABLES
              ↓
      EVIDENCE / WHY / PROOF
```

The visualization layer MUST NEVER become a second source of truth.

---

## 2. Product vision — the network must look alive

The topology canvas is not a static diagram editor. It is a **Living Topology**.

The user should be able to look at the canvas and immediately understand:

1. what exists;
2. what is connected;
3. what is active;
4. what a packet/frame/message is doing;
5. which table or policy decision caused the next step;
6. where and why a flow succeeds, changes, waits, retries, reroutes or fails;
7. what changed after a fault or remediation;
8. which evidence in the right-side panel proves what is shown.

The target visual character is the established Dan-project language from Dan Packet Lab and Dan Network Analyzer Local Host:

- dark professional canvas;
- rich but controlled blue/cyan base palette;
- green / amber / red / purple semantic states;
- colored traffic lanes and directional arrows;
- visible device identity;
- meaningful motion;
- high information density;
- no decorative animation that lies;
- no childish gamification;
- optional deep technical overlays without cluttering the default view.

The topology is the **SEE IT** surface.  
The existing right-side evidence/diagnostic panel is the **PROVE IT / WHY** surface.

Both MUST describe the same deterministic state.

---

## 3. Non-negotiable truth rules

### 3.1 Animation must communicate mechanics

Animation is allowed only when it communicates a modeled event such as:

- packet/frame/message creation;
- ARP/ND resolution;
- DNS lookup;
- route lookup;
- MAC learning;
- flooding;
- VLAN tagging/untagging;
- firewall or ACL evaluation;
- NAT/PAT translation;
- queueing;
- retransmission;
- timeout;
- route convergence;
- failover;
- service response;
- authentication;
- remediation;
- packet drop;
- interface or device state change.

A moving dot with no semantic relationship to the engine is prohibited.

### 3.2 No fabricated hidden infrastructure

YadiLab MUST NOT invent intermediate routers, switches, access points, physical paths, services, protocol exchanges or timing merely to make an animation complete.

Unknown remains unknown.

### 3.3 Provenance must remain visible

Where useful, visual states may be marked as:

```text
CONFIGURED
MODELED
OBSERVED
MEASURED
CORRELATED
INFERRED
EXPECTED
UNKNOWN
FAULT-INJECTED
REMEDIATED
```

Color alone MUST NOT be the only provenance indicator.

### 3.4 Same event, multiple renderers

A packet journey is one event stream. The user may choose different visual renderers without changing semantics:

- **PDU / envelope mode** — Packet-Tracer-like packet/envelope objects;
- **particle mode** — compact colored dots/particles;
- **flow-pulse mode** — luminous pulses along links;
- **directional-arrow mode** — animated arrows over the active path;
- **journey-lane mode** — Dan Packet Lab style horizontal protocol/traffic lanes;
- **reduced-motion mode** — static states + step transitions.

All renderers MUST replay the same deterministic event sequence.

---

## 4. Two primary visual projections

### 4.1 Topology Path view

The packet follows the actual topology edges and device interfaces.

Use for:

- routing;
- switching;
- segmentation;
- firewalling;
- NAT;
- path troubleshooting;
- fault injection;
- device/port inspection.

### 4.2 Journey Lanes view

The active communication is temporarily projected into a highly legible Dan Packet Lab style linear journey.

Example:

```text
CLIENT → SWITCH → ROUTER → FIREWALL → SERVER
  ARP      MAC      ROUTE      ACL       SERVICE
```

Use when topology complexity would otherwise hide causality.

The user can switch between Topology Path and Journey Lanes without changing the engine state or current timeline position.

---

## 5. Living device system

Every device type MUST have a distinctive professional visual identity.

Minimum built-in visual families:

- Windows workstation;
- Linux workstation;
- generic endpoint;
- Windows server;
- Linux server;
- domain controller / identity server;
- router;
- L2 switch;
- L3 switch;
- firewall;
- wireless AP;
- load balancer / reverse proxy;
- DNS server;
- DHCP server;
- VPN gateway;
- hypervisor;
- Proxmox-like virtualization host profile where enabled;
- VM;
- container/LXC;
- SIEM/log collector;
- IDS/IPS/NDR sensor;
- storage/backup server;
- cloud service/gateway;
- internet/external network;
- user / admin / attacker actor where relevant.

### 5.1 Device chassis and activity

Where state exists, a device may show:

- power/availability state;
- interface LEDs;
- link LEDs;
- activity LEDs;
- warning/fault LED;
- service-active indicator;
- firewall-policy activity;
- routing activity;
- CPU/queue pressure indicator only when modeled;
- selected/inspected state;
- fault-injected state;
- remediation-in-progress state.

LED animation MUST be bound to actual modeled activity; random blinking is prohibited.

### 5.2 Physical/logical ports

Ports/interfaces should be first-class visual anchors where the scenario supports them.

Possible visible labels:

```text
eth0
ens18
Gi0/1
VLAN 20
WAN
LAN
mgmt0
vmbr0
vnet3
wlan0
```

The user may toggle between compact device mode and port-detail mode.

---

## 6. Links must carry meaning

A link is not merely a line.

A link may encode:

- adjacency;
- Ethernet segment;
- access VLAN;
- trunk;
- routed interface;
- LAG/LACP bundle;
- wireless association;
- tunnel;
- VPN;
- management path;
- service dependency;
- authentication path;
- logical trust;
- replication/backup path;
- telemetry path.

### 6.1 Link activity

Active links may show:

- moving packets/particles;
- directional arrows;
- animated flow pulses;
- throughput thickness where modeled;
- delay animation where modeled;
- queue/backpressure state;
- loss/drop markers;
- duplex direction;
- protocol coloring;
- VLAN color bands;
- tunnel wrapping / outer-inner path indication.

Inactive links remain visually quiet.

### 6.2 Link-state effects

Show visually:

- up/down;
- administratively disabled;
- degraded;
- member of LAG;
- blocked by STP;
- standby path;
- failed path;
- alternate path selected after failure;
- wireless signal/association state where modeled.

---

## 7. Semantic color and motion language

The exact palette may evolve, but semantic meaning MUST remain stable.

Recommended Dan-style semantics:

- **cyan/blue** — ordinary active transport / network forwarding;
- **green** — verified success / reply / permitted / healthy;
- **amber** — discovery / lookup / pending decision / warning / degraded;
- **red** — deny / drop / fault / reset / failed verification;
- **purple** — application / identity / encrypted or higher-level semantic event;
- **teal** — management/control-plane state;
- **gray** — inactive / unknown / not evaluated;
- **white highlight** — current selected timeline event.

Do not encode critical meaning by color alone. Use icons, labels, stroke style and motion patterns too.

---

## 8. Packet / PDU visual system

The user can choose how traffic appears.

### 8.1 PDU / envelope mode

Shows a small packet/envelope icon traveling along the route.

Optional badge:

```text
ARP
DNS
SYN
SYN/ACK
HTTP
ICMP
TLS
DHCP
RST
```

### 8.2 Particle mode

Uses small colored particles for high-density flows.

Useful for:

- many packets;
- broadcast/flooding;
- throughput demonstrations;
- simultaneous conversations.

### 8.3 Flow-pulse mode

Shows the path itself illuminating segment-by-segment.

Useful for:

- diagnostics;
- route visualization;
- accessibility;
- high-level demonstrations.

### 8.4 Packet inspection on pause

Pausing a journey should allow inspection of the current PDU at the supported abstraction level:

- Ethernet source/destination;
- EtherType;
- VLAN tag;
- IPv4/IPv6 addresses;
- TTL/Hop Limit;
- protocol / next header;
- ICMP type/code;
- TCP ports/flags/sequence/ack/window/MSS where modeled;
- UDP ports/length;
- DNS fields;
- DHCP fields;
- application metadata supported by the scenario.

Do not display fields that the active capability does not model.

---

## 9. Packet lifecycle animations

A journey may visibly show:

1. application/service requests communication;
2. DNS lookup if needed;
3. source chooses destination address;
4. route lookup occurs;
5. selected route row highlights;
6. local/remote subnet decision occurs;
7. ARP/ND lookup occurs;
8. neighbor cache is read or populated;
9. Ethernet frame is built;
10. switch learns source MAC;
11. switch chooses unicast/flood/broadcast behavior;
12. VLAN tags are applied/removed where appropriate;
13. router receives and decapsulates L2 frame;
14. TTL/Hop Limit changes;
15. route lookup occurs on router;
16. ACL/firewall policy is evaluated;
17. NAT/PAT may rewrite address/port;
18. frame is rebuilt for next segment;
19. queue/QoS behavior may occur;
20. packet reaches destination interface;
21. local firewall/listener/service decision occurs;
22. response is generated or failure returned;
23. return path is visualized;
24. state tables are updated;
25. evidence pane synchronizes with each event.

Only applicable steps are shown.

---

# 10. EVERYTHING SHOULD BE VISUALIZABLE

The following sections define the target visualization coverage. Not every scenario needs every capability; when a capability exists in state, YadiLab should have a visual projection for it.

---

## 10.1 Layer 1 / link / physical-adjacent state

Where modeled, visualize:

- interface up/down;
- administrative state;
- speed;
- duplex;
- MTU;
- link member state;
- media/profile type;
- error counters;
- CRC/FCS errors;
- RX/TX drops;
- carrier loss;
- interface flapping;
- link aggregation member state;
- LACP active/standby member;
- wireless association;
- wireless signal quality;
- channel/interference state if modeled;
- virtual cable / bridge relationship;
- unplugged/disconnected state.

Example visualizations:

- port LED turns off;
- link becomes dashed/red;
- packet stops at sending interface;
- error counter badge increments;
- active LAG members glow while failed member dims.

---

## 10.2 Ethernet / Layer 2

Visualize:

- Ethernet frame source/destination MAC;
- MAC/CAM forwarding table;
- MAC learning;
- MAC aging;
- MAC move/flap;
- known unicast;
- unknown-unicast flooding;
- broadcast;
- multicast where modeled;
- ARP request/reply;
- IPv6 Neighbor Solicitation/Advertisement;
- neighbor cache;
- VLAN membership;
- access VLAN;
- tagged/untagged frames;
- 802.1Q trunk;
- native VLAN where modeled;
- inter-VLAN boundary;
- STP root bridge;
- STP root/designated/alternate port roles;
- STP forwarding/blocking/discarding state;
- BPDU/control-plane events where modeled;
- loop/flood-storm visualization;
- LACP/LAG;
- LLDP/CDP-like neighbor relationship when declared;
- port security / allowed MAC state where supported;
- storm-control effect where supported;
- IGMP/multicast membership/snooping where supported.

### Required table overlays

- MAC/CAM table;
- ARP/neighbor table;
- VLAN table;
- trunk/access-port table;
- STP state table;
- LACP bundle/member table;
- interface counters.

Table rows MUST highlight exactly when they cause the visual forwarding decision.

---

## 10.3 IP / Layer 3

Visualize:

- IPv4/IPv6 addressing;
- connected networks;
- subnet boundaries;
- default gateway;
- route lookup;
- route candidates;
- longest-prefix match;
- route metric/preference;
- selected next hop;
- outgoing interface;
- RIB vs FIB distinction where modeled;
- recursive next-hop resolution where modeled;
- static routes;
- default routes;
- blackhole/unreachable/prohibit-style routes where modeled;
- policy routing where modeled;
- ECMP/multiple next hops where modeled;
- VRF/logical routing domains;
- route leaking where modeled;
- first-hop redundancy state where modeled;
- TTL/Hop Limit decrement;
- ICMP Time Exceeded;
- ICMP Destination Unreachable;
- traceroute hop progression;
- route withdrawal;
- alternate-route convergence;
- OSPF adjacency/route changes where modeled;
- BGP session/route advertisement where modeled;
- other control-plane route protocols through capability adapters.

### Required overlays

- routing table;
- forwarding table where distinct;
- policy-routing rules;
- VRF table selector;
- route-decision explanation;
- route-diff before/after fault or remediation.

A route lookup should visibly highlight every relevant candidate, then the winning route.

---

## 10.4 NAT / stateful middleboxes

Visualize:

- SNAT;
- DNAT;
- PAT;
- static NAT;
- translated source/destination address;
- translated port;
- return mapping;
- state table entry creation;
- state expiry;
- hairpin NAT where modeled;
- asymmetric path impact where modeled.

Required overlays:

- NAT/PAT table;
- conntrack/session table;
- original tuple → translated tuple;
- reverse tuple.

The packet icon should visibly transform at the NAT decision point.

---

## 10.5 Firewall / ACL / security policy

Visualize:

- ordered ACL evaluation;
- firewall rule evaluation;
- zone transition;
- permit;
- deny;
- reject/reset;
- silent drop;
- stateful allow due to established session;
- default deny;
- rule shadowing where modeled;
- service/object-group expansion where modeled;
- local host firewall vs network firewall distinction;
- segmentation boundary;
- management-plane restriction;
- IPS/IDS/NDR decision where modeled.

Required overlays:

- rule list;
- evaluated rules;
- matched rule;
- hit counter;
- session/conntrack state;
- reason for decision.

A DROP must occur visually at the actual policy decision point, not at the final destination.

---

## 10.6 DHCP / addressing lifecycle

Visualize:

- DHCP Discover;
- Offer;
- Request;
- ACK;
- NAK where modeled;
- lease assignment;
- renewal;
- expiry;
- fallback/no-address state;
- gateway option;
- DNS option;
- subnet mask/prefix;
- duplicate/conflict detection where modeled;
- relay/helper traversal where modeled.

Required overlays:

- lease table;
- client interface configuration before/after;
- DHCP options relevant to connectivity.

---

## 10.7 DNS / name-resolution lifecycle

Visualize:

- hostname request;
- resolver selection;
- cache hit/miss;
- A/AAAA query;
- CNAME chain;
- referral/recursive chain where modeled;
- response;
- NXDOMAIN;
- timeout;
- SERVFAIL where modeled;
- TTL/cache expiry;
- UDP query;
- truncation/TC flag;
- TCP retry;
- DNSSEC status where modeled;
- split-horizon / internal vs external answer where modeled.

Required overlays:

- configured resolvers;
- DNS cache;
- current resolution chain;
- answer set;
- TTL countdown when useful.

Once an address is resolved, the visual story should transition directly into the network journey.

---

## 10.8 TCP

Visualize, where capability/state supports it:

- SYN;
- SYN/ACK;
- ACK;
- ESTABLISHED;
- data transfer;
- FIN/ACK close;
- RST;
- LISTEN;
- SYN-SENT;
- SYN-RECEIVED;
- CLOSE-WAIT;
- TIME-WAIT;
- retransmission;
- duplicate ACK;
- SACK;
- out-of-order arrival;
- sequence/ack progress;
- MSS;
- receive window;
- zero window;
- window probe;
- delayed ACK;
- keepalive;
- half-open session;
- RTO/backoff;
- congestion-control phases where modeled;
- connection refused vs timeout distinction.

Required overlays:

- TCP state machine;
- socket/session row;
- sequence/ack timeline;
- retransmission markers.

---

## 10.9 UDP / QUIC / ICMP

Visualize:

### UDP
- stateless datagram send;
- receive;
- no-listener ICMP response;
- silent no-response condition;
- checksum failure where modeled.

### QUIC / HTTP/3
- UDP transport;
- connection setup;
- encrypted streams;
- independent stream activity where modeled.

### ICMP
- Echo Request/Reply;
- Destination Unreachable;
- Port Unreachable;
- Time Exceeded;
- Fragmentation Needed / Packet Too Big;
- redirects only where explicitly modeled;
- path diagnostics.

---

## 10.10 MTU / fragmentation / PMTUD

Visualize:

- packet size relative to interface/link MTU;
- fragmentation where allowed;
- fragment count/order;
- DF behavior;
- ICMP Fragmentation Needed;
- IPv6 Packet Too Big;
- source reducing payload/segment size;
- black-holed PMTUD failure where modeled;
- MSS adaptation;
- reassembly at destination.

A packet that is too large should visibly collide with the MTU constraint and either fragment, trigger an ICMP response, or fail according to modeled semantics.

---

## 10.11 Sockets / processes / host network stack

Provide a **Host Stack microscope**.

Visualize:

```text
Application / Process
        ↓
      Socket
        ↓
 Local Firewall
        ↓
 Route Lookup
        ↓
 Neighbor Resolution
        ↓
 Interface / NIC
        ↓
      Network
```

Where modeled, show:

- process name/PID;
- listening socket;
- local IP/port;
- remote IP/port;
- protocol;
- socket state;
- service binding;
- wildcard vs specific interface bind;
- loopback vs external bind;
- local firewall decision;
- outgoing interface;
- owning service.

Required overlays:

- listening ports;
- active sockets;
- process-to-socket mapping;
- service status;
- interface configuration;
- local routing table.

---

## 10.12 Application/service protocols

Where the scenario models them, the visual layer should support protocol-specific events without requiring full protocol emulation.

Examples:

- HTTP request/response;
- HTTPS dependency chain;
- TLS handshake/certificate state;
- SSH connection;
- RDP connection;
- SMB access;
- LDAP/LDAPS;
- Kerberos-style authentication path at supported abstraction;
- SMTP/mail flow;
- NTP;
- database client/server connection;
- API request;
- backup/replication traffic;
- telemetry/log shipping.

The visualization should distinguish:

```text
NETWORK REACHABILITY
TRANSPORT ESTABLISHMENT
SERVICE LISTENER
APPLICATION SUCCESS
AUTHENTICATION/AUTHORIZATION
```

A green network path MUST NOT imply application success unless evidence supports it.

---

## 10.13 TLS / encryption visibility

Where modeled, visualize:

- plaintext vs encrypted portion;
- TLS handshake stage;
- certificate presentation;
- certificate validation result;
- hostname mismatch;
- expired/untrusted certificate;
- protocol/cipher policy where modeled;
- tunnel encryption boundary;
- inner vs outer packet for VPN/tunnel visualization.

Encryption should be shown as a semantic wrapper, not by pretending encrypted payload contents are known.

---

## 10.14 QoS / queues / congestion / performance

Where modeled, visualize:

- queue occupancy;
- enqueue/dequeue;
- queue drops;
- priority classes;
- DSCP/class marking;
- shaping/policing;
- bandwidth cap;
- saturation;
- latency;
- jitter;
- loss;
- retransmission consequences;
- bufferbloat-style delay where modeled;
- congestion-control reaction.

Possible rendering:

- packet slows as it enters a queue;
- queue bar fills;
- packets wait in order;
- drop-tail or policy drop is shown at the queue;
- link thickness reflects modeled utilization.

---

## 10.15 Tunnels / VPN / overlays

Visualize:

- tunnel endpoints;
- inner packet;
- encapsulation into outer packet;
- encrypted tunnel wrapper;
- route into tunnel;
- tunnel up/down;
- peer state;
- split tunnel vs full tunnel;
- allowed prefixes;
- route overlap;
- tunnel MTU effects;
- decapsulation.

Potential adapters:

- generic IP tunnel;
- GRE;
- IPsec;
- WireGuard;
- site-to-site VPN;
- remote-access VPN;
- overlay networks.

Specific protocol detail only when modeled.

---

## 10.16 Virtualization / bridges / containers

YadiLab should visualize virtual networking as first-class topology, especially for Proxmox-oriented labs.

Where modeled, show:

- hypervisor;
- VM;
- LXC/container;
- vNIC;
- tap/veth;
- Linux bridge;
- vSwitch;
- VLAN-aware bridge;
- bond/LAG;
- virtual firewall/router;
- management bridge;
- storage/backup network;
- NAT/masquerade boundary;
- host-only/isolation boundary;
- VM-to-VM path on same host;
- path leaving the hypervisor;
- snapshot/rollback event relationship where relevant.

Packets moving between two VMs on the same virtual switch should not be drawn as leaving the host unless the modeled topology says they do.

---

## 10.17 Identity / authentication / authorization

YadiLab is not only networking. Identity flows should also become visual when the Identity Engine participates.

Visualize, at supported abstraction:

- user → endpoint → identity provider;
- authentication request;
- MFA challenge;
- group/role lookup;
- authorization decision;
- service account use;
- trust/delegation edge;
- privilege path;
- deny due to policy;
- session creation;
- session expiry/revocation;
- effective permissions;
- identity-related lateral movement path in security labs.

Possible overlays:

- group membership graph;
- role/permission table;
- access policy decision;
- session list;
- trust relationships.

Do not pretend to emulate Kerberos/NTLM/LDAP token internals unless the capability explicitly models them.

---

## 10.18 Security telemetry / detection / response

Where YadiLab scenarios include security components, visualize:

- sensor/agent telemetry path;
- log shipping;
- detection event;
- correlated evidence;
- firewall block;
- IDS/IPS alert;
- endpoint isolation;
- process kill where supported by scenario model;
- account disable;
- containment boundary;
- before/after reachability after response;
- affected blast radius.

Security visualization must preserve evidence vs inference.

---

## 10.19 Fault injection / diagnostics / remediation

Faults should be visually obvious and causally localized.

Examples:

- wrong default gateway;
- route removed;
- blackhole route;
- DNS failure;
- DHCP failure;
- interface down;
- VLAN mismatch;
- STP/loop issue;
- firewall rule deny;
- NAT mapping fault;
- service down;
- listening port removed;
- MTU mismatch;
- excessive loss/latency;
- duplicate address;
- tunnel down;
- broken authentication/authorization;
- failed dependency.

Required visual concepts:

- fault origin marker;
- affected path highlighted;
- blast-radius overlay;
- expected vs actual path;
- before/after state diff;
- remediation preview;
- remediation commit;
- after-evidence verification;
- rollback animation/state restoration.

The topology should be able to answer visually:

> Where did the failure originate?
> What did it affect?
> Which table/policy/state made the failure happen?
> What changed after remediation?

---

## 10.20 Configuration change visualization

When Builder or remediation changes state, visualize diffs.

Examples:

- route added/removed;
- firewall rule inserted;
- VLAN changed;
- service enabled;
- interface address changed;
- DNS resolver changed;
- NAT rule changed;
- role/group membership changed.

Use a before/after ghost representation and explicit delta badge.

Changes MUST remain distinguishable from traffic events.

---

## 10.21 Control plane vs data plane

Where applicable, YadiLab should visually distinguish:

- control-plane event;
- forwarding/data-plane event;
- management-plane event.

Examples:

- OSPF hello/adjacency vs user packet forwarding;
- STP BPDU vs Ethernet data frame;
- ARP/ND control exchange vs application traffic;
- SSH management connection vs user service traffic.

This prevents learners from confusing “network learning” traffic with application traffic.

---

## 10.22 Broadcast / multicast / one-to-many visualization

The topology must support branching journeys.

Examples:

- ARP broadcast;
- unknown-unicast flooding;
- DHCP Discover;
- IPv6 multicast neighbor discovery;
- multicast group delivery where modeled.

Animation should visibly split at the branching device and terminate at non-participating recipients according to semantics.

---

## 10.23 Return-path and asymmetry visualization

Forward and return paths may differ.

The UI should support:

- forward path color/line;
- return path color/line;
- path comparison;
- asymmetric routing warning;
- NAT/state implications;
- reverse firewall/state decision;
- different egress/ingress interfaces.

Do not assume symmetry.

---

## 10.24 Dependency graph visualization

Not every failure is a packet-routing failure.

YadiLab should visualize service dependencies such as:

```text
User → RDP service → DNS → Identity → Database
```

A dependency edge should be distinct from a physical/network adjacency edge.

The user can toggle:

- Network topology;
- Service dependencies;
- Identity/auth paths;
- Management paths;
- Telemetry paths;
- Backup/replication paths.

---

## 10.25 Hidden-state tables that must have visual representations

At minimum, future capability adapters should support visual overlays for:

- routing table / RIB;
- forwarding table / FIB;
- policy-routing rules;
- ARP cache;
- IPv6 neighbor cache;
- MAC/CAM table;
- VLAN table;
- trunk/access state;
- STP table;
- LACP/bond members;
- NAT/PAT table;
- conntrack/session state;
- firewall/ACL rules and hit counters;
- DHCP lease table;
- DNS resolver configuration;
- DNS cache;
- socket table;
- listening-port table;
- process ↔ socket mapping;
- service status;
- interface counters;
- QoS/queue state;
- tunnel/VPN peer and route state;
- identity sessions;
- group/role memberships;
- virtualization bridge/vNIC mappings;
- fault overlays;
- remediation delta;
- evidence/provenance timeline.

If a table exists in the modeled state, it should not be trapped only in text on the right panel; the topology should be able to call it up contextually at the relevant device.

---

## 11. Contextual table overlays

A table overlay can appear:

- beside the selected device;
- as a docked topology overlay;
- as a compact mini-table anchored to the device;
- expanded into a larger inspector.

### 11.1 Decision highlighting

When a packet reaches a device:

- the relevant table opens or pulses if enabled;
- candidate rows highlight;
- the selected row becomes dominant;
- the resulting action is drawn into the topology.

Example routing decision:

```text
10.0.0.0/8     via 192.0.2.1    eth1
10.20.0.0/16   via 192.0.2.9    eth2   ← WINNER
0.0.0.0/0      via 192.0.2.254  eth0
```

The winning route, next hop and egress interface should visually connect.

---

## 12. Failure and drop vocabulary

Failures must not all look the same.

### 12.1 Silent drop

Packet reaches decision point, turns red/dims and disappears without a generated response.

### 12.2 Reject / reset

Packet is denied and a response event is animated back to the sender.

### 12.3 No route

Route lookup fails; packet never leaves the routing decision point.

### 12.4 Blackhole route

Winning route is visibly a blackhole; packet is absorbed at route decision.

### 12.5 Link down

Packet attempts egress but link/interface is visibly unavailable.

### 12.6 VLAN/L2 mismatch

Frame reaches a switching boundary but cannot be delivered in the expected broadcast domain.

### 12.7 Service closed

Network path succeeds; destination transport layer generates RST/ICMP depending on protocol.

### 12.8 Service down / no listener

Differentiate from firewall filtering.

### 12.9 Timeout

Packet leaves source and no modeled valid response returns before timeout event.

### 12.10 MTU failure

Packet meets MTU boundary; show fragmentation, ICMP feedback, or failure as modeled.

### 12.11 Authentication / authorization failure

Network path can remain green while identity/application layer turns red/purple with explicit deny reason.

---

## 13. Arrival vocabulary

Successful arrival should also distinguish layers.

Possible states:

```text
L2 DELIVERED
L3 REACHABLE
TRANSPORT ESTABLISHED
SERVICE ACCEPTED
AUTHENTICATED
AUTHORIZED
APPLICATION SUCCESS
```

Do not collapse these into one generic green check.

---

## 14. Journey Player / Network Time Machine

The main topology must include a real timeline player.

Required controls:

- Play;
- Pause;
- Step Forward;
- Step Back;
- Replay;
- Restart;
- Jump to Event;
- timeline scrubber;
- 0.25×;
- 0.5×;
- 1×;
- 2×;
- 4×;
- follow active packet toggle;
- loop current journey toggle;
- compare before/after toggle where applicable.

At any timeline position, topology, tables, PDU detail and evidence panel MUST show the same event state.

---

## 15. Network Microscope — zoom/detail levels

YadiLab should provide multiple semantic zoom levels.

### Level 1 — Topology / Journey

```text
Client → Switch → Router → Firewall → Server
```

### Level 2 — Device / Interface

Show interfaces, VLANs, addresses, port states and active table decision.

### Level 3 — Host Stack

```text
Process → Socket → Firewall → Route → Neighbor → NIC
```

### Level 4 — L2/L3 Forwarding

Show frame rewrite, MAC learning, routing, TTL/Hop Limit, NAT and policy decisions.

### Level 5 — PDU / Protocol

Show Ethernet/IP/TCP/UDP/ICMP/DNS/DHCP/application fields supported by the current capability.

### Level 6 — Evidence / Causality

Show event provenance, before/after state, rule/table row, fault origin and verification evidence.

The user should be able to zoom deeper without losing the current journey event.

---

## 16. Ambient animation

When no focused journey is playing, the topology may still feel alive using lightweight deterministic signals:

- active connections pulse;
- current service links glow subtly;
- new session appears;
- closed session fades;
- route changes animate;
- interface state changes;
- DNS event briefly illuminates resolver path;
- faulted device pulses warning;
- remediation change briefly highlights affected state.

Ambient animation must remain low CPU and must have a pause/reduced-motion path.

---

## 17. Focus modes / clutter control

Because YadiLab may visualize everything, it must also let the user hide what is irrelevant.

Required focus filters should include:

- Active journey only;
- Network path;
- L2;
- L3 routing;
- Firewall/security;
- NAT/state;
- DNS/DHCP;
- Transport;
- Application;
- Identity;
- Virtualization;
- Faults;
- Changes;
- Telemetry;
- Management;
- All.

The UI should default to clarity, not maximum simultaneous overlays.

---

## 18. Path comparison modes

Support visual comparisons such as:

- healthy vs faulted;
- before vs after remediation;
- expected vs actual;
- forward vs return path;
- route A vs route B;
- VLAN before vs after change;
- permitted vs denied flow;
- working client vs broken client.

Ghost paths and split-color links can be used, but labels must explain differences.

---

## 19. Fault blast-radius visualization

When a fault is previewed or active, YadiLab should be able to show:

- fault origin;
- directly affected resources;
- transitively affected services/flows;
- unaffected resources;
- recovery target;
- expected after-state.

This is a visual projection of the existing fault/blast-radius engine state, not a new score.

---

## 20. Routing and switching “x-ray” modes

### Routing X-Ray

Show simultaneously:

- destination IP;
- candidate routes;
- prefix lengths;
- metrics/preferences;
- selected route;
- next hop;
- egress interface;
- ARP/ND dependency;
- NAT/firewall dependency if next.

### Switching X-Ray

Show simultaneously:

- ingress port;
- source MAC learned;
- destination MAC lookup;
- VLAN;
- forwarding/flooding decision;
- eligible egress ports;
- STP blocked ports;
- trunk tag changes.

These modes should be especially suitable for teaching.

---

## 21. Animated device internals

For selected devices, the UI may show a small exploded/inside view.

### Router

```text
Ingress NIC
   ↓
L2 decapsulation
   ↓
Route lookup
   ↓
ACL / Firewall / NAT
   ↓
TTL update
   ↓
Neighbor lookup
   ↓
Egress frame build
```

### Switch

```text
Ingress port
   ↓
Source MAC learn
   ↓
VLAN classify
   ↓
Destination MAC lookup
   ↓
STP / port eligibility
   ↓
Unicast / Flood / Drop
```

### Host

```text
Process
 ↓
Socket
 ↓
Local policy
 ↓
Routing
 ↓
Neighbor
 ↓
NIC
```

This is optional detail mode, not the default canvas.

---

## 22. Visual protocol stack

The existing right-side evidence is preserved, but the canvas may also show a compact stack for the current packet:

```text
Application  HTTP / DNS / SMB / ...
Transport    TCP / UDP / QUIC
Network      IPv4 / IPv6 / ICMP
Data Link    Ethernet / VLAN
Physical     modeled link
```

During encapsulation the layers can visually wrap around payload; during decapsulation they unwrap.

---

## 23. Multi-packet / concurrent-flow visualization

YadiLab should eventually support several simultaneous deterministic flows.

Requirements:

- distinguish conversations by color + ID;
- group repeated packets into a flow when detail is not needed;
- allow one flow to be focused while others dim;
- support broadcast/flood fan-out;
- show contention/queueing where modeled;
- avoid unreadable particle storms through aggregation.

---

## 24. Security and attack-path overlays

For security labs, the same topology can show:

- exposed service;
- initial access path;
- authentication path;
- privilege path;
- lateral movement relation;
- telemetry/detection path;
- containment action;
- restored segmentation.

Attack-related visualization must remain evidence/state-based and must not imply causality beyond modeled state.

---

## 25. Accessibility / reduced motion

The “flashy” visual identity must not make the product inaccessible.

Requirements:

- `prefers-reduced-motion` support;
- explicit Reduce Motion toggle;
- pause all continuous motion;
- color-blind-safe alternatives;
- icons/text in addition to color;
- high-contrast focus state;
- keyboard access to timeline and device/table overlays;
- no essential hover-only information.

Reduced-motion mode should preserve every semantic transition through static step states.

---

## 26. Performance rules

The visual layer must remain smooth without turning animation into a functional dependency.

Targets:

- animation isolated from engine logic;
- deterministic state update independent of frame rate;
- bounded particles;
- aggregation at high event volume;
- requestAnimationFrame for visual interpolation only;
- no logic that depends on animation completion;
- ability to disable ambient effects;
- preserve usable topology on modest Parrot/Linux hardware.

If rendering degrades, truth and interaction take priority over cosmetic effects.

---

## 27. Visual Event Model

Introduce a presentation-neutral event contract rather than hard-coding effects in React components.

Illustrative structure:

```json
{
  "eventId": "evt-0042",
  "sequence": 42,
  "kind": "route.selected",
  "sourceResourceId": "client1",
  "targetResourceId": "router1",
  "resourceId": "router1",
  "interfaceId": "lan0",
  "flowId": "flow-https-1",
  "protocol": "ipv4",
  "decision": {
    "table": "routing",
    "winnerId": "route-10.20.0.0-16",
    "reason": "longest-prefix-match"
  },
  "provenance": "MODELED",
  "evidenceRefs": ["ev-route-17"]
}
```

The event model must support at least these families:

```text
flow.*
packet.*
frame.*
interface.*
neighbor.*
mac.*
vlan.*
stp.*
route.*
vrf.*
nat.*
firewall.*
acl.*
conntrack.*
dhcp.*
dns.*
tcp.*
udp.*
icmp.*
mtu.*
queue.*
tunnel.*
service.*
socket.*
process.*
identity.*
security.*
fault.*
remediation.*
change.*
evidence.*
```

A renderer subscribes to events and creates motion; it does not decide network truth.

---

## 28. Visual adapter architecture — future-proof “visualize everything” rule

Every new engine capability that introduces user-relevant state SHOULD provide a visual adapter contract containing:

- resource renderer or badge;
- event renderer;
- contextual table/inspector;
- timeline representation;
- before/after diff support;
- provenance mapping;
- accessibility fallback;
- deterministic acceptance fixture.

Therefore future capabilities do not need changes to the core canvas architecture merely to become visible.

This is the mechanism that makes **“visualize everything”** sustainable rather than a one-time list.

---

## 29. Dan-style visual quality requirements

The topology should feel intentionally designed, not like default React Flow.

Required qualities:

- strong device silhouettes/icons;
- beautiful curved/orthogonal links where appropriate;
- subtle neon-like active path emphasis without excessive glow;
- polished semantic gradients only where they convey state;
- clear hierarchy;
- smooth but deterministic transitions;
- labels that remain readable while zooming;
- visual grouping by zones/VLANs/sites;
- contextual mini-tables;
- animated arrows/pulses;
- polished arrival/drop effects;
- visible interface activity;
- consistent Dan project visual language.

Avoid:

- generic rectangles connected by thin gray lines;
- random blinking;
- meaningless motion;
- excessive particle clutter;
- cartoon effects;
- decorative 3D that obscures data;
- visual success states unsupported by evidence.

---

## 30. Topology zone and layout rules

The v1.0.1 overlap defect establishes a permanent rule:

- zone headers have a reserved header inset;
- child nodes may never overlap zone title/subtitle/header controls;
- visual validation must test parent-header vs child-card collisions;
- animated overlays must not obscure labels permanently;
- contextual tables must avoid covering the active packet path where practical;
- layout must reserve space for expanded overlays or reposition them.

No future release may rely only on static box-inside-box validation.

---

## 31. Browser acceptance requirements

Release QA for the Living Topology must include real Chromium and Firefox tests.

At minimum test:

- no node overlap;
- no zone-header overlap;
- no clipped labels;
- path visible at supported zoom levels;
- packet/particle follows the correct semantic edge sequence;
- drop occurs at the correct decision device;
- successful arrival reaches the correct resource;
- route-table winner matches animation;
- MAC-table winner/flood set matches animation;
- firewall matched rule matches animation;
- NAT translation shown matches engine tuple;
- before/after fault path matches engine state;
- timeline scrub restores correct visual state;
- renderer mode switching does not alter semantics;
- reduced-motion mode remains fully understandable;
- no console/runtime errors;
- deterministic replay produces identical event sequence.

Screenshot/DOM visual acceptance should include representative labs for:

- healthy routed path;
- wrong gateway;
- firewall drop;
- NAT/PAT;
- VLAN + trunk;
- unknown-unicast flooding;
- STP failover;
- DNS then TCP;
- DHCP DORA;
- MTU/PMTUD;
- TCP retransmission;
- virtualization bridge path;
- fault preview/remediation comparison.

---

## 32. Vertical implementation plan for v1.1.0+

Do not build months of invisible framework first. Each phase must produce a usable visual capability.

### Phase A — Living Packet Journey

Deliver:

- deterministic Visual Event Model;
- active-path highlighting;
- directional arrows;
- PDU/envelope mode;
- particle mode;
- flow-pulse mode;
- arrival/drop effects;
- timeline Play/Pause/Step/Replay;
- evidence sync;
- healthy + firewall-drop + wrong-route demos.

This is the first required implementation after v1.0.1 is settled.

### Phase B — Real Device Visuals

Deliver:

- router/switch/firewall/server/client icons;
- interface/port anchors;
- link LEDs/activity;
- zone polish;
- compact port state;
- semantic link styling.

### Phase C — Routing & Switching X-Ray

Deliver:

- routing table overlay;
- route-candidate/winner animation;
- ARP/ND table;
- MAC/CAM table;
- MAC learn/flood/unicast;
- VLAN/trunk visualization;
- STP blocked/forwarding visualization.

### Phase D — Stateful Network Decisions

Deliver:

- firewall/ACL rule overlay;
- NAT/PAT transformation;
- conntrack/session table;
- local firewall vs network firewall distinction;
- forward/return path comparison.

### Phase E — Host Stack & Core Services

Deliver:

- process/socket/service view;
- DNS chain;
- DHCP DORA;
- listener/service state;
- TCP state machine;
- UDP/ICMP failure distinctions;
- MTU/PMTUD.

### Phase F — Time Machine / Fault Compare

Deliver:

- before/after ghost paths;
- fault origin;
- blast radius;
- remediation preview;
- after-evidence verification;
- timeline rewind;
- healthy vs faulted compare.

### Phase G — Deep & Extensible Visualizations

Deliver adapters for:

- QoS/queues;
- VPN/tunnels;
- virtualization;
- identity/auth;
- security telemetry;
- dynamic routing where modeled;
- advanced protocol capability packs.

---

## 33. Minimum v1.1.0 acceptance experience

A user should be able to open a lab and perform this exact flow without developer tools:

```text
1. Start a modeled HTTPS journey.
2. Watch DNS resolution if required.
3. See route lookup highlight its winning route.
4. See ARP/ND resolve the next hop.
5. Watch the packet cross the topology.
6. See the switch decision when applicable.
7. See firewall/NAT decisions when applicable.
8. Pause the packet at any decision point.
9. Open the relevant routing/MAC/ARP/firewall/NAT table in-place.
10. Inspect packet/PDU fields.
11. Read matching proof/evidence in the right panel.
12. Resume and watch arrival or drop.
13. Inject a deterministic fault.
14. Replay and visually see exactly where behavior diverges.
15. Preview remediation.
16. Commit remediation.
17. Replay and verify the changed path.
```

If this cannot be demonstrated from the packaged app, the first Living Topology milestone is not complete.

---

## 34. Architectural additions chosen by Chief Architect

The following are explicit additions beyond the previously stated Dan Packet Lab / DNA concepts and are now part of YadiLab's target visual architecture:

1. **Forward-vs-return path dual visualization** so asymmetric routing is visible.
2. **RIB/FIB/policy-routing differentiation** rather than a single generic routing-table view.
3. **Conntrack/session-state visualization** bound to firewall/NAT decisions.
4. **Queue/QoS/congestion visualization** including wait, shaping and queue drops where modeled.
5. **Control-plane vs data-plane visual distinction** to prevent conceptual confusion.
6. **Virtualization path visualization** for bridges, vNICs, veth/tap and VM/LXC traffic.
7. **Dependency graph overlay** so non-network service dependencies can fail visibly.
8. **Identity/authentication path visualization** integrated with network reachability.
9. **Before/after ghost topology and path diffs** for fault/remediation/change work.
10. **Contextual device-local tables** whose winning row physically connects to the resulting path.
11. **Branching journeys** for broadcast, flooding and multicast rather than forcing every journey into one line.
12. **Semantic arrival levels** (L2, L3, transport, service, auth, app) rather than one generic success state.
13. **Tunnel inner/outer packet visualization** to make overlays understandable.
14. **Capability-driven visual adapters** so future engines automatically have a defined route into the canvas.
15. **Truth-preserving reduced-motion renderer** so animation is optional but semantics are not.
16. **Multi-flow aggregation/focus** so the canvas can eventually show realistic concurrent activity without becoming noise.
17. **Device internal exploded views** for router, switch and host decision pipelines.
18. **Network microscope semantic zoom** that preserves the current timeline event while changing detail level.
19. **Failure-specific animation vocabulary** so firewall drop, no-route, RST, timeout, MTU, auth failure and service failure look different.
20. **Context-driven ambient activity** where links/devices subtly live only when actual modeled state justifies it.

---

## 35. Source lineage / design inheritance

This specification intentionally consolidates and extends ideas already established in prior Dan projects:

### Dan Packet Lab

Inherited concepts:

- topology/traffic canvas as visual hero;
- colored traffic lanes;
- directional arrows;
- device cards with technical identity;
- Traffic Story / Why This Happened / Live Protocol Stack / Packet Inspector style separation;
- Simulation Controls + Learning Progress timeline;
- topology-first WHAT / WHY / NEXT pedagogy;
- MAC learning, VLAN/trunking, routing, NAT, STP, PMTUD, TCP and many other deterministic labs.

Primary source artifacts:

- `MASTERPROMPT-DAN-PACKET-LAB*.md`
- `LAB-CATALOG*.md`
- `docs/DAN-PACKET-LAB-VISUAL-REFERENCE.png`
- `Dan-Packet-Lab-v1.2.0-VISUAL-ACCEPTANCE-CANDIDATE.zip`

### Dan Network Analyzer Local Host

Inherited concepts:

- animation must communicate mechanics, not decoration;
- ambient / diagnostic / training / experimental animation categories;
- Journey Player;
- Network Time Machine;
- semantic zoom / Network Detail View;
- live TCP state visualization;
- DNS + ARP/NDP laboratories;
- packet inspection / Packet Weld / Packet Tweak concepts;
- evidence/provenance truth discipline.

Primary source artifact:

- `DAN_NETWORK_ANALYZER_LOCAL_HOST_MASTERPROMPT_VERTICAL_FEATURE_CHECKPOINTS_v5.md`

### YadiLab Masterprompt v1.3 VERIFIED

Preserved constraints:

- deterministic engine truth;
- component-based topology;
- semantic connections;
- zones;
- deterministic auto-layout;
- routes/metrics;
- VLANs;
- VRFs;
- tunnels/VPN;
- NAT;
- ACL/firewall;
- services/listening ports;
- DNS/DHCP relationships;
- MTU/PMTUD;
- deterministic latency/loss/link-state semantics;
- neighbor/ARP-style reachability;
- semantic packet/evidence journey;
- no false packet-emulator claims.

---

## 36. Final binding principle

> **If YadiLab knows it, the user should be able to see it.**

But:

> **If YadiLab does not know it, the UI must not invent it.**

The Living Topology must become the primary visual explanation of YadiLab's deterministic world: beautiful, colorful, animated, technically rigorous, evidence-linked and capable of showing not only where traffic moves, but exactly **why** every meaningful state transition happens.

