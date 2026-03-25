from __future__ import annotations

import numpy as np
from scipy.integrate import solve_ivp


def analytical_vertical_burn_altitude_m(
    t_s: float,
    m0_kg: float,
    mdot_kg_s: float,
    exhaust_velocity_m_s: float,
    g_m_s2: float,
) -> float:
    if t_s <= 0.0:
        return 0.0
    m = m0_kg - mdot_kg_s * t_s
    if m <= 0.0:
        raise ValueError("Mass became non-physical during analytical baseline calculation.")
    term = m * np.log(m / m0_kg) + mdot_kg_s * t_s
    return float(exhaust_velocity_m_s / mdot_kg_s * term - 0.5 * g_m_s2 * t_s * t_s)


def rk4_vertical_burn_altitude_m(
    burn_time_s: float,
    dt_s: float,
    m0_kg: float,
    mdot_kg_s: float,
    thrust_n: float,
    g_m_s2: float,
) -> float:
    state = np.array([0.0, 0.0], dtype=float)  # h, v

    def f(t_s: float, y: np.ndarray) -> np.ndarray:
        h, v = y
        del h
        m = max(m0_kg - mdot_kg_s * t_s, 1.0)
        a = thrust_n / m - g_m_s2
        return np.array([v, a], dtype=float)

    t_s = 0.0
    n = int(burn_time_s / dt_s)
    for _ in range(n):
        k1 = f(t_s, state)
        k2 = f(t_s + 0.5 * dt_s, state + 0.5 * dt_s * k1)
        k3 = f(t_s + 0.5 * dt_s, state + 0.5 * dt_s * k2)
        k4 = f(t_s + dt_s, state + dt_s * k3)
        state = state + dt_s / 6.0 * (k1 + 2 * k2 + 2 * k3 + k4)
        t_s += dt_s
    return float(state[0])


def scipy_vertical_burn_altitude_m(
    burn_time_s: float,
    m0_kg: float,
    mdot_kg_s: float,
    thrust_n: float,
    g_m_s2: float,
) -> float:
    def f(t_s: float, y: np.ndarray) -> np.ndarray:
        h, v = y
        del h
        m = max(m0_kg - mdot_kg_s * t_s, 1.0)
        return np.array([v, thrust_n / m - g_m_s2], dtype=float)

    sol = solve_ivp(f, (0.0, burn_time_s), y0=np.array([0.0, 0.0], dtype=float), rtol=1e-10, atol=1e-12)
    return float(sol.y[0, -1])


def baseline_trajectory_error_percent() -> tuple[float, float]:
    m0_kg = 150_000.0
    thrust_n = 2_000_000.0
    isp_s = 300.0
    g = 9.80665
    burn_time_s = 35.0
    dt_s = 0.02
    mdot_kg_s = thrust_n / (isp_s * g)
    ve = isp_s * g

    analytical = analytical_vertical_burn_altitude_m(burn_time_s, m0_kg, mdot_kg_s, ve, g)
    rk4_alt = rk4_vertical_burn_altitude_m(burn_time_s, dt_s, m0_kg, mdot_kg_s, thrust_n, g)
    scipy_alt = scipy_vertical_burn_altitude_m(burn_time_s, m0_kg, mdot_kg_s, thrust_n, g)

    analytical_error_pct = abs(rk4_alt - analytical) / max(abs(analytical), 1.0) * 100.0
    scipy_error_pct = abs(rk4_alt - scipy_alt) / max(abs(scipy_alt), 1.0) * 100.0
    return float(analytical_error_pct), float(scipy_error_pct)
