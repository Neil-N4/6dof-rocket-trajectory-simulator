from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np
import yaml

from .models import RocketConfig, Stage


def default_config(project_root: Path) -> RocketConfig:
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
        sim_duration_s=2200.0,
    )


def _to_stage(entry: dict[str, Any]) -> Stage:
    inertia = np.array(entry["inertia_kg_m2"], dtype=float)
    if inertia.shape == (3,):
        inertia = np.diag(inertia)
    lever = np.array(entry.get("lever_arm_m", [0.0, 0.0, -1.0]), dtype=float)
    return Stage(
        name=str(entry["name"]),
        dry_mass_kg=float(entry["dry_mass_kg"]),
        propellant_mass_kg=float(entry["propellant_mass_kg"]),
        max_thrust_n=float(entry["max_thrust_n"]),
        isp_s=float(entry["isp_s"]),
        burn_time_s=float(entry["burn_time_s"]),
        reference_area_m2=float(entry["reference_area_m2"]),
        cd=float(entry["cd"]),
        inertia_kg_m2=inertia,
        lever_arm_m=lever,
        max_gimbal_deg=float(entry.get("max_gimbal_deg", 6.0)),
    )


def load_config(config_path: Path | None, project_root: Path) -> RocketConfig:
    base = default_config(project_root)
    if config_path is None:
        return base

    raw = yaml.safe_load(config_path.read_text())
    if not isinstance(raw, dict):
        raise ValueError(f"Invalid scenario config: {config_path}")

    stages = base.stages
    if "stages" in raw:
        stages = [_to_stage(s) for s in raw["stages"]]

    thrust_curve = base.thrust_curve_csv
    if "thrust_curve_csv" in raw and raw["thrust_curve_csv"] is not None:
        thrust_curve = (project_root / raw["thrust_curve_csv"]).resolve()

    wind = np.array(raw.get("wind_i_m_s", [0.0, 0.0, 0.0]), dtype=float)
    if wind.shape != (3,):
        raise ValueError("wind_i_m_s must be a 3-element vector.")

    return replace(
        base,
        stages=stages,
        payload_mass_kg=float(raw.get("payload_mass_kg", base.payload_mass_kg)),
        dt_s=float(raw.get("dt_s", base.dt_s)),
        sim_duration_s=float(raw.get("sim_duration_s", base.sim_duration_s)),
        staging_delay_s=float(raw.get("staging_delay_s", base.staging_delay_s)),
        pid_kp=float(raw.get("pid_kp", base.pid_kp)),
        pid_ki=float(raw.get("pid_ki", base.pid_ki)),
        pid_kd=float(raw.get("pid_kd", base.pid_kd)),
        wind_i_m_s=wind,
        thrust_curve_csv=thrust_curve,
    )
