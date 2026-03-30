from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path


def _run(cmd: list[str], cwd: Path) -> str:
    out = subprocess.check_output(cmd, cwd=cwd, text=True)
    return out


def _parse_metric(text: str, key: str) -> float:
    m = re.search(rf"{re.escape(key)}=([0-9eE+.-]+)", text)
    if not m:
        raise ValueError(f"Missing {key} in output")
    return float(m.group(1))


def main() -> None:
    p = argparse.ArgumentParser(description="Benchmark scalar vs SIMD RK4 and run event engine.")
    p.add_argument("--build-dir", type=Path, default=Path("build"))
    p.add_argument("--trajectories", type=int, default=16384)
    p.add_argument("--steps", type=int, default=500)
    args = p.parse_args()

    root = Path(__file__).resolve().parents[1]
    build_dir = (root / args.build_dir).resolve()

    simd_out = _run(
        [
            str(build_dir / "cpp_simd_batch_rk4"),
            "--trajectories",
            str(args.trajectories),
            "--steps",
            str(args.steps),
        ],
        root,
    )
    print(simd_out.strip())

    event_out = _run(
        [
            str(build_dir / "cpp_event_engine"),
            "--duration",
            "800",
            "--summary",
            "outputs/cpp_event_summary.txt",
        ],
        root,
    )
    print(event_out.strip())

    speedup = _parse_metric(simd_out, "speedup")
    print(f"simd_speedup={speedup:.3f}x")


if __name__ == "__main__":
    main()
