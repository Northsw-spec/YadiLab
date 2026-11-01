# YADILAB-CI-CONCURRENCY-001 — controlled live supersession probe

This is a **separate, evidence-seeking follow-up commit** on PR #93, deliberately made while the PR's previous-head required CI run was IN_PROGRESS. The initial frozen acceptance oracles remain **unchanged**.

**Previous PR head:** `8f475a3bdac323c92cd15b83cfcb64c0d1eb90bb`.

**Previous required CI run:** [#41267253837](https://github.com/Northsw-spec/YadiLab/actions/runs/41267253837) was reported IN_PROGRESS just before this doc-only second commit.

**Controlled expected behavior:** On this branch's new PR commit, GitHub cancels superseded run #41267253837 (previous PR commit), starts a replacement `yadilab-required-ci` for the new head, and does **not** cancel unrelated independent workflow runs from the earlier head that were not retriggered by this doc-only change. Treat cancellation and SUCCESS as **UNVERIFIED** until readback of real GitHub run/job statuses and logs.

**Why a separate doc file:** This test action does not edit code, production tests, frozen oracles, source metadata, or existing workflow commands. It creates one intentional additional required-CI run rather than multiplying 42 independent workflows for a synthetic commit. New latest-head required CI must complete its **full** real Chromium, provenance, import, Engine and adversarial gates before merge.

**Future final evidence:** record old and new run IDs with their actual `status`/`conclusion`, newest full test PASS and non-PR isolation; report any failed/unproven aspect accurately in issue #3.
