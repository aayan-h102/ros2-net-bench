import math

import pytest

from net_bench import metrics


def test_pack_unpack_roundtrip():
    data = metrics.pack(42, 123_456_789_012, 100)
    assert len(data) == metrics.HEADER_BYTES + 100
    assert metrics.unpack(data) == (42, 123_456_789_012)


def test_pack_zero_payload():
    assert len(metrics.pack(0, 0, 0)) == metrics.HEADER_BYTES


def test_pack_rejects_negative_payload():
    with pytest.raises(ValueError):
        metrics.pack(0, 0, -1)


def test_unpack_rejects_short_message():
    with pytest.raises(ValueError):
        metrics.unpack(b"\x00" * 5)


def test_percentile_matches_linear_interpolation():
    vals = [10, 20, 30, 40]
    assert metrics.percentile(vals, 0) == 10
    assert metrics.percentile(vals, 100) == 40
    assert metrics.percentile(vals, 50) == 25
    assert metrics.percentile(vals, 95) == pytest.approx(38.5)


def test_percentile_empty_is_nan():
    assert math.isnan(metrics.percentile([], 50))


def test_mean_jitter():
    assert metrics.mean_jitter([10, 12, 9, 9]) == pytest.approx((2 + 3 + 0) / 3)
    assert metrics.mean_jitter([5]) == 0.0


def test_summarize_with_loss():
    rtts = {0: 10.0, 1: 12.0, 3: 11.0}  # seq 2 lost
    s = metrics.summarize(sent=4, rtts_ms_by_seq=rtts, payload_bytes=100, duration_s=1.0)
    assert s["sent"] == 4
    assert s["received"] == 3
    assert s["loss_pct"] == 25.0
    assert s["rtt_p50_ms"] == 11.0
    assert s["rtt_max_ms"] == 12.0
    # jitter in sequence order: |12-10|, |11-12| -> 1.5
    assert s["jitter_mean_ms"] == 1.5
    # 3 payloads x 100 B x 8 bits / 1 s = 2.4 kb/s
    assert s["goodput_kbps"] == 2.4


def test_summarize_nothing_sent():
    s = metrics.summarize(sent=0, rtts_ms_by_seq={}, payload_bytes=100, duration_s=1.0)
    assert s["loss_pct"] == 0.0
    assert s["received"] == 0
