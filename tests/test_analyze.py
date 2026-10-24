import csv

from net_bench import analyze

FIELDS = ["label", "profile", "rmw", "rate_hz", "payload_bytes", "duration_s", "sent", "received",
          "loss_pct", "rtt_p50_ms", "rtt_p95_ms", "rtt_p99_ms", "rtt_max_ms", "jitter_mean_ms",
          "goodput_kbps"]


def row(profile, rate, payload, loss):
    return {"label": f"{profile}-{rate}-{payload}", "profile": profile, "rmw": "rmw_fastrtps_cpp",
            "rate_hz": rate, "payload_bytes": payload, "duration_s": 30, "sent": 300,
            "received": 290, "loss_pct": loss, "rtt_p50_ms": 1.2, "rtt_p95_ms": 2.5,
            "rtt_p99_ms": 3.0, "rtt_max_ms": 4.0, "jitter_mean_ms": 0.3, "goodput_kbps": 7.7}


def test_table_orders_profiles_near_to_far(tmp_path):
    path = tmp_path / "summary.csv"
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for r in [row("far", 10.0, 100, 8.1), row("none", 10.0, 100, 0.0), row("mid", 25.0, 500, 2.2)]:
            w.writerow(r)

    table = analyze.markdown_table(analyze.load(path))
    lines = table.splitlines()
    assert lines[0].startswith("| Middleware | Profile")
    profiles = [line.split("|")[2].strip() for line in lines[2:]]
    assert profiles == ["none", "mid", "far"]
    assert "| DDS (Fast DDS) | none | 10 | 100 |" in lines[2]


def test_table_groups_by_middleware(tmp_path):
    path = tmp_path / "summary.csv"
    zen = row("none", 10.0, 100, 0.0)
    zen["rmw"] = "rmw_zenoh_cpp"
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerow(zen)
        w.writerow(row("far", 10.0, 100, 8.0))
    lines = analyze.markdown_table(analyze.load(path)).splitlines()
    assert [line.split("|")[1].strip() for line in lines[2:]] == ["DDS (Fast DDS)", "Zenoh"]


def test_main_writes_report(tmp_path):
    path = tmp_path / "summary.csv"
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerow(row("none", 10.0, 100, 0.0))
    assert analyze.main([str(path)]) == 0
    assert (tmp_path / "report.md").read_text().startswith("# Link benchmark results")


def test_main_missing_file(tmp_path):
    assert analyze.main([str(tmp_path / "nope.csv")]) == 1
