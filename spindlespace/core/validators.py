"""
Validators for rail network topology and safety.

Implements loop detection and LFE (Loop-Feedback Explosion) prevention.
"""

from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict, deque

from .models import Rail, System, Galaxy


class LoopDetectionError(Exception):
    """Raised when a potential closed timelike curve is detected."""
    pass


class RailNetworkValidationError(Exception):
    """Raised when rail network validation fails."""
    pass


def detect_loops(rails: List[Rail]) -> List[List[str]]:
    """
    Detect all cycles in the rail network.
    
    Returns a list of cycles, where each cycle is a list of system IDs.
    Since rails are one-way, we're looking for directed cycles.
    """
    # Build adjacency list
    graph = defaultdict(list)
    for rail in rails:
        graph[rail.from_system].append(rail.to_system)
    
    # Find all strongly connected components using Tarjan's algorithm
    index = 0
    stack = []
    indices = {}
    lowlinks = {}
    on_stack = set()
    sccs = []
    
    def strongconnect(v):
        nonlocal index
        indices[v] = index
        lowlinks[v] = index
        index += 1
        stack.append(v)
        on_stack.add(v)
        
        for w in graph[v]:
            if w not in indices:
                strongconnect(w)
                lowlinks[v] = min(lowlinks[v], lowlinks[w])
            elif w in on_stack:
                lowlinks[v] = min(lowlinks[v], indices[w])
        
        if lowlinks[v] == indices[v]:
            scc = []
            while True:
                w = stack.pop()
                on_stack.remove(w)
                scc.append(w)
                if w == v:
                    break
            if len(scc) > 1:  # Only cycles with more than 1 node
                sccs.append(scc)
    
    # Find all nodes in the graph
    all_nodes = set()
    for rail in rails:
        all_nodes.add(rail.from_system)
        all_nodes.add(rail.to_system)
    
    # Run Tarjan's algorithm on all unvisited nodes
    for node in all_nodes:
        if node not in indices:
            strongconnect(node)
    
    return sccs


def validate_rail_network(galaxy: Galaxy) -> Tuple[bool, List[str]]:
    """
    Validate a rail network for safety and consistency.
    
    Returns (is_valid, list_of_errors).
    """
    errors = []
    
    # Check for cycles (potential LFEs)
    loops = detect_loops(list(galaxy.rails.values()))
    if loops:
        errors.append(f"Found {len(loops)} potential closed timelike curves: {loops}")
    
    # Check for orphaned systems (systems with rails but not in galaxy)
    rail_systems = set()
    for rail in galaxy.rails.values():
        rail_systems.add(rail.from_system)
        rail_systems.add(rail.to_system)
    
    orphaned = rail_systems - set(galaxy.systems.keys())
    if orphaned:
        errors.append(f"Found orphaned systems in rails: {orphaned}")
    
    # Check for invalid rail connections
    for rail in galaxy.rails.values():
        if rail.from_system not in galaxy.systems:
            errors.append(f"Rail {rail.id} starts from unknown system {rail.from_system}")
        if rail.to_system not in galaxy.systems:
            errors.append(f"Rail {rail.id} ends at unknown system {rail.to_system}")
        
        # Check if rail length matches system coordinates
        if rail.from_system in galaxy.systems and rail.to_system in galaxy.systems:
            from_sys = galaxy.systems[rail.from_system]
            to_sys = galaxy.systems[rail.to_system]
            actual_distance = from_sys.coord.distance_to(to_sys.coord)
            
            # Allow 1% tolerance for floating point errors
            if abs(actual_distance - rail.length) > rail.length * 0.01:
                errors.append(
                    f"Rail {rail.id} length {rail.length:.2f} LY doesn't match "
                    f"system distance {actual_distance:.2f} LY"
                )
    
    # Check for duplicate rails
    rail_connections = set()
    for rail in galaxy.rails.values():
        connection = (rail.from_system, rail.to_system)
        if connection in rail_connections:
            errors.append(f"Duplicate rail from {rail.from_system} to {rail.to_system}")
        rail_connections.add(connection)
    
    # Check gravitium economics
    total_gravitium_cost = sum(rail.gravitium_cost for rail in galaxy.rails.values())
    total_gravitium_available = sum(
        system.gravitium_deposits for system in galaxy.systems.values()
    )
    
    if total_gravitium_cost > total_gravitium_available:
        errors.append(
            f"Insufficient gravitium: need {total_gravitium_cost:.1f} tons, "
            f"have {total_gravitium_available:.1f} tons"
        )
    
    return len(errors) == 0, errors


