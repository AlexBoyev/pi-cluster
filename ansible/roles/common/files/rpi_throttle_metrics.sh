#!/bin/bash
# Writes Raspberry Pi firmware undervoltage/throttle state as a node-exporter
# textfile-collector metric. vcgencmd's get_throttled bitmask is the only
# reliable signal for this - the kernel's own hwmon in0_lcrit_alarm metric
# was checked live against vcgencmd during the 2026-09-08 pi-node3 incident
# and missed an active undervoltage event, so it is not trustworthy on its
# own. See docs/decisions.md.
set -euo pipefail

OUT_DIR="/var/lib/node-exporter/textfile-collector"
OUT_FILE="$OUT_DIR/rpi_throttle.prom"
TMP_FILE="$(mktemp "$OUT_DIR/.rpi_throttle.XXXXXX")"
trap 'rm -f "$TMP_FILE"' EXIT

raw="$(vcgencmd get_throttled | cut -d= -f2)"
val=$((raw))

{
  echo "# HELP node_rpi_throttled_bit Raspberry Pi firmware throttled status (vcgencmd get_throttled), 1 if the bit is set"
  echo "# TYPE node_rpi_throttled_bit gauge"
  echo "node_rpi_throttled_bit{bit=\"undervoltage_now\"} $(( (val >> 0) & 1 ))"
  echo "node_rpi_throttled_bit{bit=\"freq_capped_now\"} $(( (val >> 1) & 1 ))"
  echo "node_rpi_throttled_bit{bit=\"throttled_now\"} $(( (val >> 2) & 1 ))"
  echo "node_rpi_throttled_bit{bit=\"undervoltage_occurred\"} $(( (val >> 16) & 1 ))"
  echo "node_rpi_throttled_bit{bit=\"freq_capped_occurred\"} $(( (val >> 17) & 1 ))"
  echo "node_rpi_throttled_bit{bit=\"throttled_occurred\"} $(( (val >> 18) & 1 ))"
} > "$TMP_FILE"

mv "$TMP_FILE" "$OUT_FILE"
