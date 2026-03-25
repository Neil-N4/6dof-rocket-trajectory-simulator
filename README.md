# Multi-Stage Rocket Dynamics Simulator

A multi-stage launch vehicle simulator with 6-DOF rigid-body dynamics, RK4 integration, PID + TVC attitude control, a 7-state flight state machine, and validation against analytical and SciPy baselines.

## Tech Stack

C++, Python, NumPy, SciPy, Matplotlib

## Features

- 6-DOF equations of motion (position, velocity, attitude, body rates, mass)
- RK4 integration for flight state propagation
- US Standard Atmosphere 1976 density model and drag/dynamic pressure computation
- Closed-loop PID attitude controller with TVC gimbal commands
- Multi-stage burnout + separation with configurable staging delay
- 7-state flight state machine:
  - `IGNITION -> ASCENT -> STAGING -> COAST -> APOGEE -> REENTRY -> LANDING`
- Autonomous event detection (`MECO`, `staging`, `apogee`, `reentry`, `landing`)
- Analytical + SciPy baseline validation utilities
- Optional C++ RK4 reference executable (`cpp/rk4_reference.cpp`)

## Equations

Translational dynamics:

- $\dot{\mathbf{r}} = \mathbf{v}$
- $\dot{\mathbf{v}} = \mathbf{g}(\mathbf{r}) + \frac{\mathbf{F}_{\text{thrust}} + \mathbf{F}_{\text{drag}}}{m}$
- $\mathbf{g}(\mathbf{r}) = -\mu \frac{\mathbf{r}}{\|\mathbf{r}\|^3}$

Drag model:

- $\mathbf{F}_{\text{drag}} = -\frac{1}{2}\rho V^2 C_d A \hat{\mathbf{v}}$
- $q = \frac{1}{2}\rho V^2$

Mass flow during burn:

- $\dot{m} = -\frac{T}{I_{sp}g_0}$

## Quickstart (Python)

```bash
cd /path/to/6dof-rocket-trajectory-simulator
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
MPLCONFIGDIR=$PWD/.mplconfig PYTHONPATH=. python main.py --dt 0.1 --duration 2200
```

## Optional C++ Baseline Build

```bash
cd /path/to/6dof-rocket-trajectory-simulator
cmake -S . -B build
cmake --build build
./build/rk4_reference
```

## Tests

```bash
cd /path/to/6dof-rocket-trajectory-simulator
source .venv/bin/activate
PYTHONPATH=. pytest -q tests/test_sim.py
```

## Output Artifacts

Generated in `outputs/`:

- `trajectory_3d.png`
- `timeseries.png`
- `flight_states.csv`

## Launch Validation (Latest)

Reference run:

- Command: `python main.py --dt 0.1 --duration 2200`
- Apogee: `3118.50 km` at `t = 1547.9 s`
- Max-Q (ascent, 0-80 km): `36.32 kPa` at `t = 61.7 s`
- Steady-state attitude error (`t > 40 s`): `0.12 deg`
- RK4 trajectory error vs analytical baseline: `0.000%` (SciPy cross-check: `0.000%`)
- Detected events: `MECO`, `staging`, `apogee`, `reentry`

## Resume-Ready Project Entry

**Multi-Stage Rocket Dynamics Simulator | C++, Python, NumPy, SciPy, Matplotlib**

- Implemented 6-DOF equations of motion with RK4 integration; achieved `<0.5%` trajectory error vs analytical baseline.
- Modeled US Standard Atmosphere 1976; computed dynamic pressure and Max-Q across the ascent `0-80 km` altitude range.
- Engineered a closed-loop PID attitude controller with TVC gimbal commands; stabilized vehicle within `0.3 deg` of target.
- Built a 7-state flight state machine (ignition to landing); autonomously detected `MECO`, staging, apogee, and reentry.
