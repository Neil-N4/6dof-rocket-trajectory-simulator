# Debugging Case Study: Python/C++ Event-Time Drift

## Symptom

During Python/C++ parity checks, event times diverged more than expected:

- `MECO` and `staging` in C++ appeared earlier than Python.
- Apogee values were still directionally similar, so the issue was subtle and easy to miss without event-level checks.

## Investigation

Instrumentation added:

- Per-run summary outputs from C++ (`cpp_sim --summary ...`) including event times.
- Parity harness (`scripts/parity_check.py`) comparing:
  - apogee
  - Max-Q (<=80 km ascent)
  - MECO/staging timestamps

Findings:

- Stage mass depletion and stage-transition timing were handled in the same integration step, creating slight timing skew between implementations.
- The skew was amplified by integration timestep and event-trigger ordering.

## Root Cause

Cross-implementation differences in when phase/event transitions were committed relative to state update boundaries.

## Fix

- Added explicit phase and event fields in C++ result model.
- Standardized event trigger ordering and summary export in C++ (`sim_main.cpp`).
- Added CI parity gate so future drift fails fast.

## Verification

- `make parity` now passes with configured tolerances.
- C++ validation and C++ tests pass.
- CI includes parity gate on every push/PR.

## Lessons

- Numeric parity is not enough; event-level parity is required for flight-logic confidence.
- Small step-ordering differences can produce meaningful timeline drift in staged systems.
