# 6-DOF Rocket Trajectory Simulator

A resume-grade rocket flight simulator with rigid-body 6-DOF dynamics, RK4 integration, staging logic, atmospheric drag, and thrust-curve support.

## Features

- 6-DOF state: position, velocity, Euler attitude, body rates, and mass
- 4th-order Runge-Kutta (RK4) numerical integration
- Gravity model with inverse-square law
- US Standard Atmosphere 1976 density model (piecewise)
- Dynamic pressure and drag force modeling
- Multi-stage vehicle with dry-mass jettison at separation
- Thrust profile loaded from CSV (`time_norm`, `throttle`)
- Output metrics: apogee, Max-Q, stage transitions
- Plot generation: 3D trajectory and key timeseries

## Equations

Translational dynamics:

- $\dot{\mathbf{r}} = \mathbf{v}$
- $\dot{\mathbf{v}} = \mathbf{g}(\mathbf{r}) + \frac{\mathbf{F}_{\text{thrust}} + \mathbf{F}_{\text{drag}}}{m}$
- $\mathbf{g}(\mathbf{r}) = -\mu \frac{\mathbf{r}}{\|\mathbf{r}\|^3}$

Drag model:

- $\mathbf{F}_{drag} = -\frac{1}{2}\rho V^2 C_d A \hat{\mathbf{v}}$
- $q = \frac{1}{2}\rho V^2$ (dynamic pressure)

Rigid-body rotational dynamics:

- $\dot{\boldsymbol{\omega}} = \mathbf{I}^{-1}\left(\boldsymbol{\tau} - \boldsymbol{\omega} \times (\mathbf{I}\boldsymbol{\omega})\right)$
- $\dot{\boldsymbol{\Theta}} = \mathbf{T}(\phi,\theta)\,\boldsymbol{\omega}$

Mass flow:

- $\dot{m} = -\frac{T}{I_{sp}g_0}$ while propellant remains.

## Quickstart

```bash
cd /Users/neilnair/Documents/Playground/spacex_6dof_sim
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py --dt 0.1 --duration 520
```

## Test

```bash
cd /Users/neilnair/Documents/Playground/spacex_6dof_sim
source .venv/bin/activate
PYTHONPATH=. pytest -q
```

## Output

Generated in `outputs/`:

- `trajectory_3d.png`
- `timeseries.png`
- `flight_states.csv`

The CLI also prints:

- Apogee (km and time)
- Max-Q (kPa and time)

## Launch Validation

Reference run (latest):

- Command: `python main.py --dt 0.1 --duration 520`
- Apogee: `1061.77 km` at `t = 520.0 s`
- Max-Q: `44.01 kPa` at `t = 64.2 s`

Use these values as baseline checks after changes to dynamics, thrust curves, or vehicle parameters.

## Resume Bullet Template

- Built a **6-DOF rocket trajectory simulator** in Python with RK4 integration, US Standard Atmosphere drag, multi-stage separation, and thrust-curve inputs; generated 3D flight trajectories and Max-Q/apogee metrics for validation workflows.
