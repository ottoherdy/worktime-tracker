#!/bin/bash
# Development helper: sync the integration to a Home Assistant host and restart it.
#
# Not needed to *use* Worktime Tracker — install it through HACS instead.
# This exists so contributors can push a working copy straight to a test instance.
#
# Requires SSH access to the HA host with the "Advanced SSH & Web Terminal"
# add-on (or equivalent) so that /config is writable and `ha` is on PATH.
#
# Usage:
#   ./deploy.sh                      # uses host "homeassistant"
#   HA_HOST=ha.lan ./deploy.sh       # override the host
#   HA_HOST=root@10.0.0.5 ./deploy.sh

set -euo pipefail

HA_HOST="${HA_HOST:-homeassistant}"
HA_CONFIG_DIR="${HA_CONFIG_DIR:-/config}"

echo "→ Syncing files to ${HA_HOST}:${HA_CONFIG_DIR}..."
rsync -av --delete \
  custom_components/worktime_tracker/ \
  "${HA_HOST}:${HA_CONFIG_DIR}/custom_components/worktime_tracker/"

echo "→ Restarting Home Assistant..."
ssh "${HA_HOST}" "ha core restart"

echo "✓ Done"
