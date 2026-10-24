#!/usr/bin/env bash
# Apply a simulated link profile to this container's network interface with tc/netem.
# Applied on both containers, so round-trip delay is roughly 2x the one-way delay below.
#
# Profiles are synthetic stand-ins for a rover moving away from the base station.
# They are NOT measured RF data; replace them with field measurements when available.
#
#   none    no impairment
#   near    delay 5 ms  +/- 1 ms,  0.5 % loss
#   mid     delay 20 ms +/- 5 ms,  2 % loss
#   far     delay 60 ms +/- 20 ms, 8 % loss
#   custom  uses $NETEM_ARGS, e.g. NETEM_ARGS="delay 100ms loss 15%"
set -euo pipefail

profile="${1:-none}"
dev="${NETEM_DEV:-eth0}"

case "$profile" in
  none)
    tc qdisc del dev "$dev" root 2>/dev/null || true
    echo "[netem] $dev: no impairment"
    exit 0
    ;;
  near)   args="delay 5ms 1ms loss 0.5%" ;;
  mid)    args="delay 20ms 5ms distribution normal loss 2%" ;;
  far)    args="delay 60ms 20ms distribution normal loss 8%" ;;
  custom)
    args="${NETEM_ARGS:-}"
    if [[ -z "$args" ]]; then
      echo "[netem] profile 'custom' needs NETEM_ARGS" >&2
      exit 1
    fi
    ;;
  *)
    echo "[netem] unknown profile '$profile' (use none|near|mid|far|custom)" >&2
    exit 1
    ;;
esac

# shellcheck disable=SC2086
if ! tc qdisc replace dev "$dev" root netem $args; then
  echo "[netem] failed to apply profile. Does the container have the NET_ADMIN capability?" >&2
  exit 1
fi
echo "[netem] $dev: $args"
