# Release notes v0.6.0 — Headless CLI Phase 6

YadiLab Foundation v0.6.0 continues directly from v0.5.0.

## Added

- generic `app` headless CLI surface;
- `validate` command wired to the authoritative injected source validator;
- `compile` command wired to the real Phase 2 compiler;
- `test` command wired to Phase 4 canonical regression;
- source -> compiler -> regression support in one CLI command;
- side-effect-free `inspect` for source, normalized scenario, and package manifest;
- deterministic JSON output suitable for scripts/CI;
- explicit CLI exit-code contract (0 success, 1 domain failure, 2 usage/operational error);
- strict argument parsing and file-I/O error propagation;
- Node entrypoint and generic package `bin` mapping;
- CLI functional and adversarial verification suites.

## Preserved

All Phase 0-5 schema, compiler, Engine, regression, and PackageIO tests remain in the same Foundation regression command.

## Environment limitation

The sandbox still has no installed npm dependencies. The CLI core and real Compiler/Engine pipeline are runtime-tested, but the production Node entrypoint cannot load the authoritative Ajv validator until dependencies are resolved. Full repository typecheck therefore still stops only at the existing unresolved Ajv imports.
