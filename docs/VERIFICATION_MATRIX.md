# Verification Matrix

| Requirement | Method | Artifact | Status |
|---|---|---|---|
| R1 / V1 | Analytical baseline check | `scripts/validate.py` | Automated |
| R1 / V2 | SciPy cross-check | `scripts/validate.py`, `rocket_sim/validation.py` | Automated |
| R2 | Stage transition regression | `tests/test_sim.py::test_staging_changes_stage_index` | Automated |
| R3 / V4 | Max-Q sanity gate | `scripts/validate.py` | Automated |
| R4 / V3 | Controller tracking gate | `scripts/validate.py` | Automated |
| R5 / V5 | Event ordering gate | `scripts/validate.py` | Automated |
| R6 | Artifact generation check | `main.py`, `rocket_sim/plotting.py` | Manual/Automated |
