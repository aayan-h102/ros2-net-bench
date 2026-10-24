#!/usr/bin/env bash
# Run the full test matrix: middleware x link profile x message rate x payload size.
# Defaults: 2 middlewares x 4 profiles x 2 rates x 2 payloads x 30 s = 32 runs, about 20 minutes.
# Override with env vars, e.g.  RMWS=rmw_fastrtps_cpp PROFILES="none far" DURATION=10 ./scripts/run_matrix.sh
set -euo pipefail
cd "$(dirname "$0")/.."

RMWS="${RMWS:-rmw_fastrtps_cpp rmw_zenoh_cpp}"
PROFILES="${PROFILES:-none near mid far}"
RATES="${RATES:-10 25}"
PAYLOADS="${PAYLOADS:-100 500}"
DURATION="${DURATION:-30}"

export HOST_UID="$(id -u)" HOST_GID="$(id -g)"
mkdir -p results

docker compose build
failures=0
for rmw in $RMWS; do
  short="${rmw#rmw_}"; short="${short%_cpp}"          # fastrtps | zenoh
  for profile in $PROFILES; do
    echo "=== Middleware: $rmw | Link profile: $profile ==="
    export RMW_IMPLEMENTATION="$rmw" NETEM_PROFILE="$profile"
    docker compose up -d --force-recreate echo
    sleep 3
    for rate in $RATES; do
      for payload in $PAYLOADS; do
        label="${short}-${profile}-${rate}hz-${payload}b"
        if ! docker compose run --rm logger \
            --rate "$rate" --payload "$payload" --duration "$DURATION" --label "$label"; then
          echo "!!! run $label failed" >&2
          failures=$((failures + 1))
        fi
      done
    done
  done
done
docker compose down

echo
echo "Done. $failures failed run(s). Summary: results/summary.csv"
echo "Make the report:  python3 net_bench/net_bench/analyze.py results/summary.csv"
exit "$failures"
