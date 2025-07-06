"""
Schedule generator for rail firing times and travel calendars.

Generates firing schedules for rails and provides travel planning utilities.
"""

import random
import math
from datetime import datetime, timedelta
from typing import List, Dict, Set, Tuple, Optional, Any
from dataclasses import replace

from ..core.models import Rail, Schedule, Galaxy


class ScheduleGenerator:
    """Base class for schedule generators."""
    
    def __init__(self, seed: Optional[int] = None):
        self.rng = random.Random(seed)
    
    def generate_rail_schedule(self, rail: Rail, start_date: datetime, 
                              duration_days: int = 365) -> Schedule:
        """Generate firing schedule for a rail."""
        departures = []
        current_date = start_date
        
        # Find first departure after start date
        while current_date < rail.next_fire:
            current_date += timedelta(days=rail.interval_days)
        
        # Generate departures for the duration
        end_date = start_date + timedelta(days=duration_days)
        while current_date <= end_date:
            departures.append(current_date)
            current_date += timedelta(days=rail.interval_days)
        
        return Schedule(
            rail_id=rail.id,
            departures=departures,
            transit_time=timedelta(hours=1)  # Near-instantaneous transit
        )
    
    def generate_galaxy_schedule(self, galaxy: Galaxy, start_date: datetime,
                               duration_days: int = 365) -> Dict[str, Schedule]:
        """Generate schedules for all rails in a galaxy."""
        schedules = {}
        
        for rail_id, rail in galaxy.rails.items():
            schedule = self.generate_rail_schedule(rail, start_date, duration_days)
            schedules[rail_id] = schedule
        
        return schedules
    
    def get_next_departures(self, rail: Rail, after_date: datetime, 
                           count: int = 10) -> List[datetime]:
        """Get next N departures for a rail after a given date."""
        departures = []
        current_date = rail.next_fire
        
        # Fast-forward to after the given date
        while current_date <= after_date:
            current_date += timedelta(days=rail.interval_days)
        
        # Generate the requested number of departures
        for _ in range(count):
            departures.append(current_date)
            current_date += timedelta(days=rail.interval_days)
        
        return departures
    
    def find_route_schedule(self, galaxy: Galaxy, from_system: str, 
                           to_system: str, departure_after: datetime) -> Optional[List[Tuple[str, datetime]]]:
        """Find a route with departure times between two systems."""
        # Get shortest path
        route = galaxy.get_route(from_system, to_system)
        if not route:
            return None
        
        if len(route) == 1:
            return [(from_system, departure_after)]
        
        # Find rails for each segment
        schedule_segments = []
        current_time = departure_after
        
        for i in range(len(route) - 1):
            from_sys = route[i]
            to_sys = route[i + 1]
            
            # Find rail between these systems
            rail = None
            for r in galaxy.rails.values():
                if r.from_system == from_sys and r.to_system == to_sys:
                    rail = r
                    break
            
            if not rail:
                return None  # No rail found
            
            # Get next departure after current time
            next_departures = self.get_next_departures(rail, current_time, 1)
            if not next_departures:
                return None
            
            departure_time = next_departures[0]
            schedule_segments.append((from_sys, departure_time))
            
            # Update current time for next segment
            current_time = departure_time + timedelta(hours=1)  # Transit time
        
        # Add final destination
        schedule_segments.append((to_system, current_time))
        
        return schedule_segments
    
    def calculate_journey_time(self, galaxy: Galaxy, from_system: str, 
                             to_system: str, departure_after: datetime) -> Optional[timedelta]:
        """Calculate total journey time between systems."""
        schedule = self.find_route_schedule(galaxy, from_system, to_system, departure_after)
        if not schedule:
            return None
        
        start_time = schedule[0][1]
        end_time = schedule[-1][1]
        
        return end_time - start_time
    
    def get_system_departures(self, galaxy: Galaxy, system_id: str,
                             after_date: datetime, count: int = 20) -> List[Tuple[str, datetime, str]]:
        """Get next departures from a system to all connected systems."""
        departures = []
        
        # Find all outgoing rails from this system
        for rail in galaxy.rails.values():
            if rail.from_system == system_id:
                next_deps = self.get_next_departures(rail, after_date, count // 2)
                for dep_time in next_deps:
                    departures.append((rail.from_system, dep_time, rail.to_system))
        
        # Sort by departure time
        departures.sort(key=lambda x: x[1])
        
        return departures[:count]
    
    def optimize_departure_times(self, galaxy: Galaxy, base_date: datetime) -> Dict[str, Rail]:
        """Optimize departure times to minimize system conflicts."""
        optimized_rails = {}
        
        # Group rails by departure system
        system_rails = {}
        for rail in galaxy.rails.values():
            if rail.from_system not in system_rails:
                system_rails[rail.from_system] = []
            system_rails[rail.from_system].append(rail)
        
        # Optimize each system's departure times
        for system_id, rails in system_rails.items():
            if len(rails) <= 1:
                # No conflicts possible
                for rail in rails:
                    optimized_rails[rail.id] = rail
                continue
            
            # Sort rails by interval (optimize high-frequency first)
            rails.sort(key=lambda r: r.interval_days)
            
            # Distribute departure times to minimize conflicts
            current_offset = 0
            for rail in rails:
                # Calculate new next fire time
                new_next_fire = base_date + timedelta(days=current_offset)
                
                # Create optimized rail
                optimized_rail = replace(rail, next_fire=new_next_fire)
                optimized_rails[optimized_rail.id] = optimized_rail
                
                # Increment offset to space out departures
                current_offset += max(1, rail.interval_days // len(rails))
        
        return optimized_rails
    
    def generate_travel_calendar(self, galaxy: Galaxy, from_system: str,
                               start_date: datetime, duration_days: int = 30) -> Dict[str, List[datetime]]:
        """Generate travel calendar showing departures to all reachable systems."""
        calendar = {}
        
        # Find all reachable systems
        reachable = set()
        for rail in galaxy.rails.values():
            if rail.from_system == from_system:
                reachable.add(rail.to_system)
        
        # Generate departure times for each reachable system
        for target_system in reachable:
            # Find rail to this system
            rail = None
            for r in galaxy.rails.values():
                if r.from_system == from_system and r.to_system == target_system:
                    rail = r
                    break
            
            if rail:
                departures = []
                current_date = start_date
                end_date = start_date + timedelta(days=duration_days)
                
                # Find first departure after start date
                while current_date < rail.next_fire:
                    current_date += timedelta(days=rail.interval_days)
                
                # Generate departures within the time window
                while current_date <= end_date:
                    departures.append(current_date)
                    current_date += timedelta(days=rail.interval_days)
                
                calendar[target_system] = departures
        
        return calendar
    
    def calculate_system_connectivity_score(self, galaxy: Galaxy, system_id: str) -> float:
        """Calculate connectivity score based on departure frequency."""
        total_score = 0.0
        
        # Find all outgoing rails
        for rail in galaxy.rails.values():
            if rail.from_system == system_id:
                # Score based on frequency (lower interval = higher score)
                frequency_score = 365.0 / rail.interval_days
                
                # Weight by rail class
                class_weights = {
                    'RFC-A': 4.0,
                    'RFC-B': 3.0,
                    'RFC-C': 2.0,
                    'RFC-D': 1.0,
                }
                class_weight = class_weights.get(rail.rail_class.value, 1.0)
                
                total_score += frequency_score * class_weight
        
        return total_score
    
    def find_optimal_departure_time(self, galaxy: Galaxy, from_system: str,
                                  to_system: str, preferred_time: datetime,
                                  flexibility_days: int = 7) -> Optional[datetime]:
        """Find optimal departure time within a flexibility window."""
        route = galaxy.get_route(from_system, to_system)
        if not route or len(route) < 2:
            return None
        
        # Find the first rail in the route
        first_rail = None
        for rail in galaxy.rails.values():
            if rail.from_system == route[0] and rail.to_system == route[1]:
                first_rail = rail
                break
        
        if not first_rail:
            return None
        
        # Get departures within flexibility window
        start_search = preferred_time - timedelta(days=flexibility_days)
        end_search = preferred_time + timedelta(days=flexibility_days)
        
        departures = self.get_next_departures(first_rail, start_search, 20)
        
        # Find departure closest to preferred time
        best_departure = None
        best_diff = float('inf')
        
        for departure in departures:
            if departure <= end_search:
                diff = abs((departure - preferred_time).total_seconds())
                if diff < best_diff:
                    best_diff = diff
                    best_departure = departure
        
        return best_departure
    
    def generate_bulk_schedule_report(self, galaxy: Galaxy, 
                                    start_date: datetime, duration_days: int = 30) -> Dict[str, Any]:
        """Generate comprehensive schedule report for the galaxy."""
        report = {
            'generation_date': datetime.now(),
            'schedule_period': f"{start_date.strftime('%Y-%m-%d')} to {(start_date + timedelta(days=duration_days)).strftime('%Y-%m-%d')}",
            'total_rails': len(galaxy.rails),
            'connected_systems': len(galaxy.connected_systems),
            'system_schedules': {},
            'route_statistics': {},
        }
        
        # Generate schedule for each connected system
        for system_id in galaxy.connected_systems:
            system_schedule = self.get_system_departures(galaxy, system_id, start_date, 50)
            connectivity_score = self.calculate_system_connectivity_score(galaxy, system_id)
            
            report['system_schedules'][system_id] = {
                'departures': system_schedule,
                'connectivity_score': connectivity_score,
                'total_departures': len(system_schedule),
            }
        
        # Calculate route statistics
        total_routes = 0
        total_journey_time = timedelta()
        
        for from_sys in galaxy.connected_systems:
            for to_sys in galaxy.connected_systems:
                if from_sys != to_sys:
                    journey_time = self.calculate_journey_time(galaxy, from_sys, to_sys, start_date)
                    if journey_time:
                        total_routes += 1
                        total_journey_time += journey_time
        
        if total_routes > 0:
            report['route_statistics'] = {
                'total_routes': total_routes,
                'average_journey_time_hours': total_journey_time.total_seconds() / 3600 / total_routes,
            }
        
        return report


class DefaultScheduleGenerator(ScheduleGenerator):
    """Default schedule generator implementation."""
    
    def __init__(self, seed: Optional[int] = None):
        super().__init__(seed)
        self.transit_time_hours = 1.0  # Near-instantaneous transit
        self.scheduling_buffer_hours = 0.5  # Buffer between connections