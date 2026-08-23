"""Fiction Forks simulation package."""

__version__ = "0.2.0"

from .engine import compare_worlds, load_json, simulate
from .social import run_social_simulation

__all__ = ["compare_worlds", "load_json", "run_social_simulation", "simulate"]
