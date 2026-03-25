from __future__ import annotations

import math
import subprocess
from pathlib import Path

from rocket_sim.config import load_config
from rocket_sim.simulate import run_simulation


FAILURE_CONFIGS = {
    "engine_cutoff": "configs/engine_cutoff.yaml",
    "separation_anomaly": "configs/separation_anomaly.yaml",
    "extreme_drag": "configs/extreme_drag.yaml",
}


def parse_summary(path: Path) -> dict[str, float]:
    out: dict[str, float] = {}
    for line in path.read_text().splitlines():
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = float(v.strip())
    return out


def main() -> None:
    root = Path(__file__).resolve().parents[1]

    nominal_cfg = load_config(Path("configs/nominal.yaml"), root)
    nominal_res = run_simulation(nominal_cfg)
    nominal_apogee = nominal_res.apogee_m

    failures = []

    for name, cfg_rel in FAILURE_CONFIGS.items():
        cfg = load_config(Path(cfg_rel), root)
        py_res = run_simulation(cfg)

        summary_path = root / "outputs" / f"cpp_summary_{name}.txt"
        csv_path = root / "outputs" / f"cpp_flight_states_{name}.csv"
        subprocess.run(
            [
                str((root / "cpp_sim").resolve()),
                "--config",
                str((root / cfg_rel).resolve()),
                "--dt",
                str(cfg.dt_s),
                "--duration",
                str(cfg.sim_duration_s),
                "--out",
                str(csv_path),
                "--summary",
                str(summary_path),
            ],
            check=True,
        )
        cpp = parse_summary(summary_path)

        if name == "engine_cutoff":
            ok = py_res.apogee_m < nominal_apogee * 0.85
            msg = f"Engine cutoff should reduce apogee (<85% nominal): got {py_res.apogee_m/1000:.2f} km"
            (print("PASS:" if ok else "FAIL:", msg))
            if not ok:
                failures.append(msg)
        elif name == "separation_anomaly":
            meco = py_res.event_times_s.get("meco", -1.0)
            staging = py_res.event_times_s.get("staging", -1.0)
            ok = meco >= 0.0 and staging >= 0.0 and (staging - meco) >= 20.0
            msg = f"Separation anomaly should delay staging by >=20s: got {staging-meco:.2f}s"
            (print("PASS:" if ok else "FAIL:", msg))
            if not ok:
                failures.append(msg)
        elif name == "extreme_drag":
            ok = py_res.apogee_m < nominal_res.apogee_m
            msg = (
                f"Extreme drag should reduce apogee: got {py_res.apogee_m/1000:.2f} "
                f"vs nominal {nominal_res.apogee_m/1000:.2f} km"
            )
            (print("PASS:" if ok else "FAIL:", msg))
            if not ok:
                failures.append(msg)

        # C++ sanity for each failure scenario.
        cpp_apogee = cpp.get("apogee_m", 0.0)
        cpp_ok = math.isfinite(cpp_apogee) and cpp_apogee >= 0.0
        cpp_msg = f"C++ run sanity for {name}: apogee={cpp_apogee/1000:.2f} km"
        (print("PASS:" if cpp_ok else "FAIL:", cpp_msg))
        if not cpp_ok:
            failures.append(cpp_msg)

    if failures:
        print("\nFailure-mode suite failed:")
        for f in failures:
            print(f" - {f}")
        raise SystemExit(1)

    print("\nFailure-mode suite passed.")


if __name__ == "__main__":
    main()
