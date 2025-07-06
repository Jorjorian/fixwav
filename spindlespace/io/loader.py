"""
Galaxy loader for JSON/YAML serialization.

Handles loading and saving galaxy data to persistent storage.
"""

import json
import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from ..core.models import (
    Galaxy, System, Planet, Rail, Schedule, Civilization, Coordinate,
    StarType, PlanetClass, RailClass, CivilizationTier
)


class GalaxyLoader:
    """Handles loading and saving galaxy data."""
    
    def __init__(self):
        self.format_version = "1.0"
    
    def galaxy_to_dict(self, galaxy: Galaxy) -> Dict[str, Any]:
        """Convert galaxy to dictionary for serialization."""
        return {
            "format_version": self.format_version,
            "galaxy": {
                "id": galaxy.id,
                "name": galaxy.name,
                "seed": galaxy.seed,
                "generation_time": galaxy.generation_time.isoformat(),
                "systems": {
                    system_id: self.system_to_dict(system)
                    for system_id, system in galaxy.systems.items()
                },
                "rails": {
                    rail_id: self.rail_to_dict(rail)
                    for rail_id, rail in galaxy.rails.items()
                },
                "civilizations": {
                    civ_id: self.civilization_to_dict(civ)
                    for civ_id, civ in galaxy.civilizations.items()
                },
                "source_vein_systems": galaxy.source_vein_systems,
            }
        }
    
    def system_to_dict(self, system: System) -> Dict[str, Any]:
        """Convert system to dictionary."""
        return {
            "id": system.id,
            "name": system.name,
            "coord": {
                "x": system.coord.x,
                "y": system.coord.y,
                "z": system.coord.z,
            },
            "star_type": system.star_type.value,
            "star_mass": system.star_mass,
            "star_age": system.star_age,
            "planets": [self.planet_to_dict(planet) for planet in system.planets],
            "population": system.population,
            "tech_level": system.tech_level.value,
            "faction_control": system.faction_control,
            "gravitium_deposits": system.gravitium_deposits,
            "trade_codes": system.trade_codes,
            "rails_out": [self.rail_to_dict(rail) for rail in system.rails_out],
        }
    
    def planet_to_dict(self, planet: Planet) -> Dict[str, Any]:
        """Convert planet to dictionary."""
        return {
            "id": planet.id,
            "name": planet.name,
            "planet_class": planet.planet_class.value,
            "orbital_radius": planet.orbital_radius,
            "mass": planet.mass,
            "radius": planet.radius,
            "habitability": planet.habitability,
            "population": planet.population,
            "atmosphere": planet.atmosphere,
            "surface_gravity": planet.surface_gravity,
            "day_length": planet.day_length,
            "year_length": planet.year_length,
            "moons": planet.moons,
            "resources": planet.resources,
        }
    
    def rail_to_dict(self, rail: Rail) -> Dict[str, Any]:
        """Convert rail to dictionary."""
        return {
            "id": rail.id,
            "from_system": rail.from_system,
            "to_system": rail.to_system,
            "rail_class": rail.rail_class.value,
            "length": rail.length,
            "construction_date": rail.construction_date.isoformat(),
            "interval_days": rail.interval_days,
            "next_fire": rail.next_fire.isoformat(),
            "gravitium_cost": rail.gravitium_cost,
            "max_capacity": rail.max_capacity,
        }
    
    def civilization_to_dict(self, civ: Civilization) -> Dict[str, Any]:
        """Convert civilization to dictionary."""
        return {
            "id": civ.id,
            "name": civ.name,
            "species": civ.species,
            "government_type": civ.government_type,
            "tech_level": civ.tech_level.value,
            "population": civ.population,
            "home_system": civ.home_system,
            "controlled_systems": civ.controlled_systems,
            "relations": civ.relations,
            "traits": civ.traits,
        }
    
    def dict_to_galaxy(self, data: Dict[str, Any]) -> Galaxy:
        """Convert dictionary to galaxy object."""
        galaxy_data = data["galaxy"]
        
        # Convert systems
        systems = {}
        for system_id, system_data in galaxy_data["systems"].items():
            systems[system_id] = self.dict_to_system(system_data)
        
        # Convert rails
        rails = {}
        for rail_id, rail_data in galaxy_data["rails"].items():
            rails[rail_id] = self.dict_to_rail(rail_data)
        
        # Convert civilizations
        civilizations = {}
        for civ_id, civ_data in galaxy_data["civilizations"].items():
            civilizations[civ_id] = self.dict_to_civilization(civ_data)
        
        return Galaxy(
            id=galaxy_data["id"],
            name=galaxy_data["name"],
            seed=galaxy_data["seed"],
            generation_time=datetime.fromisoformat(galaxy_data["generation_time"]),
            systems=systems,
            rails=rails,
            civilizations=civilizations,
            source_vein_systems=galaxy_data.get("source_vein_systems", []),
        )
    
    def dict_to_system(self, data: Dict[str, Any]) -> System:
        """Convert dictionary to system object."""
        coord = Coordinate(
            x=data["coord"]["x"],
            y=data["coord"]["y"],
            z=data["coord"]["z"],
        )
        
        planets = [self.dict_to_planet(planet_data) for planet_data in data["planets"]]
        rails_out = [self.dict_to_rail(rail_data) for rail_data in data["rails_out"]]
        
        return System(
            id=data["id"],
            name=data["name"],
            coord=coord,
            star_type=StarType(data["star_type"]),
            star_mass=data["star_mass"],
            star_age=data["star_age"],
            planets=planets,
            population=data["population"],
            tech_level=CivilizationTier(data["tech_level"]),
            faction_control=data["faction_control"],
            gravitium_deposits=data["gravitium_deposits"],
            trade_codes=data["trade_codes"],
            rails_out=rails_out,
        )
    
    def dict_to_planet(self, data: Dict[str, Any]) -> Planet:
        """Convert dictionary to planet object."""
        return Planet(
            id=data["id"],
            name=data["name"],
            planet_class=PlanetClass(data["planet_class"]),
            orbital_radius=data["orbital_radius"],
            mass=data["mass"],
            radius=data["radius"],
            habitability=data["habitability"],
            population=data["population"],
            atmosphere=data["atmosphere"],
            surface_gravity=data["surface_gravity"],
            day_length=data["day_length"],
            year_length=data["year_length"],
            moons=data["moons"],
            resources=data["resources"],
        )
    
    def dict_to_rail(self, data: Dict[str, Any]) -> Rail:
        """Convert dictionary to rail object."""
        return Rail(
            id=data["id"],
            from_system=data["from_system"],
            to_system=data["to_system"],
            rail_class=RailClass(data["rail_class"]),
            length=data["length"],
            construction_date=datetime.fromisoformat(data["construction_date"]),
            interval_days=data["interval_days"],
            next_fire=datetime.fromisoformat(data["next_fire"]),
            gravitium_cost=data["gravitium_cost"],
            max_capacity=data["max_capacity"],
        )
    
    def dict_to_civilization(self, data: Dict[str, Any]) -> Civilization:
        """Convert dictionary to civilization object."""
        return Civilization(
            id=data["id"],
            name=data["name"],
            species=data["species"],
            government_type=data["government_type"],
            tech_level=CivilizationTier(data["tech_level"]),
            population=data["population"],
            home_system=data["home_system"],
            controlled_systems=data["controlled_systems"],
            relations=data["relations"],
            traits=data["traits"],
        )
    
    def save_galaxy(self, galaxy: Galaxy, filepath: Path) -> None:
        """Save galaxy to file."""
        data = self.galaxy_to_dict(galaxy)
        
        if filepath.suffix.lower() == ".json":
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
        elif filepath.suffix.lower() in [".yaml", ".yml"]:
            with open(filepath, 'w') as f:
                yaml.dump(data, f, default_flow_style=False, sort_keys=False)
        else:
            # Default to JSON
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
    
    def load_galaxy(self, filepath: Path) -> Galaxy:
        """Load galaxy from file."""
        if filepath.suffix.lower() == ".json":
            with open(filepath, 'r') as f:
                data = json.load(f)
        elif filepath.suffix.lower() in [".yaml", ".yml"]:
            with open(filepath, 'r') as f:
                data = yaml.safe_load(f)
        else:
            # Try JSON first, then YAML
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
            except json.JSONDecodeError:
                with open(filepath, 'r') as f:
                    data = yaml.safe_load(f)
        
        return self.dict_to_galaxy(data)
    
    def save_schedule(self, schedule: Dict[str, Schedule], filepath: Path) -> None:
        """Save schedule to file."""
        data = {
            "format_version": self.format_version,
            "schedules": {
                rail_id: {
                    "rail_id": sched.rail_id,
                    "departures": [dep.isoformat() for dep in sched.departures],
                    "transit_time": sched.transit_time.total_seconds(),
                }
                for rail_id, sched in schedule.items()
            }
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
    
    def create_backup(self, galaxy: Galaxy, backup_dir: Path) -> Path:
        """Create a timestamped backup of the galaxy."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"{galaxy.name}_{timestamp}.spindle.json"
        backup_path = backup_dir / backup_filename
        
        backup_dir.mkdir(parents=True, exist_ok=True)
        self.save_galaxy(galaxy, backup_path)
        
        return backup_path
    
    def validate_file_format(self, filepath: Path) -> bool:
        """Validate that file has correct format."""
        try:
            data = {}
            if filepath.suffix.lower() == ".json":
                with open(filepath, 'r') as f:
                    data = json.load(f)
            elif filepath.suffix.lower() in [".yaml", ".yml"]:
                with open(filepath, 'r') as f:
                    data = yaml.safe_load(f)
            
            # Check for required fields
            if "format_version" not in data:
                return False
            if "galaxy" not in data:
                return False
            
            galaxy_data = data["galaxy"]
            required_fields = ["id", "name", "seed", "generation_time", "systems"]
            
            for field in required_fields:
                if field not in galaxy_data:
                    return False
            
            return True
        
        except Exception:
            return False
    
    def get_file_info(self, filepath: Path) -> Optional[Dict[str, Any]]:
        """Get basic information about a galaxy file without full loading."""
        try:
            data = {}
            if filepath.suffix.lower() == ".json":
                with open(filepath, 'r') as f:
                    data = json.load(f)
            elif filepath.suffix.lower() in [".yaml", ".yml"]:
                with open(filepath, 'r') as f:
                    data = yaml.safe_load(f)
            
            galaxy_data = data.get("galaxy", {})
            
            return {
                "name": galaxy_data.get("name", "Unknown"),
                "seed": galaxy_data.get("seed", 0),
                "generation_time": galaxy_data.get("generation_time", "Unknown"),
                "system_count": len(galaxy_data.get("systems", {})),
                "rail_count": len(galaxy_data.get("rails", {})),
                "format_version": data.get("format_version", "Unknown"),
            }
        
        except Exception:
            return None