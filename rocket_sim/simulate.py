from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .atmosphere import air_density_kg_m3
from .control import PIDController
from .dynamics import StageRuntime, get_throttle, rk4_step
from .models import FlightPhase, RocketConfig, SimState


@dataclass
class SimResult:
    time_s: np.ndarray
    states: np.ndarray
    altitude_m: np.ndarray
    speed_m_s: np.ndarray
    dynamic_pressure_pa: np.ndarray
    stage_index: np.ndarray
    flight_phase: np.ndarray
    gimbal_pitch_deg: np.ndarray
    gimbal_yaw_deg: np.ndarray
    max_q_pa: float
    max_q_time_s: float
    max_q_under_80km_pa: float
    max_q_under_80km_time_s: float
    apogee_m: float
    apogee_time_s: float
    max_attitude_error_deg: float
    steady_state_attitude_error_deg: float
    event_times_s: dict[str, float]


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
        euler_rad=np.zeros(3),
        body_rates_rad_s=np.zeros(3),
        mass_kg=total_mass,
    )


def target_pitch_rad(t_s: float) -> float:
    # Hold near-vertical for liftoff, then execute a smooth gravity turn.
    if t_s < 8.0:
        return 0.0
    return np.deg2rad(min((t_s - 8.0) * 0.28, 28.0))


def _phase_array(n_steps: int) -> np.ndarray:
    return np.zeros(n_steps, dtype=int)


