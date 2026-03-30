from __future__ import annotations

import argparse
from dataclasses import replace
from pathlib import Path

from rocket_sim.config import load_config
from rocket_sim.estimation import run_ekf_position_velocity
from rocket_sim.simulate import run_simulation


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run EKF state-estimation demo on simulated flight telemetry.")
    p.add_argument("--config", type=Path, default=Path("configs/nominal.yaml"))
    p.add_argument("--dt", type=float, default=None)
    p.add_argument("--duration", type=float, default=None)
    p.add_argument("--gps-period-steps", type=int, default=10)
    p.add_argument("--imu-sigma", type=float, default=0.25)
    p.add_argument("--gps-pos-sigma", type=float, default=8.0)
    p.add_argument("--gps-vel-sigma", type=float, default=0.8)
    p.add_argument("--seed", type=int, default=7)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    root = Path(__file__).resolve().parents[1]
    cfg = load_config(args.config, root)
    if args.dt is not None:
        cfg = replace(cfg, dt_s=args.dt)
    if args.duration is not None:
        cfg = replace(cfg, sim_duration_s=args.duration)

    sim = run_simulation(cfg)
    ekf = run_ekf_position_velocity(
        sim,
        imu_accel_sigma_m_s2=args.imu_sigma,
        gps_pos_sigma_m=args.gps_pos_sigma,
        gps_vel_sigma_m_s=args.gps_vel_sigma,
        gps_period_steps=args.gps_period_steps,
        seed=args.seed,
    )

    print(f"samples={len(sim.time_s)}")
    print(f"gps_updates={ekf.gps_updates}")
    print(f"rmse_position_m={ekf.rmse_position_m:.3f}")
    print(f"rmse_velocity_m_s={ekf.rmse_velocity_m_s:.3f}")


if __name__ == "__main__":
    main()

