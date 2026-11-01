# AUDIT-007 P3 — frozen network-address correctness oracles

**Authority:** owner-approved correctness-first gate, protected main `e222a2154c1fcebd2084f03a421abc8dbce45759`, [issue #96](https://github.com/Northsw-spec/YadiLab/issues/96). Freeze this contract **before** editing `engine/src/ip.ts` or `enterprise-model/src/validation.ts`. Prior P1/P2a/P2b are already merged; do not redo them.

## Source-grounded defects and scope

1. `engine/src/ip.ts:parseIpAddress` silently strips every suffix after `/` without validating it. An interface text such as `192.0.2.7/garbage` can become a valid host and `addressInCidr` can return TRUE. Explicit valid host/mask notation, including `192.0.2.7/24` and `2001:db8::7/64`, must remain supported.
2. `enterprise-model/src/validation.ts:valueMatchesType` currently accepts any colon-bearing string for IPv6 and, for CIDR, any colon-bearing string ending in `/[0-9]{1,3}`. IPv4 CIDR regex also skips octet bounds. Invalid modeled facts and conflicting candidates can be incorrectly accepted.
3. Normalize syntax parsing by reusing one pure address/CIDR parser in a neutral shared module. Do not create a new Engine truth inference, route, network link, implicit disclosure, or import activation.

## Immutable adversarial/positive cases

The test oracle `tests/security/run_audit007_p3_network_address_contract_tests.mjs` is frozen in this branch before production edits. It checks:

- Engine: invalid missing, text, duplicate or out-of-range interface prefix => undefined; `addressInCidr` must never yield known TRUE for those; valid bare IPs, IPv4 /24 and IPv6 /64 remain accepted and matching. Keep prior P1 malformed address and CIDR tests intact.
- Enterprise: KNOWN/INFERRED `ipv6` and `cidr` values reject arbitrary colons, malformed hextets, bad IPv4 octets, missing/out-of-range/fake prefixes, zone indices and wrong family syntax with exact `ENTERPRISE_VALUE_TYPE_MISMATCH` diagnostics and no identity mismatch. Positive IPv4/IPv6 and CIDR boundary values still verify.
- Enterprise: CONFLICTING fact candidate with malformed IPv6/CIDR remains rejected, not silently treated as evidence.
- Regression: existing P1 91, P2a 39, P2b 137, IC-040 P1a 278, real Chromium, AUDIT-006, Dev11, IC-030, Ubuntu mirror and release provenance remain required and must not be removed.

## Deliverable and evidence

Scope is source-only address-validation repair; no UI, probe, native physical-network or Runtime attestation is claimed. Add a named `npm run test:audit007-p3-address-contract` in BOTH mandatory PR CI and independent Linux release, verify actual logs. No removal/rewrite of frozen failure expectations to force green. If test or workflow reveals a test-oracle error, document precisely and preserve the original frozen oracle commit. Later changes require a separately justified minimal amendment, never silently weakening the negative cases.

Status upon freeze: **ORACLES_FROZEN; production patch and CI NOT_VERIFIED**.
