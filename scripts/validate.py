from __future__ import annotations

import argparse
import sys
from pathlib import Path

from rocket_sim.config import load_config
from rocket_sim.simulate import run_simulation
from rocket_sim.validation import baseline_trajectory_error_percent


THRESHOLDS = {
    "analytical_error_pct": 0.5,
    "steady_attitude_error_deg": 0.3,
    "max_q_kpa_min": 10.0,
    "max_q_kpa_max": 120.0,
    "apogee_km_min": 500.0,
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Validation gate")
    p.add_argument("--config", type=Path, default=Path("configs/nominal.yaml"))
    p.add_argument("--fail-fast", action="store_true")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    project_root = Path(__file__).resolve().parents[1]
    cfg = load_config(args.config, project_root)
    res = run_simulation(cfg)
    analytical_error, scipy_error = baseline_trajectory_error_percent()

    failures: list[str] = []

    def check(condition: bool, msg: str) -> None:
        if condition:
            print(f"PASS: {msg}")
        else:
            failures.append(msg)
            print(f"FAIL: {msg}")
            if args.fail_fast:
                print("Validation failed (fail-fast).")
                sys.exit(1)

    check(analytical_error <= THRESHOLDS["analytical_error_pct"], f"Analytical error <= {THRESHOLDS['analytical_error_pct']}% (got {analytical_error:.4f}%)")
    check(scipy_error <= THRESHOLDS["analytical_error_pct"], f"SciPy cross-check error <= {THRESHOLDS['analytical_error_pct']}% (got {scipy_error:.4f}%)")
    check(res.steady_state_attitude_error_deg <= THRESHOLDS["steady_attitude_error_deg"], f"Steady-state attitude error <= {THRESHOLDS['steady_attitude_error_deg']} deg (got {res.steady_state_attitude_error_deg:.3f})")

    max_q_kpa = res.max_q_under_80km_pa / 1000.0
    check(max_q_kpa >= THRESHOLDS["max_q_kpa_min"], f"Max-Q ascent >= {THRESHOLDS['max_q_kpa_min']} kPa (got {max_q_kpa:.2f})")
    check(max_q_kpa <= THRESHOLDS["max_q_kpa_max"], f"Max-Q ascent <= {THRESHOLDS['max_q_kpa_max']} kPa (got {max_q_kpa:.2f})")

    apogee_km = res.apogee_m / 1000.0
    check(apogee_km >= THRESHOLDS["apogee_km_min"], f"Apogee >= {THRESHOLDS['apogee_km_min']} km (got {apogee_km:.2f})")

    events = res.event_times_s
    check("meco" in events and "staging" in events, "Events include MECO and staging")
    if "meco" in events and "staging" in events:
        check(events["meco"] < events["staging"], f"Event ordering meco < staging ({events['meco']:.1f}s < {events['staging']:.1f}s)")
    if "apogee" in events and "reentry" in events:
        check(events["apogee"] <= events["reentry"], f"Event ordering apogee <= reentry ({events['apogee']:.1f}s <= {events['reentry']:.1f}s)")

    if failures:
        print("\nValidation failed:")
        for f in failures:
            print(f" - {f}")
        sys.exit(1)

    print("\nValidation passed.")


if __name__ == "__main__":
    main()
