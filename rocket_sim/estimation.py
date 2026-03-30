from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .simulate import SimResult


@dataclass
class EkfResult:
    estimated_state: np.ndarray  # [N, 6] = position(3), velocity(3)
    rmse_position_m: float
    rmse_velocity_m_s: float
    gps_updates: int


def _rmse(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.sqrt(np.mean((a - b) ** 2)))


def run_ekf_position_velocity(
    sim: SimResult,
    imu_accel_sigma_m_s2: float = 0.25,
    gps_pos_sigma_m: float = 8.0,
    gps_vel_sigma_m_s: float = 0.8,
    gps_period_steps: int = 10,
    seed: int = 7,
) -> EkfResult:
    rng = np.random.default_rng(seed)

    t = sim.time_s
    dt = float(np.mean(np.diff(t))) if len(t) > 1 else 0.1
    truth_pos = sim.states[:, 0:3]
    truth_vel = sim.states[:, 3:6]
    n = truth_pos.shape[0]

    # IMU acceleration proxy from finite differences on truth velocity.
    truth_accel = np.zeros_like(truth_vel)
    if n > 1:
        truth_accel[1:] = (truth_vel[1:] - truth_vel[:-1]) / dt
        truth_accel[0] = truth_accel[1]
    imu_accel = truth_accel + rng.normal(0.0, imu_accel_sigma_m_s2, size=truth_accel.shape)

    x = np.zeros((n, 6))
    x[0, 0:3] = truth_pos[0]
    x[0, 3:6] = truth_vel[0]

    # Initial covariance.
    P = np.eye(6)
    P[0:3, 0:3] *= 50.0
    P[3:6, 3:6] *= 8.0

    # Process model x_k+1 = F x_k + B a_k
    F = np.eye(6)
    F[0:3, 3:6] = dt * np.eye(3)
    B = np.zeros((6, 3))
    B[0:3, :] = 0.5 * dt * dt * np.eye(3)
    B[3:6, :] = dt * np.eye(3)

    q_pos = (0.5 * dt * dt * imu_accel_sigma_m_s2) ** 2
    q_vel = (dt * imu_accel_sigma_m_s2) ** 2
    Q = np.diag([q_pos, q_pos, q_pos, q_vel, q_vel, q_vel])

    H = np.eye(6)
    R = np.diag(
        [
            gps_pos_sigma_m**2,
            gps_pos_sigma_m**2,
            gps_pos_sigma_m**2,
            gps_vel_sigma_m_s**2,
            gps_vel_sigma_m_s**2,
            gps_vel_sigma_m_s**2,
        ]
    )

    updates = 0
    I = np.eye(6)

    for k in range(1, n):
        # Predict
        x_pred = F @ x[k - 1] + B @ imu_accel[k]
        P = F @ P @ F.T + Q

        # GPS update at stride.
        if k % gps_period_steps == 0:
            z = np.concatenate([truth_pos[k], truth_vel[k]]) + rng.normal(
                0.0,
                np.array(
                    [
                        gps_pos_sigma_m,
                        gps_pos_sigma_m,
                        gps_pos_sigma_m,
                        gps_vel_sigma_m_s,
                        gps_vel_sigma_m_s,
                        gps_vel_sigma_m_s,
                    ]
                ),
            )
            y = z - (H @ x_pred)
            S = H @ P @ H.T + R
            K = P @ H.T @ np.linalg.inv(S)
            x[k] = x_pred + K @ y
            P = (I - K @ H) @ P
            updates += 1
        else:
            x[k] = x_pred

    rmse_pos = _rmse(x[:, 0:3], truth_pos)
    rmse_vel = _rmse(x[:, 3:6], truth_vel)
    return EkfResult(x, rmse_pos, rmse_vel, updates)

