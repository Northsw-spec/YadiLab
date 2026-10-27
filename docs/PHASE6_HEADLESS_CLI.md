# Phase 6 — Headless CLI

Version: 0.6.0

Phase 6 continues directly from the verified v0.5.0 checkpoint. It does not replace or bypass the schema, compiler, deterministic Engine, canonical regression framework, or PackageIO.

## Command surface

The Foundation CLI exposes the architecture-defined generic command name `app`:

```text
app validate --input <scenario-source.json> [--output <validation.json>]
app compile  --input <scenario-source.json> [--output <scenario.json>]
app test     --input <scenario-source-or-normalized.json> [--output <report.json>]
app inspect  --input <scenario-or-manifest.json> [--output <summary.json>]
app help
```

The command name is deliberately generic and rebrandable. It does not hardcode the current product display name into Engine/Compiler semantics.

## validate

`validate` delegates to the injected authoritative source-schema validator. In the production Node entrypoint this is the existing Ajv Draft 2020-12 validator adapter.

Exit codes:

- `0`: schema-valid;
- `1`: validation failed;
- `2`: usage, JSON, file I/O, dependency, or internal operational error.

## compile

`compile` calls the existing Phase 2 `compileScenario()` implementation. It therefore preserves the same:

- schema gates;
- semantic validation;
- capability/profile resolution;
- exact locks;
- defaults;
- reference validation;
- deterministic source hashing;
- normalized model contract.

A failed compiler result exits `1` and preserves compiler diagnostics.

## test

`test` executes the Phase 4 canonical regression framework.

When the input is a source scenario, the CLI first compiles it using the actual compiler and only runs regression if compilation succeeds. When the input is already normalized, it runs regression directly.

This establishes the headless chain:

```text
source
  -> compile
  -> normalized model
  -> initial-state checks
  -> canonical solution replay
  -> solved-state checks
  -> required objectives
  -> completion
```

A regression failure exits `1`. Operational/input failures exit `2`.

## inspect

`inspect` is side-effect free. It summarizes recognized contract objects without executing scenario code.

Foundation-recognized inputs:

- scenario source;
- normalized scenario;
- package manifest.

The summary reports contract kind, scenario identity where present, counts, exact lock counts, distribution/package metadata where applicable, and whether a source/normalized scenario contains canonical solution data.

## Node entrypoint

`cli/src/main.ts` provides the actual headless Node entrypoint. It:

- uses ordinary filesystem reads/writes;
- loads the built-in catalog as a bundled JSON module;
- loads the existing validator adapter at runtime;
- creates Foundation CLI services around the real Compiler and Engine;
- maps the returned CLI exit code to the process exit code.

`package.json` exposes:

```json
{
  "bin": {
    "app": "./dist/cli/src/main.js"
  }
}
```

The runtime CLI therefore requires the production dependencies declared by the repository to be installed/resolved during a developer build. End-user Parrot distribution remains a later packaging/acceptance phase and must not require Node/npm at runtime.

## Test boundary

CLI core and its actual Compiler/Engine integration are strict-typechecked and runtime-tested in this environment.

The final Node entrypoint cannot be end-to-end executed here because the sandbox intentionally has no installed npm dependencies; the authoritative validator imports Ajv. This is the same previously documented dependency-resolution boundary, not a new CLI semantic limitation.
