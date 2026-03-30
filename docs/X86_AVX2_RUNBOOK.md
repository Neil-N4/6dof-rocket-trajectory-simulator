# x86_64 AVX2 Runbook

Use this runbook on an x86_64 Linux machine to collect true AVX2 SIMD metrics.

## 1) Build

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j
```

## 2) Run SIMD benchmark

```bash
./build/cpp_simd_batch_rk4 --trajectories 16384 --steps 500
```

Expected output includes:

- `scalar_ms`
- `batch_ms`
- `speedup`
- `simd_mode=avx2`

## 3) Generate all next-gen artifacts

```bash
source .venv/bin/activate
PYTHONPATH=. python scripts/generate_perf_artifacts.py --build-dir build --outdir outputs/nextgen
```

Artifacts:

- `outputs/nextgen/simd_metrics.csv`
- `outputs/nextgen/simd_runtime_comparison.png`
- `docs/PERF_PROFILE_REPORT.md`

