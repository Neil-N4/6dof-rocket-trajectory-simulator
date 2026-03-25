from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PIDController:
    kp: float
    ki: float
    kd: float
    integral_limit: float = 0.5
    integral: float = 0.0
    prev_error: float = 0.0

    def reset(self) -> None:
        self.integral = 0.0
        self.prev_error = 0.0

    def update(self, error: float, dt_s: float) -> float:
        self.integral += error * dt_s
        self.integral = max(min(self.integral, self.integral_limit), -self.integral_limit)
        derivative = (error - self.prev_error) / max(dt_s, 1e-6)
        self.prev_error = error
        return self.kp * error + self.ki * self.integral + self.kd * derivative
