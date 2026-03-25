# Validation Report

## Scenario

- Config: `configs/nominal.yaml`
- Command: `python main.py --config configs/nominal.yaml --seed 42`

## Key Results

- Apogee: `3118.50 km` at `t = 1547.9 s`
- Max-Q (0-80 km ascent): `36.32 kPa` at `t = 61.7 s`
- Steady-state attitude error (t > 40 s): `0.12 deg`
- RK4 error vs analytical baseline: `0.000%`
- RK4 error vs SciPy reference: `0.000%`
- Events detected: `MECO`, `staging`, `apogee`, `reentry`

## Validation Gates

- Analytical error <= 0.5%: PASS
- SciPy cross-check <= 0.5%: PASS
- Steady-state attitude error <= 0.3 deg: PASS
- Max-Q sanity [10, 120] kPa: PASS
- Event ordering constraints: PASS

## Monte Carlo Dispersion

- Command: `python scripts/monte_carlo.py --config configs/nominal.yaml --runs 80 --seed 123 --duration 1200 --dt 0.15`
- Apogee P50/P95: `2851.68 / 3286.77 km`
- Max-Q P50/P95: `36.47 / 39.02 kPa`
- Artifacts:
  - `outputs/monte_carlo/monte_carlo_runs.csv`
  - `outputs/monte_carlo/summary.json`
  - `outputs/monte_carlo/dispersion_histograms.png`

## Notes

- These checks are automated by `scripts/validate.py` and enforced in CI (`.github/workflows/ci.yml`).
