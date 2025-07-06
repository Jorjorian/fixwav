"""
Core data models for Spindlespace universe.

Defines immutable dataclasses for systems, planets, rails, schedules, and civilizations.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple
from uuid import UUID, uuid4


class StarType(str, Enum):
    """Stellar classification."""
    O = "O"
    B = "B"
    A = "A"
    F = "F"
    G = "G"
    K = "K"
    M = "M"
    WD = "WD"  # White Dwarf
    NS = "NS"  # Neutron Star
    BH = "BH"  # Black Hole


class PlanetClass(str, Enum):
    """Planet classification."""
    TERRESTRIAL = "terrestrial"
    OCEAN = "ocean"
    DESERT = "desert"
    ICE = "ice"
    GAS_GIANT = "gas_giant"
    ICE_GIANT = "ice_giant"
    ASTEROID = "asteroid"
    MOON = "moon"


class RailClass(str, Enum):
    """Krasnikov rail classification."""
    RFC_A = "RFC-A"  # 1M t/yr (core-core)
    RFC_B = "RFC-B"  # 50k t/mo (regional)
    RFC_C = "RFC-C"  # 5k t/day (frontier)
    RFC_D = "RFC-D"  # 500 t/day (frontier)


class CivilizationTier(int, Enum):
    """Technology and development level."""
    PRIMITIVE = 0
    INDUSTRIAL = 1
    NUCLEAR = 2
    FUSION = 3
    ANTIMATTER = 4
    RAIL_AGE = 5
    SINGULARITY = 6
    TRANSCENDENT = 7


@dataclass(frozen=True)
class Coordinate:
    """3D coordinate in light-years."""
    x: float
    y: float
    z: float = 0.0
    
    def distance_to(self, other: Coordinate) -> float:
        """Calculate distance to another coordinate."""
        return math.sqrt(
            (self.x - other.x) ** 2 + 
            (self.y - other.y) ** 2 + 
            (self.z - other.z) ** 2
        )
    
    def __add__(self, other: Coordinate) -> Coordinate:
        return Coordinate(self.x + other.x, self.y + other.y, self.z + other.z)
    
    def __sub__(self, other: Coordinate) -> Coordinate:
        return Coordinate(self.x - other.x, self.y - other.y, self.z - other.z)


@dataclass(frozen=True)
class Planet:
    """Planet or major celestial body."""
    id: str
    name: str
    planet_class: PlanetClass
    orbital_radius: float  # AU
    mass: float = 1.0  # Earth masses
    radius: float = 1.0  # Earth radii
    habitability: float = 0.0  # 0-1 scale
    population: int = 0
    atmosphere: str = "none"
    surface_gravity: float = 1.0  # Earth gravities
    day_length: float = 24.0  # hours
    year_length: float = 365.25  # days
    moons: List[str] = field(default_factory=list)
    resources: Dict[str, float] = field(default_factory=dict)
    
    @property
    def has_life(self) -> bool:
        """Check if planet has significant life."""
        return self.population > 0 or self.habitability > 0.3


@dataclass(frozen=True)
class System:
    """Star system with planets and infrastructure."""
    id: str
    name: str
    coord: Coordinate
    star_type: StarType
    star_mass: float = 1.0  # Solar masses
    star_age: float = 5.0  # Billion years
    planets: List[Planet] = field(default_factory=list)
    population: int = 0
    tech_level: CivilizationTier = CivilizationTier.PRIMITIVE
    faction_control: str = "independent"
    gravitium_deposits: float = 0.0  # Metric tons
    trade_codes: List[str] = field(default_factory=list)
    rails_out: List[Rail] = field(default_factory=list)
    
    @property
    def total_population(self) -> int:
        """Total population across all planets."""
        return self.population + sum(p.population for p in self.planets)
    
    @property
    def habitable_worlds(self) -> List[Planet]:
        """List of habitable planets."""
        return [p for p in self.planets if p.has_life]
    
    @property
    def is_junction(self) -> bool:
        """Check if system is a rail junction."""
        return len(self.rails_out) >= 3


@dataclass(frozen=True)
class Rail:
    """Krasnikov rail connection between systems."""
    id: str
    from_system: str
    to_system: str
    rail_class: RailClass
    length: float  # Light-years
    construction_date: datetime
    interval_days: int  # Days between firings
    next_fire: datetime
    gravitium_cost: float  # Metric tons
    max_capacity: float  # Metric tons per firing
    
    @property
    def capacity_per_year(self) -> float:
        """Annual capacity in metric tons."""
        return self.max_capacity * (365.25 / self.interval_days)
    
    def next_departures(self, from_time: datetime, count: int = 10) -> List[datetime]:
        """Get next N departure times."""
        departures = []
        current = self.next_fire
        while from_time > current:
            current += timedelta(days=self.interval_days)
        
        for _ in range(count):
            departures.append(current)
            current += timedelta(days=self.interval_days)
        
        return departures


@dataclass(frozen=True)
class Schedule:
    """Travel schedule for a rail."""
    rail_id: str
    departures: List[datetime]
    transit_time: timedelta = timedelta(hours=1)  # Assuming near-instantaneous
    
    def get_next_departure(self, after: datetime) -> Optional[datetime]:
        """Get next departure after given time."""
        for departure in self.departures:
            if departure > after:
                return departure
        return None


@dataclass(frozen=True)
class Civilization:
    """Civilization or faction."""
    id: str
    name: str
    species: str
    government_type: str
    tech_level: CivilizationTier
    population: int
    home_system: str
    controlled_systems: List[str] = field(default_factory=list)
    relations: Dict[str, int] = field(default_factory=dict)  # -100 to 100
    traits: List[str] = field(default_factory=list)
    
    @property
    def is_major_power(self) -> bool:
        """Check if this is a major galactic power."""
        return len(self.controlled_systems) >= 10 or self.population >= 10_000_000_000


@dataclass(frozen=True)
class Galaxy:
    """Complete galaxy state."""
    id: str
    name: str
    seed: int
    generation_time: datetime
    systems: Dict[str, System] = field(default_factory=dict)
    rails: Dict[str, Rail] = field(default_factory=dict)
    civilizations: Dict[str, Civilization] = field(default_factory=dict)
    source_vein_systems: List[str] = field(default_factory=list)
    
    @property
    def total_population(self) -> int:
        """Total galactic population."""
        return sum(system.total_population for system in self.systems.values())
    
    @property
    def rail_network_size(self) -> int:
        """Number of rail connections."""
        return len(self.rails)
    
    @property
    def connected_systems(self) -> List[str]:
        """Systems connected to the rail network."""
        connected = set()
        for rail in self.rails.values():
            connected.add(rail.from_system)
            connected.add(rail.to_system)
        return list(connected)
    
    def get_system_rails(self, system_id: str) -> List[Rail]:
        """Get all rails connected to a system."""
        return [rail for rail in self.rails.values() 
                if rail.from_system == system_id or rail.to_system == system_id]
    
    def get_route(self, from_system: str, to_system: str) -> Optional[List[str]]:
        """Find shortest route between systems using rails."""
        # Simple BFS pathfinding
        from collections import deque
        
        if from_system == to_system:
            return [from_system]
        
        queue = deque([(from_system, [from_system])])
        visited = {from_system}
        
        while queue:
            current, path = queue.popleft()
            
            # Find all rails from current system
            for rail in self.rails.values():
                if rail.from_system == current:
                    next_system = rail.to_system
                    if next_system == to_system:
                        return path + [next_system]
                    
                    if next_system not in visited:
                        visited.add(next_system)
                        queue.append((next_system, path + [next_system]))
        
        return None  # No route found


# Utility functions for working with models

def generate_system_id() -> str:
    """Generate a unique system ID."""
    return f"SYS-{uuid4().hex[:8].upper()}"


def generate_rail_id() -> str:
    """Generate a unique rail ID."""
    return f"RAIL-{uuid4().hex[:8].upper()}"


def generate_planet_id(system_id: str, planet_index: int) -> str:
    """Generate a planet ID."""
    letters = "abcdefghijklmnopqrstuvwxyz"
    return f"{system_id}-{letters[planet_index % len(letters)]}"


def calculate_gravitium_cost(distance: float, rail_class: RailClass) -> float:
    """Calculate gravitium cost for a rail."""
    base_cost = {
        RailClass.RFC_A: 1000.0,
        RailClass.RFC_B: 500.0,
        RailClass.RFC_C: 100.0,
        RailClass.RFC_D: 50.0,
    }
    
    # Cost scales with distance squared
    return base_cost[rail_class] * (distance ** 2)


def rail_class_from_capacity(capacity_per_year: float) -> RailClass:
    """Determine rail class from annual capacity."""
    if capacity_per_year >= 1_000_000:  # 1M t/yr
        return RailClass.RFC_A
    elif capacity_per_year >= 600_000:  # 50k t/mo
        return RailClass.RFC_B
    elif capacity_per_year >= 1_800:  # 5k t/day
        return RailClass.RFC_C
    else:
        return RailClass.RFC_D