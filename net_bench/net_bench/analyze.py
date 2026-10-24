"""Turn results/summary.csv into a markdown report (and plots if matplotlib is installed).

Usage: python3 net_bench/net_bench/analyze.py results/summary.csv
"""

import csv
import os
import sys

PROFILE_ORDER = ["none", "near", "mid", "far", "custom"]
COLUMNS = [
    ("profile", "Profile"), ("rate_hz", "Rate (Hz)"), ("payload_bytes", "Payload (B)"),
    ("loss_pct", "Loss (%)"), ("rtt_p50_ms", "RTT p50 (ms)"), ("rtt_p95_ms", "RTT p95 (ms)"),
    ("jitter_mean_ms", "Jitter (ms)"), ("goodput_kbps", "Goodput (kb/s)"),
]


def load(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def sort_key(row):
    p = row["profile"]
    rank = PROFILE_ORDER.index(p) if p in PROFILE_ORDER else len(PROFILE_ORDER)
    return (rank, float(row["rate_hz"]), int(float(row["payload_bytes"])))


def markdown_table(rows):
    rows = sorted(rows, key=sort_key)
    head = "| " + " | ".join(h for _, h in COLUMNS) + " |"
    sep = "| " + " | ".join("---" for _ in COLUMNS) + " |"
    body = []
    for r in rows:
        cells = []
        for key, _ in COLUMNS:
            v = r[key]
            if key in ("rate_hz", "payload_bytes"):
                v = str(int(float(v)))
            cells.append(v)
        body.append("| " + " | ".join(cells) + " |")
    return "\n".join([head, sep, *body])


def plot(rows, out_dir):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed; skipping plots (pip install matplotlib)")
        return []

    rows = sorted(rows, key=sort_key)
    profiles = [p for p in PROFILE_ORDER if any(r["profile"] == p for r in rows)]
    combos = sorted({(float(r["rate_hz"]), int(float(r["payload_bytes"]))) for r in rows})
    made = []
    for metric, ylabel, fname in [
        ("rtt_p95_ms", "RTT p95 (ms)", "latency_p95.png"),
        ("loss_pct", "Packet loss (%)", "loss.png"),
    ]:
        fig, ax = plt.subplots(figsize=(7, 4))
        width = 0.8 / max(len(combos), 1)
        for i, (rate, payload) in enumerate(combos):
            ys = []
            for p in profiles:
                match = [r for r in rows if r["profile"] == p and float(r["rate_hz"]) == rate
                         and int(float(r["payload_bytes"])) == payload]
                ys.append(float(match[-1][metric]) if match else 0.0)
            xs = [j + i * width for j in range(len(profiles))]
            ax.bar(xs, ys, width, label=f"{int(rate)} Hz, {payload} B")
        ax.set_xticks([j + width * (len(combos) - 1) / 2 for j in range(len(profiles))])
        ax.set_xticklabels(profiles)
        ax.set_xlabel("Simulated link profile")
        ax.set_ylabel(ylabel)
        ax.legend(fontsize=8)
        fig.tight_layout()
        path = os.path.join(out_dir, fname)
        fig.savefig(path, dpi=150)
        plt.close(fig)
        made.append(path)
    return made


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    path = argv[0] if argv else "results/summary.csv"
    if not os.path.exists(path):
        print(f"{path} not found. Run scripts/run_matrix.sh first.", file=sys.stderr)
        return 1
    rows = load(path)
    out_dir = os.path.dirname(path) or "."
    report = "# Link benchmark results\n\n" + markdown_table(rows) + "\n"
    for img in plot(rows, out_dir):
        report += f"\n![{os.path.basename(img)}]({os.path.basename(img)})\n"
    report_path = os.path.join(out_dir, "report.md")
    with open(report_path, "w") as f:
        f.write(report)
    print(report)
    print(f"Wrote {report_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
