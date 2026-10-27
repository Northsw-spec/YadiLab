# Phase 78 — Guided Lab / Scenario Curriculum Wave 1

Foundation v0.78.0 adds the first built-in learner curriculum over the already verified Observation, Active Probe, Evidence Notebook, Evidence Review, Guided Troubleshooting and Typed Remediation stack.

## Boundary

The curriculum is a **learner-visible scenario library**, not a solution engine.

Curriculum boundary: `LEARNER_VISIBLE_NO_SOLUTION`

The Wave-1 manifest contains only lab identity, title, platform, focus, summary, sequence and the four transparent difficulty dimensions. It does not expose canonical solution operations, fault truth, typed-remediation parameters or instructor acceptance data.

Each built-in scenario source retains the ordinary author/compiler `canonicalSolution` used by existing deterministic certification/acceptance machinery. Runtime guidance continues to obey the existing `PROCESS_GUIDANCE_NO_DIAGNOSIS` and `LEARNER_ACTION_NO_SOLUTION` boundaries.

## Wave 1 labs

Eight deterministic labs are bundled locally and require no runtime Internet access:

### Windows

1. Wrong default gateway — routing evidence + off-link connectivity failure.
2. Wrong DNS resolver — client resolver evidence + failed modeled DNS lookup.
3. Blocking host-firewall default policy — firewall evidence + blocked connectivity.
4. Disabled RDP service — service evidence + failed TCP/3389 probe.

### Linux

5. Wrong default gateway — routing evidence + off-link connectivity failure.
6. Wrong DNS resolver — `resolvectl` evidence + failed modeled DNS lookup.
7. Blocking host-firewall default policy — modeled nftables/default-policy evidence + blocked connectivity.
8. Disabled SSH service — service evidence + failed TCP/22 probe.

All eight start in an intentionally broken modeled state embedded directly in the scenario source. Launch does not secretly inject a fault after compilation, so the exact source hash fully identifies the initial lab state.

## Learner evidence and remediation loop

Every lab defines one transparent two-step troubleshooting objective:

- a relevant configuration/service observation; then
- an active modeled probe that demonstrates the failure.

The learner then uses the ordinary notebook/hypothesis/typed-remediation/after-evidence workflow. The curriculum layer does not select the remediation.

Development-only curriculum acceptance data verifies that each lab:

1. compiles through the normal compiler;
2. previews into Runtime;
3. produces the intended initial active-probe verdict;
4. saves exact before evidence;
5. accepts the corresponding typed remediation through the normal mandatory preview;
6. produces `TRUE` on the same probe afterward;
7. stores after evidence;
8. reaches `VERIFIED_IMPROVEMENT`; and
9. reaches Guided Workflow `VERIFICATION_COMPLETE`.

This acceptance data lives under tests and is not part of the learner-visible curriculum manifest.

## Built-in lab launcher

The browser header exposes a `Guided lab` selector before raw scenario/package import.

For the selected lab the UI shows:

- sequence position;
- Windows/Linux platform;
- troubleshooting focus;
- learner-visible summary;
- four explicit difficulty dimensions (`layers`, `dependencyDepth`, `evidenceVisibility`, `remediationConstraints`).

The learner may either:

- **Start guided lab** — compile, auto-layout and enter Runtime through the normal verified boundaries; or
- **Open lab in Builder** — inspect/edit the source as an author.

No scalar difficulty score is introduced.

## Fail-closed curriculum catalog

The built-in catalog validates:

- exact curriculum format/version;
- stable unique lab/scenario IDs;
- unique deterministic sequence numbers;
- safe local Wave-1 source paths;
- Windows/Linux platform and supported focus;
- exactly four bounded difficulty dimensions;
- exact source scenario ID/title binding;
- presence of learner-visible troubleshooting objectives; and
- presence of author-only deterministic acceptance operations.

Path traversal, extra learner-visible solution-like manifest fields, missing source registrations, source/manifest identity mismatch and duplicate IDs/sequences fail closed.

## Explicit non-goals

v0.78.0 does not add live networking, guest command execution, automatic diagnosis, automatic remediation choice, hidden scoring/grading, adaptive AI curriculum, temporal fault scheduling or a live connector.
