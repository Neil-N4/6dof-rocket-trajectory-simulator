from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from rocket_sim.config import load_config
from rocket_sim.estimation import run_ekf_position_velocity
from rocket_sim.simulate import run_simulation


def test_ekf_runs_and_produces_finite_rmse() -> None:
    root = Path(__file__).resolve().parents[1]
    cfg = load_config(root / "configs" / "nominal.yaml", root)
    cfg = replace(cfg, sim_duration_s=120.0)
    sim = run_simulation(cfg)
    ekf = run_ekf_position_velocity(sim, gps_period_steps=8, seed=1)
    assert ekf.gps_updates > 0
    assert ekf.rmse_position_m > 0.0
    assert ekf.rmse_velocity_m_s > 0.0
