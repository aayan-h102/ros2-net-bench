"""Shared ROS 2 settings for the probe and echo nodes."""

from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy

PROBE_TOPIC = "net_bench/probe"
ACK_TOPIC = "net_bench/ack"


def link_qos() -> QoSProfile:
    # Best effort: a lost packet stays lost, so packet loss is measured, not hidden by retries.
    return QoSProfile(
        reliability=ReliabilityPolicy.BEST_EFFORT,
        history=HistoryPolicy.KEEP_LAST,
        depth=10,
    )
