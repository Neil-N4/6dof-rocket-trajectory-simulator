from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from rocket_sim.config import load_config
from rocket_sim.simulate import run_simulation


def parse_summary(path: Path) -> dict[str, float]:
    values: dict[str, float] = {}
    for line in path.read_text().splitlines():
        if not line.strip() or "=" not in line:
            continue
        key, raw = line.split("=", 1)
        values[key.strip()] = float(raw.strip())
    return values


def rel_err(a: float, b: float) -> float:
    denom = max(abs(b), 1e-9)
    return abs(a - b) / denom


def main() -> None:
    p = argparse.ArgumentParser(description="Compare Python and C++ simulation metrics")
    p.add_argument("--config", type=Path, default=Path("configs/nominal.yaml"))
    p.add_argument("--cpp-bin", type=Path, default=Path("./cpp_sim"))
    p.add_argument("--cpp-summary", type=Path, default=Path("outputs/cpp_summary.txt"))
    p.add_argument("--cpp-csv", type=Path, default=Path("outputs/cpp_flight_states.csv"))
    p.add_argument("--apogee_rel_tol", type=float, default=0.30)
    p.add_argument("--maxq_rel_tol", type=float, default=0.15)
    p.add_argument("--event_time_tol_s", type=float, default=20.0)
    args = p.parse_args()

    root = Path(__file__).resolve().parents[1]
    cfg = load_config(args.config, root)

    subprocess.run(
        [
            str((root / args.cpp_bin).resolve()),
            "--config",
            str((root / args.config).resolve()),
            "--dt",
            str(cfg.dt_s),
            "--duration",
            str(cfg.sim_duration_s),
            "--out",
            str((root / args.cpp_csv).resolve()),
            "--summary",
            str((root / args.cpp_summary).resolve()),
        ],
        check=True,
    )

    py = run_simulation(cfg)
    cpp = parse_summary((root / args.cpp_summary).resolve())

    checks: list[tuple[bool, str]] = []

    checks.append(
        (
            rel_err(cpp["apogee_m"], py.apogee_m) <= args.apogee_rel_tol,
            f"Apogee relative error <= {args.apogee_rel_tol:.2f} (cpp={cpp['apogee_m']:.2f}, py={py.apogee_m:.2f})",
        )
    )
    checks.append(
        (
            rel_err(cpp["max_q_ascent_80km_pa"], py.max_q_under_80km_pa) <= args.maxq_rel_tol,
            (
                f"Max-Q ascent relative error <= {args.maxq_rel_tol:.2f} "
                f"(cpp={cpp['max_q_ascent_80km_pa']:.2f}, py={py.max_q_under_80km_pa:.2f})"
            ),
        )
    )

    py_meco = py.event_times_s.get("meco")
    py_staging = py.event_times_s.get("staging")
    if py_meco is not None and cpp.get("meco_time_s", -1.0) >= 0.0:
        checks.append(
            (
                abs(cpp["meco_time_s"] - py_meco) <= args.event_time_tol_s,
                f"MECO time delta <= {args.event_time_tol_s:.1f}s (cpp={cpp['meco_time_s']:.2f}, py={py_meco:.2f})",
            )
        )
    if py_staging is not None and cpp.get("staging_time_s", -1.0) >= 0.0:
        checks.append(
            (
                abs(cpp["staging_time_s"] - py_staging) <= args.event_time_tol_s,
                f"Staging time delta <= {args.event_time_tol_s:.1f}s (cpp={cpp['staging_time_s']:.2f}, py={py_staging:.2f})",
            )
        )

    failures = []
    for ok, msg in checks:
        print(("PASS: " if ok else "FAIL: ") + msg)
        if not ok:
            failures.append(msg)

    if failures:
        print("\nParity check failed:")
        for f in failures:
            print(f" - {f}")
        raise SystemExit(1)

    print("\nParity check passed.")


if __name__ == "__main__":
    main()
