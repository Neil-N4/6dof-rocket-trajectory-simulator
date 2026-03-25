from __future__ import annotations

from pathlib import Path

import numpy as np

from rocket_sim.atmosphere import air_density_kg_m3
from rocket_sim.models import FlightPhase, RocketConfig, Stage
from rocket_sim.simulate import run_simulation
from rocket_sim.validation import baseline_trajectory_error_percent


def test_atmosphere_density_decreases_with_altitude() -> None:
    sea_level = air_density_kg_m3(0.0)
    ten_km = air_density_kg_m3(10_000.0)
    twenty_km = air_density_kg_m3(20_000.0)
    assert sea_level > ten_km > twenty_km >= 0.0


def test_simulation_runs_and_reaches_positive_altitude() -> None:
    stage = Stage(
        name="Test Stage",
        dry_mass_kg=1_000.0,
        propellant_mass_kg=3_000.0,
        max_thrust_n=150_000.0,
        isp_s=250.0,
        burn_time_s=30.0,
        reference_area_m2=1.5,
        cd=0.35,
        inertia_kg_m2=np.diag([5_000.0, 5_000.0, 2_500.0]),
    )
    cfg = RocketConfig(
        stages=[stage],
        payload_mass_kg=200.0,
        thrust_curve_csv=Path(__file__).resolve().parents[1] / "data" / "thrust_curve.csv",
        dt_s=0.1,
        sim_duration_s=40.0,
    )

    result = run_simulation(cfg)

    assert result.apogee_m > 0.0
    assert result.max_q_pa > 0.0
    assert result.states[-1, 12] < result.states[0, 12]


def test_staging_changes_stage_index() -> None:
    stages = [
        Stage(
            name="S1",
            dry_mass_kg=50.0,
            propellant_mass_kg=120.0,
            max_thrust_n=8_000.0,
            isp_s=220.0,
            burn_time_s=3.0,
            reference_area_m2=0.8,
            cd=0.4,
            inertia_kg_m2=np.diag([80.0, 80.0, 50.0]),
        ),
        Stage(
            name="S2",
            dry_mass_kg=20.0,
            propellant_mass_kg=80.0,
            max_thrust_n=4_000.0,
            isp_s=250.0,
            burn_time_s=4.0,
            reference_area_m2=0.4,
            cd=0.3,
            inertia_kg_m2=np.diag([50.0, 50.0, 20.0]),
        ),
    ]
    cfg = RocketConfig(stages=stages, payload_mass_kg=10.0, dt_s=0.05, sim_duration_s=10.0)

    result = run_simulation(cfg)

    assert result.stage_index.max() >= 1


def test_state_machine_reaches_expected_phases() -> None:
    stage = Stage(
        name="State Machine Stage",
        dry_mass_kg=700.0,
        propellant_mass_kg=2_500.0,
        max_thrust_n=180_000.0,
        isp_s=255.0,
        burn_time_s=45.0,
        reference_area_m2=1.2,
        cd=0.32,
        inertia_kg_m2=np.diag([4_000.0, 4_000.0, 2_000.0]),
    )
    cfg = RocketConfig(stages=[stage], payload_mass_kg=150.0, dt_s=0.1, sim_duration_s=220.0)
    result = run_simulation(cfg)
    phases = set(result.flight_phase.tolist())
    assert int(FlightPhase.IGNITION) in phases
    assert int(FlightPhase.ASCENT) in phases
    assert int(FlightPhase.COAST) in phases or int(FlightPhase.STAGING) in phases


def test_rk4_analytical_baseline_error_below_half_percent() -> None:
    analytical_error_pct, scipy_error_pct = baseline_trajectory_error_percent()
    assert analytical_error_pct < 0.5
    assert scipy_error_pct < 0.5
