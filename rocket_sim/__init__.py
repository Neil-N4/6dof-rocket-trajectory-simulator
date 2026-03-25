"""6-DOF rocket trajectory simulator."""

from .models import FlightPhase, RocketConfig, Stage
from .simulate import run_simulation

__all__ = ["RocketConfig", "Stage", "FlightPhase", "run_simulation"]
