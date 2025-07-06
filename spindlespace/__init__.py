"""
Spindlespace - Procedural generator for Krasnikov rail networks and worlds.

A tool for generating coherent star systems, rail networks, and setting data
for the Spindlespace hard science fiction universe.
"""

__version__ = "0.1.0"
__author__ = "Spindlespace Generator"

from .core.models import System, Planet, Rail, Schedule, Civilization, Galaxy
from .core.validators import validate_rail_network, detect_loops

__all__ = [
    "System",
    "Planet", 
    "Rail",
    "Schedule",
    "Civilization",
    "Galaxy",
    "validate_rail_network",
    "detect_loops",
]