def run_simulation(config: RocketConfig) -> SimResult:
    profile_t, profile_throttle = load_thrust_profile(config)
    n_steps = int(config.sim_duration_s / config.dt_s) + 1

    state = initial_state(config).to_vector()
    t_s = 0.0
    stage_idx = 0
    stage_elapsed_s = 0.0
    stage_remaining_prop = config.stages[0].propellant_mass_kg if config.stages else 0.0
    in_staging = False
    staging_elapsed_s = 0.0
    pending_stage_drop_dry_mass_kg = 0.0
    prev_altitude = 0.0
    prev_vertical_speed = 0.0

    pitch_pid = PIDController(config.pid_kp, config.pid_ki, config.pid_kd)
    yaw_pid = PIDController(config.pid_kp, config.pid_ki, config.pid_kd)

    phase = FlightPhase.IGNITION
    event_times_s: dict[str, float] = {}
    max_attitude_error_deg = 0.0
    steady_state_attitude_error_deg = 0.0

    time_hist = np.zeros(n_steps)
    state_hist = np.zeros((n_steps, len(state)))
    alt_hist = np.zeros(n_steps)
    speed_hist = np.zeros(n_steps)
    q_hist = np.zeros(n_steps)
    stage_hist = np.zeros(n_steps, dtype=int)
    phase_hist = _phase_array(n_steps)
    gimbal_pitch_hist = np.zeros(n_steps)
    gimbal_yaw_hist = np.zeros(n_steps)

    for i in range(n_steps):
        pos = state[0:3]
        vel = state[3:6]
        r = np.linalg.norm(pos)
        alt = max(r - config.earth_radius_m, 0.0)
        speed = np.linalg.norm(vel)
        rho = air_density_kg_m3(alt)
        q = 0.5 * rho * speed * speed
        radial_hat = pos / max(r, 1.0)
        vertical_speed = float(np.dot(vel, radial_hat))

        time_hist[i] = t_s
        state_hist[i] = state
        alt_hist[i] = alt
        speed_hist[i] = speed
        q_hist[i] = q
        stage_hist[i] = stage_idx
        phase_hist[i] = int(phase)

        if i == n_steps - 1:
            break

        runtime = None
        gimbal_pitch = 0.0
        gimbal_yaw = 0.0
        burning = (not in_staging) and stage_idx < len(config.stages) and stage_remaining_prop > 0.0
        if burning:
            target_pitch = target_pitch_rad(t_s)
            pitch_error = target_pitch - state[7]
            yaw_error = 0.0 - state[8]
            max_attitude_error_deg = max(max_attitude_error_deg, np.rad2deg(abs(pitch_error)))
            if t_s > 40.0:
                steady_state_attitude_error_deg = max(steady_state_attitude_error_deg, np.rad2deg(abs(pitch_error)))

            gimbal_pitch = pitch_pid.update(pitch_error, config.dt_s)
            gimbal_yaw = yaw_pid.update(yaw_error, config.dt_s)

            runtime = StageRuntime(
                stage=config.stages[stage_idx],
                stage_index=stage_idx,
                stage_elapsed_s=stage_elapsed_s,
                stage_propellant_kg=stage_remaining_prop,
                gimbal_pitch_rad=gimbal_pitch,
                gimbal_yaw_rad=gimbal_yaw,
                target_pitch_rad=target_pitch,
                target_yaw_rad=0.0,
            )
        else:
            pitch_pid.reset()
            yaw_pid.reset()

        next_state = rk4_step(t_s, state, config.dt_s, runtime, config, profile_t, profile_throttle)
        gimbal_pitch_hist[i] = np.rad2deg(gimbal_pitch)
        gimbal_yaw_hist[i] = np.rad2deg(gimbal_yaw)

        if burning:
            stage = config.stages[stage_idx]
            throttle = get_throttle(stage_elapsed_s, stage.burn_time_s, profile_t, profile_throttle)
            thrust = throttle * stage.max_thrust_n
            mdot = thrust / (stage.isp_s * config.g0_m_s2)
            burned = mdot * config.dt_s
            stage_remaining_prop = max(stage_remaining_prop - burned, 0.0)
            stage_elapsed_s += config.dt_s

            if stage_remaining_prop <= 0.0 or stage_elapsed_s >= stage.burn_time_s:
                if "meco" not in event_times_s:
                    event_times_s["meco"] = t_s
                phase = FlightPhase.STAGING
                in_staging = True
                staging_elapsed_s = 0.0
                pending_stage_drop_dry_mass_kg = stage.dry_mass_kg
        elif in_staging:
            staging_elapsed_s += config.dt_s
            if staging_elapsed_s >= config.staging_delay_s:
                next_state[12] -= pending_stage_drop_dry_mass_kg
                stage_idx += 1
                in_staging = False
                if stage_idx < len(config.stages):
                    stage_remaining_prop = config.stages[stage_idx].propellant_mass_kg
                    stage_elapsed_s = 0.0
                    phase = FlightPhase.ASCENT
                    event_times_s.setdefault("staging", t_s)
                else:
                    phase = FlightPhase.COAST

        if phase == FlightPhase.IGNITION and t_s >= 2.0:
            phase = FlightPhase.ASCENT
        if phase in (FlightPhase.ASCENT, FlightPhase.COAST) and prev_vertical_speed > 0.0 and vertical_speed <= 0.0:
            phase = FlightPhase.APOGEE
            event_times_s.setdefault("apogee", t_s)
        elif phase == FlightPhase.APOGEE:
            phase = FlightPhase.REENTRY
            event_times_s.setdefault("reentry", t_s)
        elif phase == FlightPhase.REENTRY and alt <= 50.0:
            phase = FlightPhase.LANDING
            event_times_s.setdefault("landing", t_s)

        next_state[12] = max(next_state[12], config.payload_mass_kg)
        state = next_state
        t_s += config.dt_s
        prev_altitude = alt
        prev_vertical_speed = vertical_speed

        if phase == FlightPhase.LANDING and prev_altitude < 100.0:
            time_hist = time_hist[: i + 1]
            state_hist = state_hist[: i + 1]
            alt_hist = alt_hist[: i + 1]
            speed_hist = speed_hist[: i + 1]
            q_hist = q_hist[: i + 1]
            stage_hist = stage_hist[: i + 1]
            phase_hist = phase_hist[: i + 1]
            gimbal_pitch_hist = gimbal_pitch_hist[: i + 1]
            gimbal_yaw_hist = gimbal_yaw_hist[: i + 1]
            break

    max_q_idx = int(np.argmax(q_hist))
    apogee_idx = int(np.argmax(alt_hist))
    under_80_mask = (alt_hist <= 80_000.0) & (time_hist <= time_hist[apogee_idx])
    if np.any(under_80_mask):
        under80_idx = int(np.argmax(np.where(under_80_mask, q_hist, -1.0)))
    else:
        under80_idx = max_q_idx
    event_times_s.setdefault("max_q", float(time_hist[under80_idx]))

    return SimResult(
        time_s=time_hist,
        states=state_hist,
        altitude_m=alt_hist,
        speed_m_s=speed_hist,
        dynamic_pressure_pa=q_hist,
        stage_index=stage_hist,
        flight_phase=phase_hist,
        gimbal_pitch_deg=gimbal_pitch_hist,
        gimbal_yaw_deg=gimbal_yaw_hist,
        max_q_pa=float(q_hist[max_q_idx]),
        max_q_time_s=float(time_hist[max_q_idx]),
        max_q_under_80km_pa=float(q_hist[under80_idx]),
        max_q_under_80km_time_s=float(time_hist[under80_idx]),
        apogee_m=float(alt_hist[apogee_idx]),
        apogee_time_s=float(time_hist[apogee_idx]),
        max_attitude_error_deg=float(max_attitude_error_deg),
        steady_state_attitude_error_deg=float(steady_state_attitude_error_deg),
        event_times_s=event_times_s,
    )
