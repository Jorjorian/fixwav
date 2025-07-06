"""
Star system and planet generator.

Procedurally generates star systems with realistic distributions of stars,
planets, and civilizations based on the Spindlespace setting.
"""

import random
import math
from datetime import datetime, timedelta
from typing import List, Optional, Tuple, Dict
from dataclasses import replace

from ..core.models import (
    System, Planet, Coordinate, StarType, PlanetClass, 
    CivilizationTier, generate_system_id, generate_planet_id
)


class StarGenerator:
    """Base class for star system generators."""
    
    def __init__(self, seed: Optional[int] = None):
        self.rng = random.Random(seed)
    
    def generate_coordinates(self, count: int, radius: float = 100.0) -> List[Coordinate]:
        """Generate star coordinates using Poisson disk sampling."""
        coordinates = []
        attempts = 0
        max_attempts = count * 100
        min_distance = radius * 0.1  # Minimum distance between stars
        
        while len(coordinates) < count and attempts < max_attempts:
            # Generate random coordinate
            x = self.rng.uniform(-radius, radius)
            y = self.rng.uniform(-radius, radius)
            z = self.rng.uniform(-radius * 0.1, radius * 0.1)  # Flattened galaxy
            
            coord = Coordinate(x, y, z)
            
            # Check minimum distance
            too_close = False
            for existing in coordinates:
                if coord.distance_to(existing) < min_distance:
                    too_close = True
                    break
            
            if not too_close:
                coordinates.append(coord)
            
            attempts += 1
        
        return coordinates
    
    def generate_star_type(self) -> StarType:
        """Generate realistic star type distribution."""
        rand = self.rng.random()
        
        # Based on stellar populations
        if rand < 0.76:
            return StarType.M
        elif rand < 0.88:
            return StarType.K
        elif rand < 0.96:
            return StarType.G
        elif rand < 0.99:
            return StarType.F
        elif rand < 0.995:
            return StarType.A
        elif rand < 0.9995:
            return StarType.B
        else:
            return StarType.O
    
    def generate_star_mass(self, star_type: StarType) -> float:
        """Generate star mass based on type."""
        mass_ranges = {
            StarType.M: (0.08, 0.5),
            StarType.K: (0.5, 0.8),
            StarType.G: (0.8, 1.2),
            StarType.F: (1.2, 1.6),
            StarType.A: (1.6, 2.5),
            StarType.B: (2.5, 16.0),
            StarType.O: (16.0, 90.0),
        }
        
        min_mass, max_mass = mass_ranges.get(star_type, (0.5, 2.0))
        return self.rng.uniform(min_mass, max_mass)
    
    def generate_star_age(self, star_type: StarType) -> float:
        """Generate star age based on type."""
        # Older stars for longer-lived types
        if star_type in [StarType.M, StarType.K]:
            return self.rng.uniform(1.0, 12.0)
        elif star_type == StarType.G:
            return self.rng.uniform(1.0, 10.0)
        elif star_type == StarType.F:
            return self.rng.uniform(0.5, 4.0)
        elif star_type == StarType.A:
            return self.rng.uniform(0.1, 1.0)
        else:  # B, O
            return self.rng.uniform(0.01, 0.5)
    
    def generate_planet_count(self, star_type: StarType) -> int:
        """Generate number of planets based on star type."""
        if star_type in [StarType.M, StarType.K]:
            return self.rng.choices([0, 1, 2, 3, 4, 5], weights=[5, 15, 25, 30, 20, 5])[0]
        elif star_type == StarType.G:
            return self.rng.choices([0, 1, 2, 3, 4, 5, 6, 7, 8], weights=[2, 8, 15, 20, 25, 15, 10, 3, 2])[0]
        elif star_type == StarType.F:
            return self.rng.choices([0, 1, 2, 3, 4, 5, 6], weights=[5, 10, 20, 25, 25, 10, 5])[0]
        else:  # A, B, O
            return self.rng.choices([0, 1, 2, 3, 4], weights=[20, 30, 25, 15, 10])[0]
    
    def generate_planet(self, system_id: str, planet_index: int, orbital_radius: float, 
                       star_type: StarType, star_mass: float) -> Planet:
        """Generate a single planet."""
        planet_id = generate_planet_id(system_id, planet_index)
        
        # Generate planet class based on orbital radius and star type
        planet_class = self.generate_planet_class(orbital_radius, star_type, star_mass)
        
        # Generate planet properties
        mass = self.generate_planet_mass(planet_class)
        radius = self.generate_planet_radius(planet_class, mass)
        
        # Calculate habitability
        habitability = self.calculate_habitability(orbital_radius, star_type, star_mass, planet_class)
        
        # Generate population based on habitability
        population = self.generate_population(habitability, planet_class)
        
        # Generate atmosphere
        atmosphere = self.generate_atmosphere(planet_class, mass)
        
        # Generate surface gravity
        surface_gravity = mass / (radius ** 2)
        
        # Generate day/year length
        day_length = self.rng.uniform(10, 100)  # hours
        year_length = self.calculate_orbital_period(orbital_radius, star_mass)
        
        # Generate moons
        moons = self.generate_moons(planet_class, mass)
        
        # Generate resources
        resources = self.generate_resources(planet_class, orbital_radius)
        
        return Planet(
            id=planet_id,
            name=f"Planet {chr(ord('A') + planet_index)}",
            planet_class=planet_class,
            orbital_radius=orbital_radius,
            mass=mass,
            radius=radius,
            habitability=habitability,
            population=population,
            atmosphere=atmosphere,
            surface_gravity=surface_gravity,
            day_length=day_length,
            year_length=year_length,
            moons=moons,
            resources=resources
        )
    
    def generate_planet_class(self, orbital_radius: float, star_type: StarType, star_mass: float) -> PlanetClass:
        """Generate planet class based on orbital distance and star properties."""
        # Calculate effective temperature based on star luminosity and distance
        luminosity = self.calculate_stellar_luminosity(star_type, star_mass)
        temp = math.sqrt(luminosity / (16 * math.pi * orbital_radius ** 2))
        
        # Determine planet class based on temperature and random factors
        if temp > 2.0:  # Very hot
            return self.rng.choices([PlanetClass.DESERT, PlanetClass.TERRESTRIAL], weights=[70, 30])[0]
        elif temp > 1.5:  # Hot
            return self.rng.choices([PlanetClass.TERRESTRIAL, PlanetClass.DESERT], weights=[60, 40])[0]
        elif temp > 0.5:  # Temperate
            if orbital_radius > 3.0:  # Outer system
                return self.rng.choices([PlanetClass.GAS_GIANT, PlanetClass.ICE_GIANT], weights=[60, 40])[0]
            else:
                return self.rng.choices([
                    PlanetClass.TERRESTRIAL, PlanetClass.OCEAN, PlanetClass.DESERT
                ], weights=[50, 30, 20])[0]
        else:  # Cold
            if orbital_radius > 5.0:
                return self.rng.choices([PlanetClass.GAS_GIANT, PlanetClass.ICE_GIANT], weights=[40, 60])[0]
            else:
                return self.rng.choices([PlanetClass.ICE, PlanetClass.TERRESTRIAL], weights=[70, 30])[0]
    
    def calculate_stellar_luminosity(self, star_type: StarType, star_mass: float) -> float:
        """Calculate stellar luminosity (solar units)."""
        # Rough mass-luminosity relationship
        if star_mass < 0.43:
            return 0.23 * (star_mass ** 2.3)
        elif star_mass < 2.0:
            return star_mass ** 4
        else:
            return 1.4 * (star_mass ** 3.5)
    
    def generate_planet_mass(self, planet_class: PlanetClass) -> float:
        """Generate planet mass in Earth masses."""
        mass_ranges = {
            PlanetClass.TERRESTRIAL: (0.1, 5.0),
            PlanetClass.OCEAN: (0.5, 3.0),
            PlanetClass.DESERT: (0.2, 2.0),
            PlanetClass.ICE: (0.1, 2.0),
            PlanetClass.GAS_GIANT: (50.0, 500.0),
            PlanetClass.ICE_GIANT: (10.0, 50.0),
            PlanetClass.ASTEROID: (0.001, 0.1),
            PlanetClass.MOON: (0.01, 0.5),
        }
        
        min_mass, max_mass = mass_ranges.get(planet_class, (0.1, 5.0))
        return self.rng.uniform(min_mass, max_mass)
    
    def generate_planet_radius(self, planet_class: PlanetClass, mass: float) -> float:
        """Generate planet radius in Earth radii."""
        if planet_class in [PlanetClass.GAS_GIANT, PlanetClass.ICE_GIANT]:
            # Gas giants have different mass-radius relationship
            return mass ** 0.2
        else:
            # Rocky planets
            return mass ** 0.27
    
    def calculate_habitability(self, orbital_radius: float, star_type: StarType, 
                             star_mass: float, planet_class: PlanetClass) -> float:
        """Calculate habitability score (0-1)."""
        if planet_class in [PlanetClass.GAS_GIANT, PlanetClass.ICE_GIANT]:
            return 0.0
        
        # Calculate habitable zone
        luminosity = self.calculate_stellar_luminosity(star_type, star_mass)
        inner_hz = math.sqrt(luminosity / 1.1)
        outer_hz = math.sqrt(luminosity / 0.53)
        
        # Base habitability from orbital position
        if inner_hz <= orbital_radius <= outer_hz:
            base_habitability = 1.0
        else:
            # Decrease habitability outside habitable zone
            if orbital_radius < inner_hz:
                base_habitability = max(0.0, 1.0 - (inner_hz - orbital_radius) / inner_hz)
            else:
                base_habitability = max(0.0, 1.0 - (orbital_radius - outer_hz) / outer_hz)
        
        # Modify by planet class
        class_modifiers = {
            PlanetClass.TERRESTRIAL: 1.0,
            PlanetClass.OCEAN: 1.2,
            PlanetClass.DESERT: 0.3,
            PlanetClass.ICE: 0.2,
            PlanetClass.ASTEROID: 0.0,
            PlanetClass.MOON: 0.5,
        }
        
        modifier = class_modifiers.get(planet_class, 0.5)
        return min(1.0, base_habitability * modifier)
    
    def generate_population(self, habitability: float, planet_class: PlanetClass) -> int:
        """Generate population based on habitability."""
        if habitability < 0.1:
            return 0
        
        # Population scales with habitability
        if habitability > 0.8:
            base_pop = self.rng.randint(1_000_000, 10_000_000_000)
        elif habitability > 0.6:
            base_pop = self.rng.randint(100_000, 1_000_000_000)
        elif habitability > 0.4:
            base_pop = self.rng.randint(10_000, 100_000_000)
        elif habitability > 0.2:
            base_pop = self.rng.randint(1_000, 10_000_000)
        else:
            base_pop = self.rng.randint(100, 1_000_000)
        
        # Random chance of no population despite habitability
        if self.rng.random() < 0.3:
            return 0
        
        return base_pop
    
    def generate_atmosphere(self, planet_class: PlanetClass, mass: float) -> str:
        """Generate atmosphere description."""
        if planet_class in [PlanetClass.GAS_GIANT, PlanetClass.ICE_GIANT]:
            return "dense hydrogen/helium"
        elif planet_class == PlanetClass.ASTEROID:
            return "none"
        elif mass < 0.1:
            return "none"
        elif mass < 0.5:
            return "thin"
        elif planet_class == PlanetClass.TERRESTRIAL:
            return self.rng.choice([
                "nitrogen/oxygen", "carbon dioxide", "nitrogen/methane", "noble gases"
            ])
        elif planet_class == PlanetClass.OCEAN:
            return "nitrogen/oxygen/water vapor"
        elif planet_class == PlanetClass.DESERT:
            return "carbon dioxide/nitrogen"
        elif planet_class == PlanetClass.ICE:
            return "thin carbon dioxide"
        else:
            return "unknown"
    
    def calculate_orbital_period(self, orbital_radius: float, star_mass: float) -> float:
        """Calculate orbital period in Earth days."""
        # Kepler's third law (simplified)
        return 365.25 * math.sqrt((orbital_radius ** 3) / star_mass)
    
    def generate_moons(self, planet_class: PlanetClass, mass: float) -> List[str]:
        """Generate moons for a planet."""
        if planet_class in [PlanetClass.ASTEROID, PlanetClass.MOON]:
            return []
        
        # Moon probability increases with planet mass
        if mass < 1.0:
            moon_count = self.rng.choices([0, 1, 2], weights=[70, 25, 5])[0]
        elif mass < 10.0:
            moon_count = self.rng.choices([0, 1, 2, 3], weights=[40, 35, 20, 5])[0]
        else:  # Gas giants
            moon_count = self.rng.choices([0, 1, 2, 3, 4, 5, 6], weights=[10, 15, 20, 25, 15, 10, 5])[0]
        
        return [f"Moon {i+1}" for i in range(moon_count)]
    
    def generate_resources(self, planet_class: PlanetClass, orbital_radius: float) -> Dict[str, float]:
        """Generate resource deposits."""
        resources = {}
        
        # Gravitium is rare and found mainly in specific conditions
        if self.rng.random() < 0.05:  # 5% chance
            resources["gravitium"] = self.rng.uniform(10.0, 1000.0)
        
        # Common resources
        if planet_class == PlanetClass.TERRESTRIAL:
            resources["metals"] = self.rng.uniform(0.1, 5.0)
            resources["rare_earth"] = self.rng.uniform(0.01, 1.0)
        elif planet_class == PlanetClass.ASTEROID:
            resources["metals"] = self.rng.uniform(5.0, 50.0)
            resources["rare_earth"] = self.rng.uniform(1.0, 10.0)
        elif planet_class == PlanetClass.GAS_GIANT:
            resources["hydrogen"] = self.rng.uniform(100.0, 1000.0)
            resources["helium"] = self.rng.uniform(10.0, 100.0)
        elif planet_class == PlanetClass.ICE:
            resources["water"] = self.rng.uniform(10.0, 100.0)
        
        return resources
    
    def generate_system_population(self, planets: List[Planet]) -> int:
        """Generate additional system population (space stations, etc.)."""
        planet_pop = sum(p.population for p in planets)
        
        if planet_pop > 1_000_000_000:
            return self.rng.randint(10_000_000, 100_000_000)
        elif planet_pop > 10_000_000:
            return self.rng.randint(100_000, 10_000_000)
        elif planet_pop > 100_000:
            return self.rng.randint(1_000, 100_000)
        else:
            return 0
    
    def generate_tech_level(self, total_population: int) -> CivilizationTier:
        """Generate technology level based on population."""
        if total_population == 0:
            return CivilizationTier.PRIMITIVE
        elif total_population < 1_000:
            return CivilizationTier.PRIMITIVE
        elif total_population < 100_000:
            return CivilizationTier.INDUSTRIAL
        elif total_population < 10_000_000:
            return CivilizationTier.NUCLEAR
        elif total_population < 1_000_000_000:
            return CivilizationTier.FUSION
        elif total_population < 10_000_000_000:
            return CivilizationTier.ANTIMATTER
        else:
            # Higher tech levels are rare
            return self.rng.choices([
                CivilizationTier.ANTIMATTER,
                CivilizationTier.RAIL_AGE,
                CivilizationTier.SINGULARITY
            ], weights=[70, 25, 5])[0]
    
    def generate_trade_codes(self, system: System) -> List[str]:
        """Generate trade codes for a system."""
        codes = []
        
        # Population-based codes
        if system.total_population > 1_000_000_000:
            codes.append("Hi")  # High population
        elif system.total_population < 1_000:
            codes.append("Lo")  # Low population
        
        # Resource-based codes
        has_metals = any("metals" in p.resources for p in system.planets)
        has_water = any("water" in p.resources for p in system.planets)
        has_gravitium = any("gravitium" in p.resources for p in system.planets)
        
        if has_metals:
            codes.append("In")  # Industrial
        if has_water:
            codes.append("Wa")  # Water
        if has_gravitium:
            codes.append("Gv")  # Gravitium
        
        # Habitability-based codes
        habitable_count = len(system.habitable_worlds)
        if habitable_count == 0:
            codes.append("Ba")  # Barren
        elif habitable_count >= 3:
            codes.append("Ga")  # Garden
        
        # Tech level codes
        if system.tech_level == CivilizationTier.RAIL_AGE:
            codes.append("Ht")  # High tech
        elif system.tech_level.value >= 6:
            codes.append("TL")  # Transcendent level
        
        return codes
    
    def generate_system(self, coord: Coordinate, name: Optional[str] = None) -> System:
        """Generate a complete star system."""
        system_id = generate_system_id()
        
        # Generate star properties
        star_type = self.generate_star_type()
        star_mass = self.generate_star_mass(star_type)
        star_age = self.generate_star_age(star_type)
        
        # Generate planets
        planet_count = self.generate_planet_count(star_type)
        planets = []
        
        for i in range(planet_count):
            # Generate orbital radius (simplified)
            orbital_radius = 0.3 * (1.5 ** i) + self.rng.uniform(-0.1, 0.1)
            planet = self.generate_planet(system_id, i, orbital_radius, star_type, star_mass)
            planets.append(planet)
        
        # Generate system-level properties
        system_population = self.generate_system_population(planets)
        total_population = system_population + sum(p.population for p in planets)
        tech_level = self.generate_tech_level(total_population)
        
        # Generate gravitium deposits
        gravitium_deposits = 0.0
        for planet in planets:
            gravitium_deposits += planet.resources.get("gravitium", 0.0)
        
        # Add system-level gravitium deposits (rare)
        if self.rng.random() < 0.02:  # 2% chance
            gravitium_deposits += self.rng.uniform(100.0, 5000.0)
        
        # Generate faction control
        faction_control = self.generate_faction_control(total_population, tech_level)
        
        # Create system
        system = System(
            id=system_id,
            name=name or f"System {system_id[-8:]}",
            coord=coord,
            star_type=star_type,
            star_mass=star_mass,
            star_age=star_age,
            planets=planets,
            population=system_population,
            tech_level=tech_level,
            faction_control=faction_control,
            gravitium_deposits=gravitium_deposits,
            trade_codes=[],
            rails_out=[]
        )
        
        # Generate trade codes
        trade_codes = self.generate_trade_codes(system)
        system = replace(system, trade_codes=trade_codes)
        
        return system
    
    def generate_faction_control(self, population: int, tech_level: CivilizationTier) -> str:
        """Generate faction control based on population and tech level."""
        if population < 10_000:
            return "independent"
        elif tech_level.value >= 5:  # Rail age or higher
            return self.rng.choice([
                "Terran Federation", "Fissari Coalition", "Independent Worlds",
                "Corporate Syndicate", "Outer Rim Alliance"
            ])
        else:
            return self.rng.choice([
                "independent", "local government", "corporate", "tribal"
            ])


class DefaultStarGenerator(StarGenerator):
    """Default star generator implementation."""
    pass