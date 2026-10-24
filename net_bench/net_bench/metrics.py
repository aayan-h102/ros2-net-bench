"""Pure-Python link metrics. No ROS imports, so this module is unit-tested in CI."""

import struct

# Message header: sequence number (uint32) + send timestamp in ns (uint64), network byte order.
HEADER = struct.Struct("!IQ")
HEADER_BYTES = HEADER.size  # 12


def pack(seq: int, t_send_ns: int, payload_bytes: int) -> bytes:
    """Build a probe message: header followed by `payload_bytes` of filler."""
    if payload_bytes < 0:
        raise ValueError("payload_bytes must be >= 0")
    return HEADER.pack(seq, t_send_ns) + b"x" * payload_bytes


def unpack(data: bytes):
    """Return (seq, t_send_ns) from a probe message."""
    if len(data) < HEADER_BYTES:
        raise ValueError(f"message too short: {len(data)} bytes")
    return HEADER.unpack(data[:HEADER_BYTES])


def percentile(values, pct: float) -> float:
    """Percentile with linear interpolation (same method as numpy's default)."""
    if not values:
        return float("nan")
    if not 0 <= pct <= 100:
        raise ValueError("pct must be in [0, 100]")
    s = sorted(values)
    pos = (len(s) - 1) * pct / 100.0
    lo = int(pos)
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (pos - lo)


def mean_jitter(rtts_in_seq_order) -> float:
    """Mean absolute difference between consecutive RTTs (ms)."""
    r = list(rtts_in_seq_order)
    if len(r) < 2:
        return 0.0
    return sum(abs(b - a) for a, b in zip(r, r[1:])) / (len(r) - 1)


def summarize(sent: int, rtts_ms_by_seq: dict, payload_bytes: int, duration_s: float) -> dict:
    """Summarize one test run.

    sent            number of probes published
    rtts_ms_by_seq  {seq: rtt_ms} for every probe that came back
    payload_bytes   filler bytes per probe (header excluded)
    duration_s      length of the sending window
    """
    received = len(rtts_ms_by_seq)
    ordered = [rtts_ms_by_seq[k] for k in sorted(rtts_ms_by_seq)]
    loss_pct = 100.0 * (sent - received) / sent if sent else 0.0
    goodput_kbps = (received * payload_bytes * 8 / duration_s / 1000.0) if duration_s > 0 else 0.0
    return {
        "sent": sent,
        "received": received,
        "loss_pct": round(loss_pct, 3),
        "rtt_p50_ms": round(percentile(ordered, 50), 3),
        "rtt_p95_ms": round(percentile(ordered, 95), 3),
        "rtt_p99_ms": round(percentile(ordered, 99), 3),
        "rtt_max_ms": round(max(ordered), 3) if ordered else float("nan"),
        "jitter_mean_ms": round(mean_jitter(ordered), 3),
        "goodput_kbps": round(goodput_kbps, 3),
    }
