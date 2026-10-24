#!/usr/bin/env bash
# Source ROS 2 and the workspace, apply the requested link profile, then run the command.
set -e
source /opt/ros/jazzy/setup.bash
source /ws/install/setup.bash
/scripts/netem.sh "${NETEM_PROFILE:-none}"
echo "[net_bench] RMW_IMPLEMENTATION=${RMW_IMPLEMENTATION}"
exec "$@"
