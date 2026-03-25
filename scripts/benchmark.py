from __future__ import annotations

import argparse
import json
import subprocess
import time
from dataclasses import replace
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from rocket_sim.config import load_config
from rocket_sim.simulate import run_simulation


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Benchmark Python vs C++ simulation runtime")
    p.add_argument("--config", type=Path, default=Path("configs/nominal.yaml"))
    p.add_argument("--runs", type=int, default=5)
    p.add_argument("--duration", type=float, default=1200.0)
    p.add_argument("--dt", type=float, default=0.15)
    p.add_argument("--cpp-bin", type=Path, default=Path("./cpp_sim"))
    p.add_argument("--outdir", type=Path, default=Path("outputs/benchmarks"))
    return p.parse_args()


def avg(values: list[float]) -> float:
    return sum(values) / max(len(values), 1)


def main() -> None:
    args = parse_args()
    root = Path(__file__).resolve().parents[1]
    outdir = (root / args.outdir).resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    cfg = load_config(args.config, root)
    cfg = replace(cfg, sim_duration_s=args.duration, dt_s=args.dt)

    py_times = []
    for _ in range(args.runs):
        t0 = time.perf_counter()
        run_simulation(cfg)
        py_times.append(time.perf_counter() - t0)

    cpp_bin = (root / args.cpp_bin).resolve()
    cpp_times = []
    for _ in range(args.runs):
        t0 = time.perf_counter()
        subprocess.run(
            [
                str(cpp_bin),
                "--config",
                str((root / args.config).resolve()),
                "--dt",
                str(args.dt),
                "--duration",
                str(args.duration),
                "--out",
                str((outdir / "cpp_bench.csv").resolve()),
                "--summary",
                str((outdir / "cpp_bench_summary.txt").resolve()),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        cpp_times.append(time.perf_counter() - t0)

    py_avg = avg(py_times)
    cpp_avg = avg(cpp_times)
    speedup = py_avg / max(cpp_avg, 1e-9)

    payload = {
        "scenario": str(args.config),
        "runs": args.runs,
        "duration_s": args.duration,
        "dt_s": args.dt,
        "python_avg_s": py_avg,
        "cpp_avg_s": cpp_avg,
        "speedup_x": speedup,
    }
    (outdir / "benchmark_summary.json").write_text(json.dumps(payload, indent=2))

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar(["Python", "C++"], [py_avg, cpp_avg])
    ax.set_ylabel("Average runtime (s)")
    ax.set_title(f"Runtime Comparison (speedup {speedup:.2f}x)")
    fig.tight_layout()
    fig.savefig(outdir / "runtime_comparison.png", dpi=180)

    report = root / "docs" / "PERFORMANCE_REPORT.md"
    report.write_text(
        "\n".join(
            [
                "# Performance Report",
                "",
                f"- Scenario: `{args.config}`",
                f"- Runs per implementation: `{args.runs}`",
                f"- Duration / dt: `{args.duration}` s / `{args.dt}` s",
                f"- Python average runtime: `{py_avg:.4f}` s",
                f"- C++ average runtime: `{cpp_avg:.4f}` s",
                f"- Speedup (Python / C++): `{speedup:.2f}x`",
                "",
                "Artifacts:",
                "",
                "- `outputs/benchmarks/benchmark_summary.json`",
                "- `outputs/benchmarks/runtime_comparison.png`",
            ]
        )
        + "\n"
    )

    print(f"Python avg: {py_avg:.4f}s")
    print(f"C++ avg: {cpp_avg:.4f}s")
    print(f"Speedup: {speedup:.2f}x")


if __name__ == "__main__":
    main()
