#!/usr/bin/env bash
# Run the full test matrix: every link profile x message rate x payload size.
# Defaults: 4 profiles x 2 rates x 2 payloads x 30 s  =  16 runs, about 10 minutes.
# Override with env vars, e.g.  PROFILES="none far" DURATION=10 ./scripts/run_matrix.sh
set -euo pipefail
cd "$(dirname "$0")/.."

PROFILES="${PROFILES:-none near mid far}"
RATES="${RATES:-10 25}"
PAYLOADS="${PAYLOADS:-100 500}"
DURATION="${DURATION:-30}"

export HOST_UID="$(id -u)" HOST_GID="$(id -g)"
mkdir -p results

docker compose build
failures=0
for profile in $PROFILES; do
  echo "=== Link profile: $profile ==="
  NETEM_PROFILE="$profile" docker compose up -d --force-recreate echo
  sleep 3
  for rate in $RATES; do
    for payload in $PAYLOADS; do
      label="${profile}-${rate}hz-${payload}b"
      if ! NETEM_PROFILE="$profile" docker compose run --rm logger \
          --rate "$rate" --payload "$payload" --duration "$DURATION" --label "$label"; then
        echo "!!! run $label failed" >&2
        failures=$((failures + 1))
      fi
    done
  done
done
docker compose down

echo
echo "Done. $failures failed run(s). Summary: results/summary.csv"
echo "Make the report:  python3 net_bench/net_bench/analyze.py results/summary.csv"
exit "$failures"
