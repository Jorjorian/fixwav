"""
Rail network generator.

Implements the rail network construction algorithm using minimum spanning tree
from Source Vein systems, with cycle detection and gravitium cost calculation.
"""

import random
import math
from datetime import datetime, timedelta
from typing import List, Dict, Set, Tuple, Optional, Any
from dataclasses import replace

from ..core.models import (
    System, Rail, Galaxy, RailClass, Coordinate,
    generate_rail_id, calculate_gravitium_cost, rail_class_from_capacity
)
from ..core.validators import detect_loops


class RailGenerator:
    """Base class for rail network generators."""
    
    def __init__(self, seed: Optional[int] = None):
        self.rng = random.Random(seed)
    
    def find_source_vein_systems(self, galaxy: Galaxy, min_gravitium: float = 1000.0) -> List[str]:
        """Find systems suitable as Source Vein locations."""
        candidates = []
        
        for system_id, system in galaxy.systems.items():
            if system.gravitium_deposits >= min_gravitium:
                candidates.append(system_id)
        
        # Sort by gravitium deposits (descending)
        candidates.sort(
            key=lambda sid: galaxy.systems[sid].gravitium_deposits,
            reverse=True
        )
        
        return candidates
    
    def calculate_rail_cost(self, from_system: System, to_system: System, 
                           rail_class: RailClass) -> float:
        """Calculate the cost of building a rail between two systems."""
        distance = from_system.coord.distance_to(to_system.coord)
        base_cost = calculate_gravitium_cost(distance, rail_class)
        
        # Add modifiers based on system properties
        tech_modifier = 1.0
        if from_system.tech_level.value < 5:  # Below rail age
            tech_modifier *= 2.0
        if to_system.tech_level.value < 5:
            tech_modifier *= 2.0
        
        # Population modifier (need workers)
        pop_modifier = 1.0
        if from_system.total_population < 10_000:
            pop_modifier *= 1.5
        if to_system.total_population < 10_000:
            pop_modifier *= 1.5
        
        return base_cost * tech_modifier * pop_modifier
    
    def estimate_rail_capacity(self, from_system: System, to_system: System) -> float:
        """Estimate required rail capacity based on system populations."""
        # Base capacity on population and trade potential
        from_pop = from_system.total_population
        to_pop = to_system.total_population
        
        # Trade volume roughly proportional to population product
        trade_volume = math.sqrt(from_pop * to_pop) / 1000.0
        
        # Add bonuses for resource differences
        from_resources = set()
        to_resources = set()
        
        for planet in from_system.planets:
            from_resources.update(planet.resources.keys())
        for planet in to_system.planets:
            to_resources.update(planet.resources.keys())
        
        # More trade if systems have different resources
        unique_resources = len(from_resources.symmetric_difference(to_resources))
        trade_volume *= (1.0 + unique_resources * 0.1)
        
        # Tech level difference creates trade
        tech_diff = abs(from_system.tech_level.value - to_system.tech_level.value)
        trade_volume *= (1.0 + tech_diff * 0.2)
        
        return max(100.0, trade_volume)  # Minimum 100 t/year
    
    def build_minimum_spanning_tree(self, galaxy: Galaxy, 
                                   source_systems: List[str]) -> List[Tuple[str, str, float]]:
        """Build minimum spanning tree for rail network using Prim's algorithm."""
        if not source_systems:
            return []
        
        # Convert to list of all systems
        all_systems = list(galaxy.systems.keys())
        
        # Initialize with source systems
        in_tree = set(source_systems)
        edges = []
        
        while len(in_tree) < len(all_systems):
            best_edge = None
            best_cost = float('inf')
            
            # Find minimum cost edge from tree to outside
            for from_id in in_tree:
                from_system = galaxy.systems[from_id]
                
                for to_id in all_systems:
                    if to_id not in in_tree:
                        to_system = galaxy.systems[to_id]
                        
                        # Estimate rail class needed
                        capacity = self.estimate_rail_capacity(from_system, to_system)
                        rail_class = rail_class_from_capacity(capacity)
                        
                        cost = self.calculate_rail_cost(from_system, to_system, rail_class)
                        
                        if cost < best_cost:
                            best_cost = cost
                            best_edge = (from_id, to_id, cost)
            
            if best_edge:
                edges.append(best_edge)
                in_tree.add(best_edge[1])
            else:
                # No more reachable systems
                break
        
        return edges
    
    def add_redundancy_connections(self, galaxy: Galaxy, mst_edges: List[Tuple[str, str, float]], 
                                  redundancy_factor: float = 0.1) -> List[Tuple[str, str, float]]:
        """Add redundancy connections to prevent single points of failure."""
        additional_edges = []
        
        # Find systems with only one connection (potential bottlenecks)
        connection_count = {}
        for from_id, to_id, _ in mst_edges:
            connection_count[from_id] = connection_count.get(from_id, 0) + 1
            connection_count[to_id] = connection_count.get(to_id, 0) + 1
        
        bottlenecks = [sys_id for sys_id, count in connection_count.items() if count == 1]
        
        # Add connections for bottleneck systems
        for bottleneck_id in bottlenecks:
            if self.rng.random() < redundancy_factor:
                bottleneck_system = galaxy.systems[bottleneck_id]
                
                # Find nearby systems not already connected
                nearby_systems = []
                for other_id, other_system in galaxy.systems.items():
                    if other_id != bottleneck_id:
                        distance = bottleneck_system.coord.distance_to(other_system.coord)
                        if distance < 50.0:  # Within 50 LY
                            # Check if not already connected
                            already_connected = any(
                                (bottleneck_id == from_id and other_id == to_id) or
                                (bottleneck_id == to_id and other_id == from_id)
                                for from_id, to_id, _ in mst_edges
                            )
                            if not already_connected:
                                nearby_systems.append((other_id, distance))
                
                # Connect to closest nearby system
                if nearby_systems:
                    nearby_systems.sort(key=lambda x: x[1])
                    target_id = nearby_systems[0][0]
                    target_system = galaxy.systems[target_id]
                    
                    capacity = self.estimate_rail_capacity(bottleneck_system, target_system)
                    rail_class = rail_class_from_capacity(capacity)
                    cost = self.calculate_rail_cost(bottleneck_system, target_system, rail_class)
                    
                    additional_edges.append((bottleneck_id, target_id, cost))
        
        return additional_edges
    
    def create_rail(self, from_system_id: str, to_system_id: str, 
                   galaxy: Galaxy, construction_date: datetime) -> Rail:
        """Create a rail between two systems."""
        from_system = galaxy.systems[from_system_id]
        to_system = galaxy.systems[to_system_id]
        
        # Calculate properties
        distance = from_system.coord.distance_to(to_system.coord)
        capacity = self.estimate_rail_capacity(from_system, to_system)
        rail_class = rail_class_from_capacity(capacity)
        gravitium_cost = calculate_gravitium_cost(distance, rail_class)
        
        # Determine firing interval based on rail class
        interval_map = {
            RailClass.RFC_A: self.rng.randint(1, 7),      # 1-7 days
            RailClass.RFC_B: self.rng.randint(7, 30),     # 1-4 weeks
            RailClass.RFC_C: self.rng.randint(30, 180),   # 1-6 months
            RailClass.RFC_D: self.rng.randint(180, 365),  # 6-12 months
        }
        interval_days = interval_map[rail_class]
        
        # Calculate max capacity per firing
        annual_capacity = {
            RailClass.RFC_A: 1_000_000,
            RailClass.RFC_B: 600_000,
            RailClass.RFC_C: 1_800,
            RailClass.RFC_D: 182.5,
        }
        max_capacity = annual_capacity[rail_class] / (365.25 / interval_days)
        
        # Generate next firing time
        next_fire = construction_date + timedelta(days=self.rng.randint(1, interval_days))
        
        return Rail(
            id=generate_rail_id(),
            from_system=from_system_id,
            to_system=to_system_id,
            rail_class=rail_class,
            length=distance,
            construction_date=construction_date,
            interval_days=interval_days,
            next_fire=next_fire,
            gravitium_cost=gravitium_cost,
            max_capacity=max_capacity
        )
    
    def validate_no_cycles(self, rails: List[Rail]) -> bool:
        """Validate that rail network has no cycles."""
        cycles = detect_loops(rails)
        return len(cycles) == 0
    
    def generate_rail_network(self, galaxy: Galaxy, 
                            construction_start: Optional[datetime] = None,
                            max_systems: Optional[int] = None) -> Dict[str, Rail]:
        """Generate complete rail network for galaxy."""
        if construction_start is None:
            construction_start = datetime(2800, 1, 1)  # Start of rail age
        
        rails = {}
        
        # Find source vein systems
        source_systems = self.find_source_vein_systems(galaxy)
        if not source_systems:
            # No suitable source systems found
            return rails
        
        # Limit to top source systems if specified
        if max_systems and len(source_systems) > max_systems:
            source_systems = source_systems[:max_systems]
        
        # Build minimum spanning tree
        mst_edges = self.build_minimum_spanning_tree(galaxy, source_systems)
        
        # Add redundancy connections
        redundancy_edges = self.add_redundancy_connections(galaxy, mst_edges)
        all_edges = mst_edges + redundancy_edges
        
        # Create rails from edges
        construction_date = construction_start
        
        for from_id, to_id, cost in all_edges:
            rail = self.create_rail(from_id, to_id, galaxy, construction_date)
            
            # Validate no cycles before adding
            test_rails = list(rails.values()) + [rail]
            if self.validate_no_cycles(test_rails):
                rails[rail.id] = rail
                
                # Advance construction date (rails take time to build)
                construction_years = max(1, int(rail.length / 10))  # ~10 LY per year
                construction_date += timedelta(days=construction_years * 365.25)
            else:
                # Skip this rail to avoid cycle
                continue
        
        return rails
    
    def generate_construction_schedule(self, rails: Dict[str, Rail]) -> List[Tuple[str, datetime]]:
        """Generate construction schedule for rails."""
        schedule = []
        
        for rail_id, rail in rails.items():
            schedule.append((rail_id, rail.construction_date))
        
        # Sort by construction date
        schedule.sort(key=lambda x: x[1])
        
        return schedule
    
    def calculate_total_gravitium_cost(self, rails: Dict[str, Rail]) -> float:
        """Calculate total gravitium cost of rail network."""
        return sum(rail.gravitium_cost for rail in rails.values())
    
    def get_network_statistics(self, galaxy: Galaxy) -> Dict[str, Any]:
        """Get statistics about the rail network."""
        rails = galaxy.rails
        
        stats = {
            'total_rails': len(rails),
            'total_gravitium_cost': self.calculate_total_gravitium_cost(rails),
            'connected_systems': len(galaxy.connected_systems),
            'total_systems': len(galaxy.systems),
            'coverage_percentage': len(galaxy.connected_systems) / len(galaxy.systems) * 100,
        }
        
        # Rail class distribution
        class_count = {}
        for rail in rails.values():
            class_count[rail.rail_class] = class_count.get(rail.rail_class, 0) + 1
        
        stats['rail_classes'] = class_count
        
        # Average metrics
        if rails:
            stats['average_length'] = sum(rail.length for rail in rails.values()) / len(rails)
            stats['average_interval'] = sum(rail.interval_days for rail in rails.values()) / len(rails)
        else:
            stats['average_length'] = 0
            stats['average_interval'] = 0
        
        return stats
    
    def optimize_rail_schedules(self, galaxy: Galaxy) -> Dict[str, Rail]:
        """Optimize rail firing schedules to minimize conflicts."""
        optimized_rails = {}
        
        # Group rails by system
        system_rails = {}
        for rail in galaxy.rails.values():
            if rail.from_system not in system_rails:
                system_rails[rail.from_system] = []
            system_rails[rail.from_system].append(rail)
        
        # Optimize schedules for each system
        for system_id, rails in system_rails.items():
            if len(rails) <= 1:
                # No conflicts possible
                for rail in rails:
                    optimized_rails[rail.id] = rail
                continue
            
            # Sort rails by interval
            rails.sort(key=lambda r: r.interval_days)
            
            # Distribute firing times to minimize conflicts
            base_time = datetime(3000, 1, 1)
            
            for i, rail in enumerate(rails):
                # Offset each rail by a fraction of its interval
                offset_days = (rail.interval_days * i) // len(rails)
                new_next_fire = base_time + timedelta(days=offset_days)
                
                # Create new rail with optimized schedule
                optimized_rail = replace(rail, next_fire=new_next_fire)
                optimized_rails[optimized_rail.id] = optimized_rail
        
        return optimized_rails


class DefaultRailGenerator(RailGenerator):
    """Default rail generator implementation."""
    
    def __init__(self, seed: Optional[int] = None):
        super().__init__(seed)
        self.construction_rate = 10.0  # Light-years per year
        self.redundancy_factor = 0.15  # 15% chance of redundant connections