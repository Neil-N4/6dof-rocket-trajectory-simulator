"""6-DOF rocket trajectory simulator."""

from .models import RocketConfig, Stage
from .simulate import run_simulation

__all__ = ["RocketConfig", "Stage", "run_simulation"]
