# Simulator Requirements

## Functional Requirements

- R1: System shall propagate a 6-DOF launch vehicle state with RK4 integration.
- R2: System shall model multi-stage propulsion, burnout, and stage separation.
- R3: System shall model aerodynamic drag using atmosphere density and velocity-dependent dynamic pressure.
- R4: System shall run a closed-loop PID + TVC attitude controller.
- R5: System shall detect and timestamp flight events: MECO, staging, apogee, reentry, landing.
- R6: System shall export run artifacts (CSV state history and plots).

## Verification Requirements

- V1: RK4 trajectory error vs analytical baseline shall be <= 0.5%.
- V2: RK4 trajectory error vs SciPy ODE reference shall be <= 0.5%.
- V3: Steady-state attitude error (t > 40 s) shall be <= 0.3 deg in nominal scenario.
- V4: Max-Q (0-80 km ascent) shall remain within engineering sanity range [10, 120] kPa for nominal scenario.
- V5: Event ordering shall satisfy MECO < staging and apogee <= reentry when both exist.
