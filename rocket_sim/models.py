from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class Stage:
    name: str
    dry_mass_kg: float
    propellant_mass_kg: float
    max_thrust_n: float
    isp_s: float
    burn_time_s: float
    reference_area_m2: float
    cd: float
    inertia_kg_m2: np.ndarray
    lever_arm_m: np.ndarray = field(default_factory=lambda: np.array([0.0, 0.0, -1.0]))
    max_gimbal_deg: float = 6.0


@dataclass(frozen=True)
class RocketConfig:
    stages: list[Stage]
    payload_mass_kg: float
    launch_lat_deg: float = 28.5618571
    launch_lon_deg: float = -80.577366
    earth_radius_m: float = 6_371_000.0
    earth_mu_m3_s2: float = 3.986004418e14
    g0_m_s2: float = 9.80665
    thrust_curve_csv: Path | None = None
    dt_s: float = 0.05
    sim_duration_s: float = 240.0
    staging_delay_s: float = 2.0
    pid_kp: float = 10.0
    pid_ki: float = 0.2
    pid_kd: float = 3.5


class FlightPhase(IntEnum):
    IGNITION = 0
    ASCENT = 1
    STAGING = 2
    COAST = 3
    APOGEE = 4
    REENTRY = 5
    LANDING = 6


@dataclass
class SimState:
    position_m: np.ndarray
    velocity_m_s: np.ndarray
    euler_rad: np.ndarray
    body_rates_rad_s: np.ndarray
    mass_kg: float

    def to_vector(self) -> np.ndarray:
        return np.concatenate(
            [
                self.position_m,
                self.velocity_m_s,
                self.euler_rad,
                self.body_rates_rad_s,
                np.array([self.mass_kg]),
            ]
        )

    @staticmethod
    def from_vector(vec: np.ndarray) -> "SimState":
        return SimState(
            position_m=vec[0:3],
            velocity_m_s=vec[3:6],
            euler_rad=vec[6:9],
            body_rates_rad_s=vec[9:12],
            mass_kg=float(vec[12]),
        )