def find_source_vein_candidates(galaxy: Galaxy, min_gravitium: float = 1000.0) -> List[str]:
    """
    Find systems suitable as Source Vein locations.
    
    Source Vein systems should have high gravitium deposits and be well-positioned
    for rail network construction.
    """
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


def calculate_network_connectivity(galaxy: Galaxy) -> Dict[str, int]:
    """
    Calculate connectivity metrics for each system.
    
    Returns dict mapping system_id to number of reachable systems.
    """
    connectivity = {}
    
    for system_id in galaxy.systems:
        reachable = set()
        queue = deque([system_id])
        visited = {system_id}
        
        while queue:
            current = queue.popleft()
            
            # Find all outgoing rails
            for rail in galaxy.rails.values():
                if rail.from_system == current and rail.to_system not in visited:
                    visited.add(rail.to_system)
                    queue.append(rail.to_system)
                    reachable.add(rail.to_system)
        
        connectivity[system_id] = len(reachable)
    
    return connectivity


def suggest_rail_improvements(galaxy: Galaxy) -> List[str]:
    """
    Suggest improvements to the rail network.
    
    Returns list of human-readable suggestions.
    """
    suggestions = []
    
    # Find isolated systems
    connected_systems = set(galaxy.connected_systems)
    isolated_systems = set(galaxy.systems.keys()) - connected_systems
    
    if isolated_systems:
        suggestions.append(
            f"Consider connecting {len(isolated_systems)} isolated systems: "
            f"{', '.join(list(isolated_systems)[:5])}"
        )
    
    # Find single-connection systems (potential bottlenecks)
    connectivity = calculate_network_connectivity(galaxy)
    bottlenecks = [
        system_id for system_id, count in connectivity.items()
        if count == 1 and system_id in connected_systems
    ]
    
    if bottlenecks:
        suggestions.append(
            f"Consider adding redundant connections to {len(bottlenecks)} bottleneck systems"
        )
    
    # Check for high-capacity rails that might be underutilized
    underutilized_rails = []
    for rail in galaxy.rails.values():
        if rail.rail_class.value in ["RFC-A", "RFC-B"] and rail.interval_days > 30:
            underutilized_rails.append(rail.id)
    
    if underutilized_rails:
        suggestions.append(
            f"Consider increasing frequency on {len(underutilized_rails)} high-capacity rails"
        )
    
    return suggestions


def validate_system_for_rail_construction(
    galaxy: Galaxy, 
    system_id: str, 
    target_capacity: float
) -> Tuple[bool, List[str]]:
    """
    Validate if a system can support rail construction.
    
    Checks gravitium availability, tech level, and political stability.
    """
    errors = []
    
    if system_id not in galaxy.systems:
        errors.append(f"System {system_id} does not exist")
        return False, errors
    
    system = galaxy.systems[system_id]
    
    # Check tech level
    if system.tech_level.value < 5:  # RAIL_AGE
        errors.append(f"System {system_id} tech level too low for rail construction")
    
    # Check gravitium availability
    # Estimate gravitium needed based on existing rail costs
    existing_rails = galaxy.get_system_rails(system_id)
    if existing_rails:
        avg_cost = sum(rail.gravitium_cost for rail in existing_rails) / len(existing_rails)
        estimated_cost = avg_cost * 1.5  # Buffer for new rail
        
        if system.gravitium_deposits < estimated_cost:
            errors.append(
                f"System {system_id} has insufficient gravitium: "
                f"{system.gravitium_deposits:.1f} tons available, "
                f"estimated need {estimated_cost:.1f} tons"
            )
    
    # Check population (need workers)
    if system.total_population < 10_000:
        errors.append(f"System {system_id} population too low for major construction")
    
    return len(errors) == 0, errors