## Scope and active project priority

- [ ] I read current `main`, root [AGENTS.md](../AGENTS.md), [active import masterplan](../docs/architecture/IMPORT_COMPLETION_EXECUTION_MASTERPLAN.md) and [tracking issue #3](https://github.com/Northsw-spec/YadiLab/issues/3).
- [ ] This is the next unfulfilled import milestone `IC-___` (state exact current implementation gap and profile), **or** an explicit owner-approved exception/security/required-CI repair (state reason and issue #3 decision).
- [ ] The change is additive or explicitly justifies compatibility impact; it does not replace currently working import/Engine functions or use a historical ZIP as code authority.

## Source and truth boundary

- Format / producer / scoped profile:
- Declared topology, documented configuration or observed evidence:
- Exact original-file locator/provenance and stale-source handling:
- Does this PR enable: preview, review, Builder projection, modeled Runtime probes, evidence-only overlay, report replay? State only actually delivered capabilities.
- How are unknown/ambiguous inputs represented? What prevents invented cables, services, live packet results, Engine TRUE/PASS or unauthorized Real Mode probes?
- Malicious/oversized/secret-bearing inputs and rollback behavior:

## Required evidence on exact code

- Frozen positive and negative oracle references:
- Relevant old + new test commands and observed assertion count:
- Actual GitHub Actions exact-head job/run links and conclusions:
- Real-browser/user-facing verification, separate from source-token checks:
- `PASS` / `FAIL` / `NOT_RUN` statements and limitations:
- Reimport/roundtrip/report/source replay checks if relevant:

## After protected merge

- Merged `main` SHA/tree:
- Independent exact-main Linux-release run and published artifacts:
- [ ] Update [issue #3](https://github.com/Northsw-spec/YadiLab/issues/3) with completion level, actual proof, blocked cases and **the next remaining IC checkpoint**.

Do not mark implementation complete based on the existence of a parser, a new UI label or a generic test. The project's **current** main remains the only code authority; this checklist cannot authorize missing verification.