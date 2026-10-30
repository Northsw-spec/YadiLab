# CONVERGENCE — RFC 2328 Router-LSA / Network-LSA body structures

## Canonical source and normative basis

- Protected `main` at checkpoint start: `11cd7cd89c096da3b4280cff5c861e4fb2dd69b0`, tree `8107f23d842484690696fdc69a425b9e063f5325` (2026-10-30).
- RFC 2328 [Appendix A.4.2 Router-LSAs](https://www.rfc-editor.org/rfc/rfc2328.html#appendix-A.4.2), [A.4.3 Network-LSAs](https://www.rfc-editor.org/rfc/rfc2328.html#appendix-A.4.3), [§12.1.7 checksum](https://www.rfc-editor.org/rfc/rfc2328.html#section-12.1.7), [§12.4.1 link meanings](https://www.rfc-editor.org/rfc/rfc2328.html#section-12.4.1), [§12.4.2 network contents](https://www.rfc-editor.org/rfc/rfc2328.html#section-12.4.2).
- This checkpoint is **a bounded, pure byte/body parser**, not a writable LSDB, virtual adjacency, OSPF packet decoder, authenticated network evidence, topology certainty, SPF or a route installer. Every returned link is an **advertised field**, NOT a verified physical connection.

## Parser contract

Source file: `engine/src/ospf-lsa-body.ts`, new `parseOspfLsaBody` returning a versioned structural Type 1/2 result with immutable-by-copy byte and field arrays. It reuses unchanged `verifyOspfLsaBinary` for raw octet/length/header checks and RFC 2328 Fletcher integrity **before** decoding semantic fields. No checksum repairs, source normalization or inferred links. Failure is atomic with explicit diagnostic codes.

- Type 1 Router-LSA: 20-byte common header + V/E/B flags byte + zero-reserved byte + uint16 link count; each link has a 4-byte Link ID, 4-byte Link Data, type 1–4, TOS count and uint16 base metric. Parse each TOS extension as TOS octet, reserved zero octet and uint16 metric. Type 1 means neighboring router ID, 2 designated-router interface address, 3 stub network, 4 virtual link. Expose Link Data as **raw dotted 32-bit representation**, not guaranteed to be an IPv4 address because unnumbered point-to-point interfaces encode MIB-II ifIndex there. Preserve declared order and costs. Never infer bidirectional adjacency or construct graph edges from these values.
- Type 2 Network-LSA: 4-byte contiguous IPv4 mask after common header, then integral 4-byte Router ID records. Require at least one listed ID, unique nonzero IDs, and inclusion of Advertising Router (per RFC DR self-listing). Expose contiguous prefix length but never assert this LSA establishes an active transit network or that attached routers are physically reachable. Single DR listed is **structurally parsable** and does not prove valid origination with two-router adjacency.
- Treat reserved Router V/E/B higher bits and zero byte, invalid link type, zero router/transit Link ID, invalid stub mask, truncated link/TOS records, missing/extra bytes, TOS=0/repeated TOS or nonzero TOS reserved byte as invalid. Do not silently skip unknown link types or extensions.
- Guard explicit limits: at most **128 Type 1 links**, **16 legacy TOS records per link**, **128 Type 2 attached IDs** and existing raw **4096-byte** verification limit. RFC permits variable sized bodies, so length is checked from actually decoded records and reported count, never inferred from a fixed 24-byte Router body.
- These constraints are deliberately stricter than a byte-only parser for malformed payloads and intentionally do **not** certify originator eligibility, valid election of DR, route next hops, network reachability, MaxAge floods, topology connectivity, or database synchronization.

## Independent test oracles

- New test `tests/engine/run_ospf_lsa_body_tests.mjs` / `npm run test:ospf-lsa-body`; unconditionally added to both `yadilab-required-ci` for PR and `linux-attested` after merge.
- Test uses **fixed, independently computed Fletcher-16 byte vectors**: Router-LSA with all link types 1–4, V/E/B flags, one legacy TOS metric; zero-link Router-LSA; 2-attached Network-LSA; 1-attached structurally valid Network-LSA. Assert exact header lengths, metric and link order, IDs, masks and checksum octets.
- Negative fixtures are **re-Fletcher-sealed in the test** to demonstrate that a perfectly valid checksum/header can still contain illegal body fields. Test no silent invalid TOS, bad link counts, extra data, invalid masks/DR lists, duplicate/zero IDs, reserved flags, max link and attached-ID bounds, payload changes after result copying, unchanged Engine revision/resources/reachability and 1,000 deterministic byte-identical full positive/negative replays.
- Exact head checks must be SUCCESS in GitHub Actions and test logs must contain the actual `PASS CONVERGENCE OSPFv2 Router/Network LSA bodies` count before merging; independent postmerge Linux release must pass identical tests, mounted Chromium and artifact publication. Historic failed runs remain FAIL evidence. Ubuntu CI is accepted for this code gate, native Parrot acceptance NOT_RUN.

## Separately deferred

Persisting LSAs into a writable area-scoped LSDB, recency/MaxAge/MinLSArrival/flooding/acks, parse and authority of network-level OSPF packet frames, validated bidirectional router links, router/network LSA integration into a reliable SPF graph, route calculation/installation and real `FULL` neighbor state. None of these are implemented by adding this parser. Prior `REQUESTS_SATISFIED_MODEL` must not silently become `FULL`.
