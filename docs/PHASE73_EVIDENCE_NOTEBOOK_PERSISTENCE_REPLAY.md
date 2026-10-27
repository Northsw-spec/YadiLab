# Phase 73 — Evidence Notebook Persistence & Replay

Foundation v0.73.0 binds Runtime progress and the learner-owned Evidence Notebook into one local, content-addressed troubleshooting session without merging notebook evidence into Engine truth.

## Persistence boundary

The persisted session envelope is `infrastructure-cyber-lab.troubleshooting-session@0.1.0`. It contains only:

- exact scenario ID and scenario SHA-256;
- exact current Runtime state revision;
- ordinary Engine `SaveState` progress;
- the verified Phase-72 troubleshooting notebook;
- the notebook SHA-256 identity;
- a canonical session SHA-256 identity over the complete envelope except the identity field itself.

The envelope does not contain scenario source, `faultOrigin`, hidden generator truth, reference investigation order, `canonicalSolution`, inferred root cause, grading or remediation advice.

## Local autosave integration

The existing Runtime **Autosave now** action now persists two compatible local records:

1. the existing progress-only save for backward compatibility;
2. the new combined troubleshooting-session envelope containing Runtime progress and Evidence Notebook together.

The notebook state is lifted to the application Runtime session so restore can reinstate both Runtime state and notebook UI state as one verified unit. If the learner has not started a notebook yet, autosave creates and seals an empty exact-scenario notebook rather than inventing evidence.

Local troubleshooting sessions use an isolated IndexedDB store. Portable `.yadiprogress` and `.yadinotebook` exports remain available and unchanged.

## Restore and fail-closed rules

Restore prefers the combined Phase-73 session when one exists. Before Runtime mutation it validates:

- troubleshooting-session JSON schema;
- embedded SaveState schema;
- embedded notebook schema;
- exact current scenario ID/hash binding;
- envelope revision equals embedded SaveState revision;
- envelope notebook identity equals embedded notebook identity;
- notebook canonical identity;
- complete session canonical identity.

A present but invalid/tampered combined session **does not** silently fall back to progress-only restore. Progress-only fallback is allowed only when no combined session exists for the exact scenario hash. This preserves backward compatibility without hiding integrity failures.

## Replay semantics

Replay is the canonical notebook entry sequence, not an inferred timeline. Each replay frame preserves:

- notebook sequence and entry ID;
- exact captured Runtime revision;
- entry kind and learner-visible content;
- whether that entry revision equals the restored Runtime revision.

Revision numbers are not sorted or interpreted as causal time because Runtime undo/checkpoint workflows can revisit state. The product therefore does not infer chronology, diagnosis or causal order from revision magnitude.

## Continuation

After restore, the learner can immediately continue the same notebook and save more observations, probes or learner notes. A changed notebook produces a changed session SHA-256 on the next autosave. No manual notebook export/import is required for local continuation.

## Non-goals

v0.73.0 does not add:

- silent background autosave without the existing user autosave action;
- portable combined-session export format;
- Runtime undo/checkpoint history persistence beyond the existing SaveState contract;
- automatic diagnosis, grading, scoring or remediation;
- guest command execution, packets or terminal access;
- hidden truth inside notebook/session persistence;
- AI/ML/LLM inference.
