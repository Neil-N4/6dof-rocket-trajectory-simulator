from __future__ import annotations

import math


def air_density_kg_m3(altitude_m: float) -> float:
    """US Standard Atmosphere 1976 (piecewise up to ~32 km)."""
    if altitude_m < 0.0:
        altitude_m = 0.0

    if altitude_m <= 11_000.0:
        t = 288.15 - 0.0065 * altitude_m
        p = 101_325.0 * (t / 288.15) ** 5.2558797
    elif altitude_m <= 20_000.0:
        t = 216.65
        p = 22_632.06 * math.exp(-9.80665 * (altitude_m - 11_000.0) / (287.05 * t))
    elif altitude_m <= 32_000.0:
        t = 216.65 + 0.001 * (altitude_m - 20_000.0)
        p = 5_474.889 * (216.65 / t) ** (9.80665 / (287.05 * 0.001))
    else:
        return 0.0

    return p / (287.05 * t)
