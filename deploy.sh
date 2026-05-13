#!/bin/bash
# Sync integration to Home Assistant and reload

echo "→ Syncing files..."
rsync -av --delete \
  custom_components/worktime_tracker/ \
  homeassistant:/config/custom_components/worktime_tracker/

echo "→ Reloading integration..."
ssh homeassistant "ha core restart"

echo "✓ Done"
