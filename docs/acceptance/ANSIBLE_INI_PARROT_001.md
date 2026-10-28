# ANSIBLE-INI-PARROT-ACCEPTANCE-001

**Purpose:** Independent on-device Parrot Linux acceptance for the real packaged YadiLab app using the existing P2 and P3 interactive Chromium tests. No remote or GitHub claim is a target-machine PASS. Checkpoint authority when created: main commit 073736c93f0ae644780868b8bf0737c0195530be. For operation, both source checkout and packaged distribution must be from the **same current commit**.

## Steps on the actual Parrot x86_64 computer (non-root)

1. Obtain a normal Git checkout of https://github.com/Northsw-spec/YadiLab at intended current main; do NOT use historical ZIP sources. Check the repository commit using: git rev-parse HEAD.
2. In the successful GitHub Actions **YadiLab release identity and Linux build** for exactly that commit, download the YadiLab_VERSION005_Linux_x86_64 artifact. Unzip the outer artifact and then the inner YadiLab_VERSION005_Linux_x86_64.zip. Copy the inner distribution/linux-x86_64 directory under your Git checkout. Preserve exact checksum-covered files. A release built from another commit is BLOCKED, regardless of version labels.
3. Prepare acceptance-only Python in an isolated user-owned virtual environment if it is missing. The harness itself never installs anything:

    python3 -m venv "$HOME/.venvs/yadilab-accept"
    "$HOME/.venvs/yadilab-accept/bin/python" -m pip install 'playwright==1.55.0'
    "$HOME/.venvs/yadilab-accept/bin/python" -m playwright install chromium

   These manual commands download Python packages and a browser to user-owned locations. No sudo, apt or --with-deps is needed or used by the harness. If Chromium cannot start because system libraries are missing, result is BLOCKED until the operator resolves it.
4. Run from the Git checkout, as an ordinary unprivileged user:

    YADILAB_ANSIBLE_INI_PYTHON="$HOME/.venvs/yadilab-accept/bin/python" bash scripts/run_ansible_ini_parrot_acceptance.sh

5. Inspect acceptance-evidence/ansible-ini-parrot/acceptance-status.txt, p2/ansible-ini-p2-chromium.json, p3/ansible-ini-p3-chromium.json, launcher.log and both output.log files. Share evidence for audit. Exit 0/PASS must agree with overall=PASS; exit 77/BLOCKED or 1/FAIL is not acceptance.

## Truth boundaries and expected results

- PASS/0: measured actual Parrot x86_64, non-root, checksum-verified packaged app, embedded sourceCommit matching current Git HEAD, loopback-only launcher, real Chromium P2 and P3 cases with JSON evidence and unchanged Builder.
- BLOCKED/77: non-Parrot OS, missing tools/Chromium, missing release or fixtures, mismatched commit, modified tracked test files, invalid or occupied local port.
- FAIL/1: checksum mismatch, incorrect launcher/HTTP marker or listener, real interactive browser case failure.
- Does NOT run Ansible, scan live networks, modify OS/system packages or infer physical network topology and Engine truth.
- Only tests Ansible INI P2/P3 and packed launcher; not full application certification.
- Ubuntu CI must show exit 77/BLOCKED for this target-native script, while separately verifying the same browser cases using Ubuntu Chromium. **Actual Parrot USER_ACCEPTED remains NOT RUN** until executed there and reports checked.
