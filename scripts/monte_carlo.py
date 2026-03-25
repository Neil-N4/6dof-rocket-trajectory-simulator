from __future__ import annotations

import argparse
import csv
import json
from dataclasses import replace
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from rocket_sim.config import load_config
from rocket_sim.models import RocketConfig, Stage
from rocket_sim.simulate import run_simulation


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Monte Carlo dispersion runner")
    p.add_argument("--config", type=Path, default=Path("configs/nominal.yaml"))
    p.add_argument("--runs", type=int, default=500)
    p.add_argument("--seed", type=int, default=123)
    p.add_argument("--outdir", type=Path, default=Path("outputs/monte_carlo"))
    p.add_argument("--thrust_sigma", type=float, default=0.03)
    p.add_argument("--mass_sigma", type=float, default=0.02)
    p.add_argument("--cd_sigma", type=float, default=0.05)
    p.add_argument("--wind_sigma_m_s", type=float, default=20.0)
    p.add_argument("--duration", type=float, default=1200.0, help="Override simulation duration per run for speed")
    p.add_argument("--dt", type=float, default=0.15, help="Override simulation timestep per run")
    return p.parse_args()


def perturb_config(base: RocketConfig, rng: np.random.Generator, args: argparse.Namespace) -> RocketConfig:
    stages: list[Stage] = []
    for s in base.stages:
        thrust_scale = max(0.75, 1.0 + rng.normal(0.0, args.thrust_sigma))
        cd_scale = max(0.6, 1.0 + rng.normal(0.0, args.cd_sigma))
        mass_scale = max(0.75, 1.0 + rng.normal(0.0, args.mass_sigma))
        prop_scale = max(0.75, 1.0 + rng.normal(0.0, args.mass_sigma))
        stages.append(
            replace(
                s,
                max_thrust_n=s.max_thrust_n * thrust_scale,
                cd=s.cd * cd_scale,
                dry_mass_kg=s.dry_mass_kg * mass_scale,
                propellant_mass_kg=s.propellant_mass_kg * prop_scale,
            )
        )

    wind = base.wind_i_m_s + np.array([0.0, rng.normal(0.0, args.wind_sigma_m_s), 0.0])
    return replace(base, stages=stages, wind_i_m_s=wind)


def percentile(values: list[float], p: float) -> float:
    return float(np.percentile(np.array(values, dtype=float), p))


def main() -> None:
    args = parse_args()
    project_root = Path(__file__).resolve().parents[1]
    outdir = (project_root / args.outdir).resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(args.seed)
    base = load_config(args.config, project_root)
    base = replace(base, sim_duration_s=float(args.duration), dt_s=float(args.dt))

    rows: list[dict[str, float]] = []
    apogees_km: list[float] = []
    max_q_kpa: list[float] = []
    attitude_deg: list[float] = []

    for i in range(args.runs):
        cfg = perturb_config(base, rng, args)
        res = run_simulation(cfg)
        row = {
            "run": i,
            "apogee_km": res.apogee_m / 1000.0,
            "max_q_kpa": res.max_q_under_80km_pa / 1000.0,
            "steady_attitude_error_deg": res.steady_state_attitude_error_deg,
        }
        rows.append(row)
        apogees_km.append(row["apogee_km"])
        max_q_kpa.append(row["max_q_kpa"])
        attitude_deg.append(row["steady_attitude_error_deg"])
        if (i + 1) % max(args.runs // 10, 1) == 0:
            print(f"Completed {i + 1}/{args.runs} runs...")

    csv_path = outdir / "monte_carlo_runs.csv"
    with csv_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["run", "apogee_km", "max_q_kpa", "steady_attitude_error_deg"])
        writer.writeheader()
        writer.writerows(rows)

    summary = {
        "runs": args.runs,
        "seed": args.seed,
        "apogee_km": {"p50": percentile(apogees_km, 50), "p95": percentile(apogees_km, 95)},
        "max_q_kpa": {"p50": percentile(max_q_kpa, 50), "p95": percentile(max_q_kpa, 95)},
        "steady_attitude_error_deg": {"p50": percentile(attitude_deg, 50), "p95": percentile(attitude_deg, 95)},
    }
    summary_path = outdir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2))

    fig, axs = plt.subplots(1, 2, figsize=(10, 4))
    axs[0].hist(apogees_km, bins=30, alpha=0.85)
    axs[0].set_title("Apogee Dispersion (km)")
    axs[0].set_xlabel("Apogee (km)")
    axs[0].set_ylabel("Count")

    axs[1].hist(max_q_kpa, bins=30, alpha=0.85)
    axs[1].set_title("Max-Q Dispersion (kPa)")
    axs[1].set_xlabel("Max-Q (kPa)")
    axs[1].set_ylabel("Count")

    fig.tight_layout()
    fig.savefig(outdir / "dispersion_histograms.png", dpi=180)

    print(f"Wrote {csv_path}")
    print(f"Wrote {summary_path}")
    print(f"P50/P95 Apogee (km): {summary['apogee_km']['p50']:.2f} / {summary['apogee_km']['p95']:.2f}")
    print(f"P50/P95 Max-Q (kPa): {summary['max_q_kpa']['p50']:.2f} / {summary['max_q_kpa']['p95']:.2f}")


if __name__ == "__main__":
    main()
