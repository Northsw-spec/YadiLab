# Phase 3 — Deterministic Engine Foundation

Version: 0.3.0

This phase adds the first executable semantic engine on top of the verified Phase 0-2 repository, schema, and compiler work. It does not replace or fork the compiler contracts.

## Implemented engine boundaries

### Immutable runtime state + reducer

- `createInitialEngineState()` creates mutable-runtime state from a normalized scenario while preserving scenario definition separately.
- `applyOperation()` supports schema-defined `set` and `remove` operations.
- Runtime updates are immutable.
- Dot paths support object keys and declared array indexes.
- Prototype-sensitive segments (`__proto__`, `prototype`, `constructor`) are rejected.
- `applyOperations()` is atomic: a failing batch returns the original state rather than a partially remediated state.

### Three-valued logic

The engine uses exactly:

- `TRUE`
- `FALSE`
- `UNKNOWN`

Composite rules use deterministic Kleene-style semantics:

- `all`: any FALSE is decisive; otherwise UNKNOWN propagates.
- `any`: any TRUE is decisive; otherwise UNKNOWN propagates.
- `not`: UNKNOWN remains UNKNOWN.

Missing evidence is not silently converted to false.

### NetworkEngine v1

Foundation reachability is configuration/reachability simulation, not packet emulation.

Implemented:

- declared `network` and `management` topology connections;
- bidirectional connections by default;
- explicit `properties.direction = "forward"` for one-way connection semantics;
- disabled connections via `properties.enabled = false`;
- deterministic simple-path search;
- ordered firewall policy evaluation on `network.firewall` resources;
- resource/zone/`any` source and destination matching;
- TCP/UDP/ICMP/any protocol matching;
- destination port matching;
- `allow`, `deny`, `block`, and optional `defaultAction` semantics;
- declared destination service/listener checks;
- alternate-path handling so one blocked path does not falsely imply isolation;
- explainable path, policy, listener, and blocking-point evidence;
- conservative `UNKNOWN` when firewall or listener evidence is insufficient.

Deliberately not claimed in this phase:

- packet timing or packet payload emulation;
- TCP state machine;
- routing protocol emulation;
- switch ASIC/STP behavior;
- full NAT translation semantics;
- full route-table/longest-prefix modeling;
- vendor-specific firewall syntax.

Those remain future capability/domain work. The v1 network engine is intentionally bounded by the locked architecture.

### IdentityEngine v1

Implemented:

- direct and transitive `memberOf` membership paths;
- positive membership edges derived from group `members` lists;
- conservative closed/open-world handling for missing membership declarations;
- effective permission evaluation from an authoritative target `permissions` list;
- direct and group-based allow/deny semantics;
- explicit deny precedence;
- authentication policy with allowed subjects/groups;
- MFA-required decision using declared subject MFA state;
- explainable membership/authentication/permission results.

This is relationship/authorization simulation. It is not AD/Kerberos/NTLM/LDAP protocol emulation.

### RuleEngine v1

Implemented schema-defined rules:

- `all`
- `any`
- `not`
- `equals`
- `reachable`
- `member_of`
- `has_permission`
- `service_enabled`
- `test_result`

All rule evaluation is deterministic and explanation-carrying.

### TestEngine v1

Implemented Foundation evaluators:

- `network.reachability`
- `network.segmentation`
- `network.route_test`
- `identity.authentication_test`
- `identity.privilege_path`
- `identity.permission`
- `identity.membership`
- `windows.hardening_check`
- `linux.hardening_check`

Unsupported future test types return `UNKNOWN` with an explanation rather than being silently accepted as false or true.

### Finding / Objective / Completion evaluation

`evaluateEngine()` deterministically evaluates:

1. tests;
2. test-result map;
3. findings;
4. objectives;
5. completion rule;
6. ordered evidence records.

This creates the semantic basis needed for Phase 4 canonical-solution replay and regression.

## State conventions used by Foundation v0.3.0

The external scenario schemas intentionally still permit capability-owned `properties`/`params` objects. Phase 3 interprets a small documented Foundation convention set while later domain packs will tighten these with domain schemas.

Examples:

```json
{
  "properties": {
    "rules": [
      {
        "source": "wan",
        "destination": "rds01",
        "protocol": "tcp",
        "port": 3389,
        "action": "allow"
      }
    ],
    "defaultAction": "deny"
  }
}
```

```json
{
  "properties": {
    "rdp": {
      "enabled": true,
      "port": 3389
    }
  }
}
```

```json
{
  "properties": {
    "memberOf": ["admins"],
    "mfaEnabled": true
  }
}
```

```json
{
  "properties": {
    "permissions": [
      {"subject": "admins", "permission": "admin", "effect": "allow"}
    ],
    "authentication": {
      "enabled": true,
      "allowedGroups": ["admins"],
      "mfaRequired": true
    }
  }
}
```

These conventions are engine data, not arbitrary executable scenario code.
