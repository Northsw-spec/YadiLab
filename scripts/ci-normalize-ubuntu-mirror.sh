#!/usr/bin/env bash
# GitHub-hosted Ubuntu 24.04 browser CI only. A transient Azure-hosted APT
# mirror sometimes hangs Playwright's required --with-deps installation until
# the job is cancelled. Use the standard Ubuntu archive on this ephemeral
# runner, without skipping, downgrading or mocking any browser dependencies.
set -Eeuo pipefail
if [[ "$(uname -s)" != "Linux" ]]; then
  echo "FAIL Chromium CI: requires Linux"; exit 1
fi
for apt_source in /etc/apt/sources.list /etc/apt/sources.list.d/*.sources /etc/apt/sources.list.d/*.list; do
  if [[ -f "$apt_source" ]]; then
    sudo sed -i \
      -e 's|http://azure.archive.ubuntu.com/ubuntu|http://archive.ubuntu.com/ubuntu|g' \
      -e 's|https://azure.archive.ubuntu.com/ubuntu|https://archive.ubuntu.com/ubuntu|g' \
      "$apt_source"
  fi
done
if sudo grep -R -l 'azure.archive.ubuntu.com' /etc/apt/sources.list.d /etc/apt/sources.list 2>/dev/null; then
  echo "FAIL Chromium CI: unresponsive Azure Ubuntu mirror still configured"
  exit 1
fi
echo "PASS runner-local Ubuntu APT mirror normalization; pinned Chromium --with-deps still required"
