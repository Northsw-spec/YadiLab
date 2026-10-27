# YadiLab Foundation v0.79.0

Phase 79 adds portable troubleshooting-session backup/recovery as release hardening.

- New `.yadisession` configured extension.
- One file preserves exact Runtime progress + Evidence Notebook session envelope.
- Export uses the existing content-addressed session snapshot.
- Import is atomic and validates extension, bounded input size, schema, nested SaveState/notebook, exact scenario binding, notebook SHA-256 and session SHA-256 before restore.
- Corruption, tampering and cross-scenario imports fail closed without changing Runtime.
- Existing `.yadiprogress`, `.yadinotebook` and IndexedDB autosave flows remain supported.
- No new Engine truth, automatic diagnosis/remediation, hidden scoring, live connector or guest execution.

Classification remains a development checkpoint until external product-release gates pass.
