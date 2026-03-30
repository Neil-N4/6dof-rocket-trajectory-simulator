from __future__ import annotations

import argparse
import csv
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


@dataclass
class EventMetric:
    duration_s: float
    runtime_ms: float
    throughput_eps: float
    mean_latency_ms: float
    max_latency_ms: float
    pushed: int
    dropped: int


@dataclass
class SimdMetric:
    trajectories: int
    steps: int
    scalar_ms: float
    batch_ms: float
    speedup_x: float
    simd_mode: str


def _run(cmd: list[str], cwd: Path) -> str:
    return subprocess.check_output(cmd, cwd=cwd, text=True)


def _extract(text: str, key: str) -> float:
    m = re.search(rf"{re.escape(key)}=([0-9eE+.-]+)", text)
    if not m:
        raise ValueError(f"Missing key '{key}'")
    return float(m.group(1))


def event_sweep(root: Path, build_dir: Path, out_dir: Path) -> list[EventMetric]:
    rows: list[EventMetric] = []
    for d in (200.0, 400.0, 800.0, 1200.0):
        summary = out_dir / f"event_summary_{int(d)}.txt"
        out = _run(
            [
                str(build_dir / "cpp_event_engine"),
                "--config",
                "configs/nominal.yaml",
                "--duration",
                f"{d}",
                "--summary",
                str(summary),
            ],
            root,
        )
        rows.append(
            EventMetric(
                duration_s=d,
                runtime_ms=_extract(out, "Runtime"),
                throughput_eps=_extract(out, "throughput"),
                mean_latency_ms=_extract(out, "Mean latency"),
                max_latency_ms=_extract(out, "max"),
                pushed=int(_extract(out, "pushed")),
                dropped=int(_extract(out, "dropped")),
            )
        )
    csv_path = out_dir / "event_engine_metrics.csv"
    with csv_path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "duration_s",
                "runtime_ms",
                "throughput_events_per_s",
                "mean_latency_ms",
                "max_latency_ms",
                "events_pushed",
                "events_dropped",
            ]
        )
        for r in rows:
            w.writerow([r.duration_s, r.runtime_ms, r.throughput_eps, r.mean_latency_ms, r.max_latency_ms, r.pushed, r.dropped])

    fig, ax1 = plt.subplots(figsize=(7, 4))
    ax2 = ax1.twinx()
    x = [r.duration_s for r in rows]
    ax1.plot(x, [r.throughput_eps for r in rows], marker="o", label="Throughput (events/s)")
    ax2.plot(x, [r.mean_latency_ms for r in rows], marker="s", color="tab:red", label="Mean latency (ms)")
    ax1.set_xlabel("Simulation duration (s)")
    ax1.set_ylabel("Throughput (events/s)")
    ax2.set_ylabel("Mean latency (ms)")
    ax1.set_title("Event Engine Throughput and Latency")
    fig.tight_layout()
    fig.savefig(out_dir / "event_engine_throughput_latency.png", dpi=180)
    plt.close(fig)
    return rows


def simd_benchmark(root: Path, build_dir: Path, out_dir: Path) -> SimdMetric:
    out = _run([str(build_dir / "cpp_simd_batch_rk4"), "--trajectories", "16384", "--steps", "500"], root)
    metric = SimdMetric(
        trajectories=16384,
        steps=500,
        scalar_ms=_extract(out, "scalar_ms"),
        batch_ms=_extract(out, "batch_ms"),
        speedup_x=_extract(out, "speedup"),
        simd_mode=re.search(r"simd_mode=(\S+)", out).group(1) if re.search(r"simd_mode=(\S+)", out) else "unknown",
    )
    csv_path = out_dir / "simd_metrics.csv"
    with csv_path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["trajectories", "steps", "scalar_ms", "batch_ms", "speedup_x", "simd_mode"])
        w.writerow([metric.trajectories, metric.steps, metric.scalar_ms, metric.batch_ms, metric.speedup_x, metric.simd_mode])

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar(["Scalar", f"Batch ({metric.simd_mode})"], [metric.scalar_ms, metric.batch_ms], color=["#4e79a7", "#f28e2b"])
    ax.set_ylabel("Runtime (ms)")
    ax.set_title(f"RK4 Batch Benchmark ({metric.speedup_x:.2f}x)")
    fig.tight_layout()
    fig.savefig(out_dir / "simd_runtime_comparison.png", dpi=180)
    plt.close(fig)
    return metric


