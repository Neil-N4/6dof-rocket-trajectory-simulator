from __future__ import annotations

import argparse
from dataclasses import replace
from pathlib import Path

import numpy as np

from rocket_sim.config import load_config
from rocket_sim.plotting import save_csv, save_plots
from rocket_sim.simulate import run_simulation
from rocket_sim.validation import baseline_trajectory_error_percent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Multi-Stage Rocket Dynamics Simulator")
    parser.add_argument("--config", type=Path, default=Path("configs/nominal.yaml"), help="Scenario YAML config path")
    parser.add_argument("--dt", type=float, default=None, help="Override integration timestep in seconds")
    parser.add_argument("--duration", type=float, default=None, help="Override simulation duration in seconds")
    parser.add_argument("--seed", type=int, default=42, help="Deterministic seed for reproducible runs")
    parser.add_argument("--out", type=Path, default=Path("outputs"), help="Output directory")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = Path(__file__).resolve().parent
    np.random.seed(args.seed)

    cfg = load_config(args.config if args.config else None, root)
    if args.dt is not None:
        cfg = replace(cfg, dt_s=args.dt)
    if args.duration is not None:
        cfg = replace(cfg, sim_duration_s=args.duration)

    result = run_simulation(cfg)
    baseline_error_pct, scipy_error_pct = baseline_trajectory_error_percent()

    out_dir = (root / args.out).resolve()
    plot_paths = save_plots(result, out_dir)
    csv_path = out_dir / "flight_states.csv"
    save_csv(result, csv_path)

    print(f"Scenario config: {args.config}")
    print(f"Seed: {args.seed}")
    print(f"Apogee: {result.apogee_m/1000.0:.2f} km at t={result.apogee_time_s:.1f} s")
    print(f"Max-Q (all): {result.max_q_pa/1000.0:.2f} kPa at t={result.max_q_time_s:.1f} s")
    print(
        f"Max-Q (0-80 km ascent): {result.max_q_under_80km_pa/1000.0:.2f} kPa "
        f"at t={result.max_q_under_80km_time_s:.1f} s"
    )
    print(f"Steady-state attitude error (t>40s): {result.steady_state_attitude_error_deg:.2f} deg")
    print(
        f"RK4 trajectory error vs analytical baseline: {baseline_error_pct:.3f}% "
        f"(SciPy cross-check: {scipy_error_pct:.3f}%)"
    )
    if result.event_times_s:
        events = ", ".join(f"{name}={time_s:.1f}s" for name, time_s in sorted(result.event_times_s.items()))
        print(f"Events: {events}")
    print(f"CSV: {csv_path}")
    for p in plot_paths:
        print(f"Plot: {p}")


if __name__ == "__main__":
    main()
