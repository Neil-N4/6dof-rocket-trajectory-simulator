# Project Journey

## 1. Problem Definition

Build an end-to-end launch vehicle simulator that demonstrates dynamics modeling, controls, software architecture, and validation rigor.

## 2. Initial Implementation

Implemented 6-DOF dynamics, RK4 integration, atmosphere/drag, stage separation, event detection, and plotting pipeline.

## 3. Controls and Flight Logic

Added PID + TVC attitude control and a 7-state flight phase engine:
`IGNITION -> ASCENT -> STAGING -> COAST -> APOGEE -> REENTRY -> LANDING`.

## 4. Validation and Quality Gates

Added analytical and SciPy cross-checks, scenario configs, validation thresholds, and CI gating.

## 5. Uncertainty Quantification

Added Monte Carlo dispersion runner and percentile outputs for apogee/Max-Q/attitude metrics.

## 6. Current Outcome

Project now supports deterministic reruns, automated verification, and evidence-rich outputs suitable for technical review.
