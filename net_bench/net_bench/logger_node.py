"""Base-station side: sends timestamped probes, collects echoes, and reports link metrics."""

import argparse
import array
import csv
import json
import os
import sys
import time

import rclpy
from rclpy.node import Node
from std_msgs.msg import UInt8MultiArray

from net_bench import metrics
from net_bench.ros_common import ACK_TOPIC, PROBE_TOPIC, link_qos

SUMMARY_FIELDS = [
    "label", "profile", "rmw", "rate_hz", "payload_bytes", "duration_s",
    "sent", "received", "loss_pct", "rtt_p50_ms", "rtt_p95_ms", "rtt_p99_ms",
    "rtt_max_ms", "jitter_mean_ms", "goodput_kbps",
]


class Logger(Node):
    def __init__(self, rate_hz: float, payload_bytes: int):
        super().__init__("net_bench_logger")
        qos = link_qos()
        self.pub = self.create_publisher(UInt8MultiArray, PROBE_TOPIC, qos)
        self.sub = self.create_subscription(UInt8MultiArray, ACK_TOPIC, self.on_ack, qos)
        self.rate_hz = rate_hz
        self.payload_bytes = payload_bytes
        self.seq = 0
        self.sent_at = {}      # seq -> send time (ns, monotonic)
        self.rtts = {}         # seq -> rtt (ms)
        self.timer = None

    def peers_matched(self) -> bool:
        return self.pub.get_subscription_count() > 0 and self.sub.get_publisher_count() > 0

    def start(self):
        self.timer = self.create_timer(1.0 / self.rate_hz, self.send_probe)

    def stop_sending(self):
        if self.timer is not None:
            self.timer.cancel()

    def send_probe(self):
        t = time.monotonic_ns()
        msg = UInt8MultiArray()
        msg.data = array.array("B", metrics.pack(self.seq, t, self.payload_bytes))
        self.sent_at[self.seq] = t
        self.pub.publish(msg)
        self.seq += 1

    def on_ack(self, msg):
        now = time.monotonic_ns()
        try:
            seq, t_send = metrics.unpack(bytes(msg.data))
        except ValueError:
            return
        if seq in self.sent_at and seq not in self.rtts:
            self.rtts[seq] = (now - t_send) / 1e6

    def outstanding(self) -> int:
        return len(self.sent_at) - len(self.rtts)


def spin_until(node, deadline, condition=lambda: False):
    while rclpy.ok() and time.monotonic() < deadline and not condition():
        rclpy.spin_once(node, timeout_sec=0.02)


def chown_if_requested(path):
    uid, gid = os.environ.get("HOST_UID"), os.environ.get("HOST_GID")
    if uid and gid and uid != "0":
        try:
            os.chown(path, int(uid), int(gid))
        except OSError:
            pass


def write_results(out_dir, label, node, summary_row):
    runs_dir = os.path.join(out_dir, "runs")
    os.makedirs(runs_dir, exist_ok=True)
    chown_if_requested(out_dir)
    chown_if_requested(runs_dir)

    run_path = os.path.join(runs_dir, f"{label}.csv")
    with open(run_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["seq", "rtt_ms", "lost"])
        for seq in sorted(node.sent_at):
            rtt = node.rtts.get(seq)
            w.writerow([seq, "" if rtt is None else f"{rtt:.3f}", 0 if rtt is not None else 1])
    chown_if_requested(run_path)

    summary_path = os.path.join(out_dir, "summary.csv")
    new_file = not os.path.exists(summary_path)
    with open(summary_path, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=SUMMARY_FIELDS)
        if new_file:
            w.writeheader()
        w.writerow(summary_row)
    chown_if_requested(summary_path)
    return run_path, summary_path


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="ROS 2 rover-link benchmark (base-station side)")
    p.add_argument("--rate", type=float, default=10.0, help="probe rate in Hz (default 10)")
    p.add_argument("--payload", type=int, default=100, help="payload bytes per probe (default 100)")
    p.add_argument("--duration", type=float, default=30.0, help="sending window in seconds (default 30)")
    p.add_argument("--grace", type=float, default=2.0, help="seconds to wait for late echoes (default 2)")
    p.add_argument("--discovery-timeout", type=float, default=20.0,
                   help="seconds to wait for the echo node to be discovered (default 20)")
    p.add_argument("--label", default=None, help="run name used for output files")
    p.add_argument("--out", default="/results", help="output directory (default /results)")
    p.add_argument("--max-loss", type=float, default=None,
                   help="exit non-zero if packet loss %% exceeds this (used by CI)")
    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    if args.rate <= 0 or args.payload < 0 or args.duration <= 0:
        print("rate and duration must be > 0, payload >= 0", file=sys.stderr)
        return 2

    profile = os.environ.get("NETEM_PROFILE", "none")
    rmw = os.environ.get("RMW_IMPLEMENTATION", "rmw_fastrtps_cpp")
    label = args.label or f"{profile}-{int(args.rate)}hz-{args.payload}b"

    rclpy.init()
    node = Logger(args.rate, args.payload)
    log = node.get_logger()
    try:
        log.info("Waiting for echo node (DDS discovery)...")
        spin_until(node, time.monotonic() + args.discovery_timeout, node.peers_matched)
        if not node.peers_matched():
            log.error("Echo node not discovered. Check ROS_DOMAIN_ID, network and DDS config.")
            return 3

        log.info(f"Run '{label}': {args.rate} Hz, {args.payload} B, {args.duration} s, profile={profile}")
        node.start()
        spin_until(node, time.monotonic() + args.duration)
        node.stop_sending()
        spin_until(node, time.monotonic() + args.grace, lambda: node.outstanding() == 0)

        summary = metrics.summarize(node.seq, node.rtts, args.payload, args.duration)
        row = {"label": label, "profile": profile, "rmw": rmw, "rate_hz": args.rate,
               "payload_bytes": args.payload, "duration_s": args.duration, **summary}
        run_path, summary_path = write_results(args.out, label, node, row)
        print(json.dumps(row, indent=2))
        log.info(f"Wrote {run_path} and appended {summary_path}")

        if summary["received"] == 0:
            log.error("No echoes received.")
            return 4
        if args.max_loss is not None and summary["loss_pct"] > args.max_loss:
            log.error(f"Loss {summary['loss_pct']}% exceeds limit {args.max_loss}%")
            return 5
        return 0
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    sys.exit(main())
