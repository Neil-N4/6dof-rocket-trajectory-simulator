from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .atmosphere import air_density_kg_m3
from .dynamics import StageRuntime, get_throttle, rk4_step
from .models import RocketConfig, SimState


@dataclass
class SimResult:
    time_s: np.ndarray
    states: np.ndarray
    altitude_m: np.ndarray
    speed_m_s: np.ndarray
    dynamic_pressure_pa: np.ndarray
    stage_index: np.ndarray
    max_q_pa: float
    max_q_time_s: float
    apogee_m: float
    apogee_time_s: float


def load_thrust_profile(config: RocketConfig) -> tuple[np.ndarray, np.ndarray]:
    if config.thrust_curve_csv is None:
        return np.array([]), np.array([])
    arr = np.loadtxt(config.thrust_curve_csv, delimiter=",", skiprows=1)
    if arr.ndim == 1:
        arr = arr.reshape(1, -1)
    return arr[:, 0], arr[:, 1]


def initial_state(config: RocketConfig) -> SimState:
    total_mass = config.payload_mass_kg + sum(s.dry_mass_kg + s.propellant_mass_kg for s in config.stages)
    return SimState(
        position_m=np.array([config.earth_radius_m, 0.0, 0.0]),
        velocity_m_s=np.zeros(3),
        euler_rad=np.array([0.0, 0.0, 0.0]),
        body_rates_rad_s=np.zeros(3),
        mass_kg=total_mass,
    )


def run_simulation(config: RocketConfig) -> SimResult:
    profile_t, profile_throttle = load_thrust_profile(config)
    n_steps = int(config.sim_duration_s / config.dt_s) + 1

    state = initial_state(config).to_vector()
    t_s = 0.0
    stage_idx = 0
    stage_elapsed_s = 0.0
    stage_remaining_prop = config.stages[0].propellant_mass_kg if config.stages else 0.0

    time_hist = np.zeros(n_steps)
    state_hist = np.zeros((n_steps, len(state)))
    alt_hist = np.zeros(n_steps)
    speed_hist = np.zeros(n_steps)
    q_hist = np.zeros(n_steps)
    stage_hist = np.zeros(n_steps, dtype=int)

    for i in range(n_steps):
        pos = state[0:3]
        vel = state[3:6]
        r = np.linalg.norm(pos)
        alt = max(r - config.earth_radius_m, 0.0)
        speed = np.linalg.norm(vel)
        rho = air_density_kg_m3(alt)
        q = 0.5 * rho * speed * speed

        time_hist[i] = t_s
        state_hist[i] = state
        alt_hist[i] = alt
        speed_hist[i] = speed
        q_hist[i] = q
        stage_hist[i] = stage_idx

        if i == n_steps - 1:
            break

        runtime = None
        if stage_idx < len(config.stages):
            runtime = StageRuntime(
                stage=config.stages[stage_idx],
                stage_index=stage_idx,
                stage_elapsed_s=stage_elapsed_s,
                stage_propellant_kg=stage_remaining_prop,
            )

        next_state = rk4_step(t_s, state, config.dt_s, runtime, config, profile_t, profile_throttle)

        if runtime is not None:
            stage = runtime.stage
            throttle = get_throttle(stage_elapsed_s, stage.burn_time_s, profile_t, profile_throttle)
            thrust = throttle * stage.max_thrust_n
            mdot = thrust / (stage.isp_s * config.g0_m_s2)
            burned = mdot * config.dt_s
            stage_remaining_prop = max(stage_remaining_prop - burned, 0.0)
            stage_elapsed_s += config.dt_s

            if stage_remaining_prop <= 0.0 or stage_elapsed_s >= stage.burn_time_s:
                next_state[12] -= stage.dry_mass_kg
                stage_idx += 1
                if stage_idx < len(config.stages):
                    stage_remaining_prop = config.stages[stage_idx].propellant_mass_kg
                    stage_elapsed_s = 0.0

        next_state[12] = max(next_state[12], config.payload_mass_kg)
        state = next_state
        t_s += config.dt_s

    max_q_idx = int(np.argmax(q_hist))
    apogee_idx = int(np.argmax(alt_hist))

    return SimResult(
        time_s=time_hist,
        states=state_hist,
        altitude_m=alt_hist,
        speed_m_s=speed_hist,
        dynamic_pressure_pa=q_hist,
        stage_index=stage_hist,
        max_q_pa=float(q_hist[max_q_idx]),
        max_q_time_s=float(time_hist[max_q_idx]),
        apogee_m=float(alt_hist[apogee_idx]),
        apogee_time_s=float(time_hist[apogee_idx]),
    )
