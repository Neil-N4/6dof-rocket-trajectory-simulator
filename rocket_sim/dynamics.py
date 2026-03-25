from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .atmosphere import air_density_kg_m3
from .models import RocketConfig, SimState, Stage


@dataclass(frozen=True)
class StageRuntime:
    stage: Stage
    stage_index: int
    stage_elapsed_s: float
    stage_propellant_kg: float
    gimbal_pitch_rad: float = 0.0
    gimbal_yaw_rad: float = 0.0
    target_pitch_rad: float = 0.0
    target_yaw_rad: float = 0.0


def rotation_matrix_from_euler(roll: float, pitch: float, yaw: float) -> np.ndarray:
    cr, sr = math.cos(roll), math.sin(roll)
    cp, sp = math.cos(pitch), math.sin(pitch)
    cy, sy = math.cos(yaw), math.sin(yaw)

    rx = np.array([[1.0, 0.0, 0.0], [0.0, cr, -sr], [0.0, sr, cr]])
    ry = np.array([[cp, 0.0, sp], [0.0, 1.0, 0.0], [-sp, 0.0, cp]])
    rz = np.array([[cy, -sy, 0.0], [sy, cy, 0.0], [0.0, 0.0, 1.0]])
    return rz @ ry @ rx


def euler_rates_matrix(roll: float, pitch: float) -> np.ndarray:
    cphi, sphi = math.cos(roll), math.sin(roll)
    ttheta = math.tan(pitch)
    ctheta = math.cos(pitch)
    ctheta = ctheta if abs(ctheta) > 1e-5 else 1e-5

    return np.array(
        [
            [1.0, sphi * ttheta, cphi * ttheta],
            [0.0, cphi, -sphi],
            [0.0, sphi / ctheta, cphi / ctheta],
        ]
    )


def gravity_accel(position_m: np.ndarray, mu_m3_s2: float) -> np.ndarray:
    r = np.linalg.norm(position_m)
    if r < 1.0:
        return np.array([0.0, 0.0, -9.80665])
    return -mu_m3_s2 * position_m / (r**3)


def get_throttle(stage_elapsed_s: float, burn_time_s: float, profile_t: np.ndarray, profile_throttle: np.ndarray) -> float:
    if burn_time_s <= 0.0:
        return 0.0
    if len(profile_t) == 0:
        return 1.0

    scaled_t = stage_elapsed_s / burn_time_s
    return float(np.clip(np.interp(scaled_t, profile_t, profile_throttle), 0.0, 1.05))


def derivatives(
    t_s: float,
    y: np.ndarray,
    runtime: StageRuntime | None,
    config: RocketConfig,
    profile_t: np.ndarray,
    profile_throttle: np.ndarray,
) -> np.ndarray:
    del t_s
    state = SimState.from_vector(y)

    pos = state.position_m
    vel = state.velocity_m_s
    eul = state.euler_rad
    body_rates = state.body_rates_rad_s
    mass = max(state.mass_kg, 1.0)

    radius = np.linalg.norm(pos)
    altitude = max(radius - config.earth_radius_m, 0.0)

    rho = air_density_kg_m3(altitude)
    speed = np.linalg.norm(vel)

    thrust_n = 0.0
    mdot = 0.0
    area = 1.0
    cd = 0.5
    inertia = np.eye(3)
    torque_b = np.zeros(3)

    if runtime is not None and runtime.stage_propellant_kg > 0.0 and runtime.stage_elapsed_s < runtime.stage.burn_time_s:
        stage = runtime.stage
        throttle = get_throttle(runtime.stage_elapsed_s, stage.burn_time_s, profile_t, profile_throttle)
        thrust_n = throttle * stage.max_thrust_n
        mdot = thrust_n / (stage.isp_s * config.g0_m_s2)
        area = stage.reference_area_m2
        cd = stage.cd
        inertia = stage.inertia_kg_m2

        gimbal_pitch = float(np.clip(runtime.gimbal_pitch_rad, -math.radians(stage.max_gimbal_deg), math.radians(stage.max_gimbal_deg)))
        gimbal_yaw = float(np.clip(runtime.gimbal_yaw_rad, -math.radians(stage.max_gimbal_deg), math.radians(stage.max_gimbal_deg)))
        pitch_cmd = runtime.target_pitch_rad + gimbal_pitch
        yaw_cmd = runtime.target_yaw_rad + gimbal_yaw

        radial_hat = pos / max(radius, 1.0)
        ref = np.array([0.0, 0.0, 1.0])
        east_hat = np.cross(ref, radial_hat)
        if np.linalg.norm(east_hat) < 1e-6:
            east_hat = np.array([0.0, 1.0, 0.0])
        east_hat = east_hat / np.linalg.norm(east_hat)
        north_hat = np.cross(radial_hat, east_hat)

        thrust_dir_i = (
            math.cos(pitch_cmd) * math.cos(yaw_cmd) * radial_hat
            + math.sin(yaw_cmd) * north_hat
            + math.sin(pitch_cmd) * math.cos(yaw_cmd) * east_hat
        )
        thrust_i = thrust_n * thrust_dir_i

        rot = rotation_matrix_from_euler(eul[0], eul[1], eul[2])
        thrust_b = rot.T @ thrust_i
        arm = abs(stage.lever_arm_m[2]) if len(stage.lever_arm_m) >= 3 else 1.0
        torque_b = np.array([0.0, thrust_n * arm * gimbal_pitch, thrust_n * arm * gimbal_yaw])
    else:
        thrust_i = np.zeros(3)

    drag_i = np.zeros(3)
    if speed > 1e-5:
        drag_mag = 0.5 * rho * speed * speed * cd * area
        drag_i = -drag_mag * vel / speed

    grav_a = gravity_accel(pos, config.earth_mu_m3_s2)
    accel_i = grav_a + (thrust_i + drag_i) / mass

    # Rigid body rotational dynamics (body frame).
    omega = body_rates
    coriolis = np.cross(omega, inertia @ omega)
    omega_dot = np.linalg.solve(inertia, torque_b - coriolis) - 0.35 * omega
    if runtime is not None:
        omega_dot += np.array(
            [
                -2.0 * eul[0] - 1.5 * omega[0],
                18.0 * (runtime.target_pitch_rad - eul[1]) - 5.0 * omega[1],
                18.0 * (runtime.target_yaw_rad - eul[2]) - 5.0 * omega[2],
            ]
        )

    euler_dot = euler_rates_matrix(eul[0], eul[1]) @ omega

    out = np.zeros_like(y)
    out[0:3] = vel
    out[3:6] = accel_i
    out[6:9] = euler_dot
    out[9:12] = omega_dot
    out[12] = -mdot
    return out


def rk4_step(
    t_s: float,
    y: np.ndarray,
    dt_s: float,
    runtime: StageRuntime | None,
    config: RocketConfig,
    profile_t: np.ndarray,
    profile_throttle: np.ndarray,
) -> np.ndarray:
    k1 = derivatives(t_s, y, runtime, config, profile_t, profile_throttle)
    k2 = derivatives(t_s + 0.5 * dt_s, y + 0.5 * dt_s * k1, runtime, config, profile_t, profile_throttle)
    k3 = derivatives(t_s + 0.5 * dt_s, y + 0.5 * dt_s * k2, runtime, config, profile_t, profile_throttle)
    k4 = derivatives(t_s + dt_s, y + dt_s * k3, runtime, config, profile_t, profile_throttle)
    return y + (dt_s / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)
