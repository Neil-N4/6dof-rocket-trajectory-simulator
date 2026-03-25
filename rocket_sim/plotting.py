from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from .simulate import SimResult


def save_plots(result: SimResult, out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []

    x = result.states[:, 0]
    y = result.states[:, 1]
    z = result.states[:, 2]

    traj_path = out_dir / "trajectory_3d.png"
    fig = plt.figure(figsize=(8, 6))
    ax = fig.add_subplot(111, projection="3d")
    ax.plot(x / 1000.0, y / 1000.0, z / 1000.0, linewidth=1.5)
    ax.set_xlabel("X (km)")
    ax.set_ylabel("Y (km)")
    ax.set_zlabel("Z (km)")
    ax.set_title("6-DOF Trajectory")
    fig.tight_layout()
    fig.savefig(traj_path, dpi=180)
    plt.close(fig)
    paths.append(traj_path)

    ts_path = out_dir / "timeseries.png"
    fig, axs = plt.subplots(3, 1, figsize=(9, 9), sharex=True)

    axs[0].plot(result.time_s, result.altitude_m / 1000.0)
    axs[0].set_ylabel("Altitude (km)")
    axs[0].grid(True, alpha=0.3)

    axs[1].plot(result.time_s, result.speed_m_s)
    axs[1].set_ylabel("Speed (m/s)")
    axs[1].grid(True, alpha=0.3)

    axs[2].plot(result.time_s, result.dynamic_pressure_pa / 1000.0)
    axs[2].set_ylabel("q (kPa)")
    axs[2].set_xlabel("Time (s)")
    axs[2].grid(True, alpha=0.3)

    fig.suptitle("Flight Timeseries")
    fig.tight_layout()
    fig.savefig(ts_path, dpi=180)
    plt.close(fig)
    paths.append(ts_path)

    return paths


def save_csv(result: SimResult, out_path: Path) -> None:
    arr = np.column_stack(
        [
            result.time_s,
            result.altitude_m,
            result.speed_m_s,
            result.dynamic_pressure_pa,
            result.stage_index,
            result.flight_phase,
            result.gimbal_pitch_deg,
            result.gimbal_yaw_deg,
            result.states,
        ]
    )
    header = (
        "time_s,altitude_m,speed_m_s,dynamic_pressure_pa,stage_index,flight_phase,gimbal_pitch_deg,gimbal_yaw_deg,"
        "x_m,y_m,z_m,vx_m_s,vy_m_s,vz_m_s,roll_rad,pitch_rad,yaw_rad,p_rad_s,q_rad_s,r_rad_s,mass_kg"
    )
    np.savetxt(out_path, arr, delimiter=",", header=header, comments="")
