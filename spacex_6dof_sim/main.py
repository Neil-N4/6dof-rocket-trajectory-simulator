from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from rocket_sim.models import RocketConfig, Stage
from rocket_sim.plotting import save_csv, save_plots
from rocket_sim.simulate import run_simulation


def build_default_config(project_root: Path) -> RocketConfig:
    stages = [
        Stage(
            name="Stage 1",
            dry_mass_kg=22_000.0,
            propellant_mass_kg=395_000.0,
            max_thrust_n=7_600_000.0,
            isp_s=282.0,
            burn_time_s=162.0,
            reference_area_m2=10.8,
            cd=0.34,
            inertia_kg_m2=np.diag([8.5e6, 8.5e6, 2.7e5]),
            lever_arm_m=np.array([0.0, 0.0, -8.0]),
        ),
        Stage(
            name="Stage 2",
            dry_mass_kg=4_000.0,
            propellant_mass_kg=92_000.0,
            max_thrust_n=981_000.0,
            isp_s=348.0,
            burn_time_s=340.0,
            reference_area_m2=3.5,
            cd=0.22,
            inertia_kg_m2=np.diag([8.0e5, 8.0e5, 5.0e4]),
            lever_arm_m=np.array([0.0, 0.0, -3.0]),
        ),
    ]

    return RocketConfig(
        stages=stages,
        payload_mass_kg=15_600.0,
        thrust_curve_csv=project_root / "data" / "thrust_curve.csv",
        dt_s=0.1,
        sim_duration_s=520.0,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="6-DOF Rocket Trajectory Simulator")
    parser.add_argument("--dt", type=float, default=0.1, help="Integration timestep in seconds")
    parser.add_argument("--duration", type=float, default=520.0, help="Simulation duration in seconds")
    parser.add_argument("--out", type=Path, default=Path("outputs"), help="Output directory")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = Path(__file__).resolve().parent

    cfg = build_default_config(root)
    cfg = RocketConfig(
        stages=cfg.stages,
        payload_mass_kg=cfg.payload_mass_kg,
        thrust_curve_csv=cfg.thrust_curve_csv,
        dt_s=args.dt,
        sim_duration_s=args.duration,
    )

    result = run_simulation(cfg)

    out_dir = (root / args.out).resolve()
    plot_paths = save_plots(result, out_dir)
    csv_path = out_dir / "flight_states.csv"
    save_csv(result, csv_path)

    print(f"Apogee: {result.apogee_m/1000.0:.2f} km at t={result.apogee_time_s:.1f} s")
    print(f"Max-Q: {result.max_q_pa/1000.0:.2f} kPa at t={result.max_q_time_s:.1f} s")
    print(f"CSV: {csv_path}")
    for p in plot_paths:
        print(f"Plot: {p}")


if __name__ == "__main__":
    main()
