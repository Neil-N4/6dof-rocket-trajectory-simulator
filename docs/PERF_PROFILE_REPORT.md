# Perf Profile Report

## Summary
- Event engine best throughput: `1,520,100 events/s` at `1200s` scenario duration
- Event engine mean/max latency: `0.0139 / 100.0000 ms`
- RK4 batch speedup: `1.001x` (`scalar_fallback` mode)

## Notes
- On Apple Silicon, SIMD mode may fall back to scalar due to AVX2 unavailability.
- Run the same benchmark on x86_64 Linux to collect AVX2 numbers for resume/interview claims.

## Artifacts
- `outputs/nextgen/event_engine_metrics.csv`
- `outputs/nextgen/event_engine_throughput_latency.png`
- `outputs/nextgen/simd_metrics.csv`
- `outputs/nextgen/simd_runtime_comparison.png`
- `outputs/nextgen/ekf_noise_sweep.csv`
- `outputs/nextgen/ekf_rmse_vs_noise.png`