def ekf_noise_sweep(root: Path, out_dir: Path) -> None:
    import numpy as np
    from dataclasses import replace

    from rocket_sim.config import load_config
    from rocket_sim.estimation import run_ekf_position_velocity
    from rocket_sim.simulate import run_simulation

    cfg = load_config(Path("configs/nominal.yaml"), root)
    cfg = replace(cfg, sim_duration_s=240.0)
    sim = run_simulation(cfg)

    pos_sigmas = [4.0, 8.0, 12.0, 16.0, 20.0]
    rows = []
    for s in pos_sigmas:
        ekf = run_ekf_position_velocity(sim, gps_pos_sigma_m=s, gps_vel_sigma_m_s=max(0.4, s / 10.0), seed=7)
        rows.append((s, ekf.rmse_position_m, ekf.rmse_velocity_m_s, ekf.gps_updates))

    csv_path = out_dir / "ekf_noise_sweep.csv"
    with csv_path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["gps_pos_sigma_m", "rmse_position_m", "rmse_velocity_m_s", "gps_updates"])
        w.writerows(rows)

    arr = np.array(rows)
    fig, ax1 = plt.subplots(figsize=(7, 4))
    ax2 = ax1.twinx()
    ax1.plot(arr[:, 0], arr[:, 1], marker="o", label="Position RMSE (m)")
    ax2.plot(arr[:, 0], arr[:, 2], marker="s", color="tab:red", label="Velocity RMSE (m/s)")
    ax1.set_xlabel("GPS position noise sigma (m)")
    ax1.set_ylabel("Position RMSE (m)")
    ax2.set_ylabel("Velocity RMSE (m/s)")
    ax1.set_title("EKF Error vs Sensor Noise")
    fig.tight_layout()
    fig.savefig(out_dir / "ekf_rmse_vs_noise.png", dpi=180)
    plt.close(fig)


def write_report(root: Path, out_dir: Path, event_rows: list[EventMetric], simd: SimdMetric) -> None:
    best_event = max(event_rows, key=lambda r: r.throughput_eps)
    report = root / "docs" / "PERF_PROFILE_REPORT.md"
    report.write_text(
        "\n".join(
            [
                "# Perf Profile Report",
                "",
                "## Summary",
                f"- Event engine best throughput: `{best_event.throughput_eps:,.0f} events/s` at `{best_event.duration_s:.0f}s` scenario duration",
                f"- Event engine mean/max latency: `{best_event.mean_latency_ms:.4f} / {best_event.max_latency_ms:.4f} ms`",
                f"- RK4 batch speedup: `{simd.speedup_x:.3f}x` (`{simd.simd_mode}` mode)",
                "",
                "## Notes",
                "- On Apple Silicon, SIMD mode may fall back to scalar due to AVX2 unavailability.",
                "- Run the same benchmark on x86_64 Linux to collect AVX2 numbers for resume/interview claims.",
                "",
                "## Artifacts",
                "- `outputs/nextgen/event_engine_metrics.csv`",
                "- `outputs/nextgen/event_engine_throughput_latency.png`",
                "- `outputs/nextgen/simd_metrics.csv`",
                "- `outputs/nextgen/simd_runtime_comparison.png`",
                "- `outputs/nextgen/ekf_noise_sweep.csv`",
                "- `outputs/nextgen/ekf_rmse_vs_noise.png`",
            ]
        )
        + "\n"
    )


def main() -> None:
    p = argparse.ArgumentParser(description="Generate event/SIMD/EKF performance artifacts and profile report.")
    p.add_argument("--build-dir", type=Path, default=Path("build"))
    p.add_argument("--outdir", type=Path, default=Path("outputs/nextgen"))
    args = p.parse_args()

    root = Path(__file__).resolve().parents[1]
    build_dir = (root / args.build_dir).resolve()
    out_dir = (root / args.outdir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    event_rows = event_sweep(root, build_dir, out_dir)
    simd = simd_benchmark(root, build_dir, out_dir)
    ekf_noise_sweep(root, out_dir)
    write_report(root, out_dir, event_rows, simd)
    print(f"wrote={out_dir}")
    print("report=docs/PERF_PROFILE_REPORT.md")


if __name__ == "__main__":
    main()

