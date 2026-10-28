# NMAP-XML-PREP-001 — source-grounded independent fixtures BEFORE parser

**Status:** Research/fixtures only. **Nmap XML is NOT an enabled YadiLab import format.**
**Only code authority:** Current GitHub `main`, snapshot when this branch was created: `9a426cbc147b8863e1782bf6ef4df9838c53ac21`. Future implementation MUST reread latest `main`; this SHA is NOT a future pinned base.

## Primary specifications (Nmap project)

- Nmap XML (`-oX`): https://nmap.org/book/output-formats-xml-output.html
- Nmap output manual: https://nmap.org/book/man-output.html
- Nmap DTD: https://nmap.org/book/app-nmap-dtd.html
- Nmap stylesheet processing instruction: https://nmap.org/book/output-formats-output-to-html.html

Nmap exports may contain `<?xml-stylesheet ...?>` and a DOCTYPE referencing a DTD. **Never fetch a stylesheet, DTD or entity** in the browser, Linux runtime, CI or tests. Our current `enterprise-import/src/xml-lite.ts` rejects non-XML processing instructions and ALL DTD declarations. That is a deliberate current security boundary, not a defect. Any future Nmap-specific header parser must be independently reviewed and bounded; generic `parseSafeXml` protections MUST remain active. We explicitly do not promise full Nmap producer compatibility at this preparation step.

## Semantic contract

- Track: **EVIDENCE_OBSERVED**, not `TOPOLOGY_DECLARED`.
- A `host` is a **scan record**, not proof of a physical device, asset identity, operating system or network connection.
- `status state="up"/"down"` is the scan-time **observation**, not guaranteed present reachability.
- `port state="open"/"closed"/"filtered"` is scan-time observation, NOT an Engine test result, firewall policy or guaranteed persistent service.
- `service` name, product/version, and `method/conf` are observations or guesses with their original qualifiers; NEVER verified software inventory without independent evidence.
- Hostnames and addresses are **reported identifiers**, not authoritative identity or topology. Multiple addresses or missing addresses must not cause invented merges.
- Nmap does NOT establish L1/L2 physical cables or full topology. Any graph link inferred from a route, shared subnet, port or traceroute is forbidden.
- No `ScenarioSource`, `EngineState`, active Builder change, green checkmark, `PASS`, verified physical link, route, credential or external command execution may be produced by a parser-only step.
- Preserve SHA-256 of original file and typed provenance at the scan, host ordinal and port ordinal. Format version/profile, observed host/port status and original source times must be explicit.
- Never run an Nmap scan, fetch remote hosts, query the Internet, execute NSE scripts or load external XML resources as part of importing an XML file.

## Initial proposed profile (NOT implemented)

`nmap.xml.observations.v1`: UTF-8 Nmap `nmaprun` root with `scanner="nmap"`, bounded file size, bounded host/port counts, IPv4 source address, TCP/UDP portid 1–65535, host status and port state. Unknown extensions should yield `UNSUPPORTED` or REVIEW_REQUIRED, not guessed facts. Unknown/sensitive script output remains unsupported; never serialize raw secret material into a published scenario package. An optional, syntactically exact `<?xml-stylesheet?>` prolog must be ignored without IO or executing its contents. **DTD headers: BLOCKED in the initial profile**, including Nmap's otherwise legitimate external DTD reference. Wider DTD compatibility requires separate documented protection against internal/external entities.

## PREP-001 independent fixtures and expected outcomes

| Fixture | Independent expected result |
|---|---|
| `valid-observed-hosts.xml` | 2 host observations: first UP with IPv4 192.0.2.10, TCP/22 OPEN with low-confidence table service name ssh, TCP/443 CLOSED; second DOWN at 192.0.2.11. Zero links, routes, Engine PASS or verified OS. |
| `valid-stylesheet-reference.xml` | 1 host UP at 198.51.100.50, TCP/80 OPEN. The `<?xml-stylesheet?>` processing instruction references a local file but MUST be ignored; no filesystem read occurs. The initial parser must implement this safely before claiming support. |
| `invalid-wrong-root.xml` | BLOCK wrong Nmap root; never interpret a Nessus XML document as Nmap. |
| `adversarial-external-dtd.xml` | BLOCK external DOCTYPE/DTD without any network request. |
| `adversarial-xxe.xml` | BLOCK internal entity / XXE without any local-file access or entity expansion. |
| `invalid-port-range.xml` | BLOCK portid 70000 outside valid 1–65535. |
| `invalid-duplicate-observation.xml` | BLOCK conflicting duplicate TCP/22 state in one host instead of taking first/last silently. |
| `invalid-malformed.xml` | BLOCK unbalanced XML. |
| `invalid-stylesheet-script.xml` | BLOCK nonallowlisted processing instruction; no script execution or network request. |

All addresses use TEST-NET ranges (RFC 5737), and names use reserved `.invalid` suffix. The fixtures are entirely synthetic, NOT real customer data. Other producer variants (IPv6, SCTP, OS fingerprints, traceroute, host/port scripts, complex service data, partial scans) remain **out of the initial declared subset** until explicitly specified and tested. The inability to parse a legitimate but unsupported file is an honest **UNSUPPORTED_PROFILE**, not permission to guess.

## Security gates BEFORE implementation status can advance

1. Real positive fixture parses with observed status and source metadata; no activation or networking.
2. All seven negative fixtures block with stable typed failure codes; no partial observation success on fatal parse errors.
3. A negative mutation test proves wrong-root, DTD and entity protection cannot be bypassed.
4. Versioned source locator round-trip and deterministic repeat parse; preserve exact SHA-256 from original bytes.
5. Hard file size, XML nesting, element-count, host-count and port-count limits with bounded parsing and memory.
6. No leakage of NSE script secrets, XML processing instructions or raw untrusted HTML into UI, logs, exports or scenario packages.
7. Existing five import adapters and GraphML tests unchanged; fail-closed format discovery still reports Nmap as NOT_IMPLEMENTED until actual reviewed adapter activation.
8. Browser real click, UI XSS safety and Parrot acceptance are separate gates. **Never conflate PR CI success with Parrot device acceptance.**

## Checkpoint sequence

- **NMAP-XML-PREP-001:** This document + fixtures only, no source parser.
- **NMAP-XML-P1:** strict `EVIDENCE_OBSERVED` read-only parser/typed locators and exhaustive negative tests, no UI change.
- **NMAP-XML-P2:** isolated file inspection and observation UI, no Engine truth.
- **NMAP-XML-P3:** provenance-aware linkage of user-confirmed observations to already-modeled assets, with conflicts and stale source checks; never update active Engine state automatically.
- **NMAP-XML-P4:** true browser, security, scale and Parrot acceptance independent of source assertions.

**No implementation PASS is asserted by this document.**
