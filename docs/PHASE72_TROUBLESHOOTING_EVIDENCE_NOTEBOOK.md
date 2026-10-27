# Phase 72 — Troubleshooting Session / Evidence Notebook

Foundation v0.72.0 connects the deterministic Observation Engine to a learner-owned troubleshooting evidence chain.

## Boundary

The notebook is **not Engine state**, is **not automatic diagnosis**, and is **not hidden instructor truth**. It records only:

- modeled observation transcripts the learner explicitly saves;
- modeled active-probe transcripts the learner explicitly saves;
- learner-authored hypothesis, next-step and conclusion notes.

The notebook never imports `faultOrigin`, hidden fault truth, generator ground truth, reference investigation order or `canonicalSolution` material.

## Portable contract

A notebook document has:

- format `infrastructure-cyber-lab.troubleshooting-notebook`;
- schema version `0.1.0`;
- exact `scenarioId` and `scenarioHash` binding;
- at most 256 ordered entries;
- canonical entry IDs `entry-0001`, `entry-0002`, ...;
- canonical SHA-256 `notebookIdentity` over the entire notebook except the identity field itself.

The browser uses the centralized `.yadinotebook` extension. Import validates JSON schema, exact scenario identity, canonical sequence and notebook identity before accepting the document.

## Evidence entries

Observation and active-probe entries preserve the learner-visible transcript only:

- exact Runtime `stateRevision`;
- command-shaped learning surface;
- target/source and optional destination;
- active-probe `TRUE` / `FALSE` / `UNKNOWN` verdict where applicable;
- transcript lines and direct modeled evidence;
- independent transcript SHA-256 identity.

Saving the exact same transcript twice for the same Runtime revision fails closed as duplicate evidence. Re-running the same probe after state changes is valid new evidence because the transcript is bound to the new revision.

## Learner notes

Learner notes are explicit, separate entries with one of three types:

- `hypothesis`;
- `next_step`;
- `conclusion`.

The application does not infer these notes from evidence and does not rank or score hypotheses.

## Runtime behavior

The Runtime UI adds **Troubleshooting session / Evidence notebook**. Observation and active-probe transcripts gain an explicit **Save evidence to notebook** action. The notebook shows evidence in capture order, revision badges and transcript-identity prefixes. Historical evidence remains visible after Runtime state changes but is labeled as a historical snapshot.

A transcript from an earlier Runtime revision cannot be newly captured after state drift; the learner must re-run the observation/probe and save the current transcript.

The notebook can be exported and imported as a portable JSON document. Clearing the notebook does not modify Engine state, Runtime history, checkpoints, fault overlays or scenario source.

## Non-goals

v0.72.0 does not introduce:

- automatic root-cause diagnosis;
- automatic troubleshooting order derived from outputs;
- scoring or grading of learner hypotheses;
- automatic remediation;
- packet capture;
- guest command execution;
- terminal/PTY access;
- AI/ML/LLM inference;
- merging notebook content into Engine evidence or canonical solution state.

Those require separate explicit contracts.
