"""
Command-line interface for Spindlespace generator.

Provides the main 'spindle' command with subcommands for generating,
editing, and exporting galaxy data.
"""

import typer
import json
import yaml
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel

from ..core.models import Galaxy, Coordinate, generate_system_id
from ..generators.stargen import DefaultStarGenerator
from ..generators.railgen import DefaultRailGenerator
from ..generators.schedgen import DefaultScheduleGenerator
from ..core.validators import validate_rail_network, detect_loops
from ..io.loader import GalaxyLoader


# Initialize Typer app and Rich console
app = typer.Typer(
    name="spindle",
    help="Spindlespace rail network and world generator",
    add_completion=False,
)
console = Console()


@app.command()
def new(
    name: str = typer.Argument(help="Name of the galaxy project"),
    seed: Optional[int] = typer.Option(None, "--seed", "-s", help="Random seed for generation"),
    systems: int = typer.Option(50, "--systems", "-n", help="Number of star systems to generate"),
    radius: float = typer.Option(100.0, "--radius", "-r", help="Galaxy radius in light-years"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path"),
):
    """Create a new galaxy project."""
    if seed is None:
        seed = int(datetime.now().timestamp())
    
    output_path = Path(output) if output else Path(f"{name}.spindle.json")
    
    console.print(f"[bold green]Creating new galaxy: {name}[/bold green]")
    console.print(f"Seed: {seed}")
    console.print(f"Systems: {systems}")
    console.print(f"Radius: {radius} LY")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        # Generate star systems
        task = progress.add_task("Generating star systems...", total=None)
        
        star_gen = DefaultStarGenerator(seed)
        coordinates = star_gen.generate_coordinates(systems, radius)
        
        galaxy_systems = {}
        for i, coord in enumerate(coordinates):
            system = star_gen.generate_system(coord, f"System {i+1:03d}")
            galaxy_systems[system.id] = system
        
        progress.update(task, description="Generating rail network...")
        
        # Create galaxy
        galaxy = Galaxy(
            id=generate_system_id(),
            name=name,
            seed=seed,
            generation_time=datetime.now(),
            systems=galaxy_systems,
            rails={},
            civilizations={},
            source_vein_systems=[]
        )
        
        # Generate rail network
        rail_gen = DefaultRailGenerator(seed)
        rails = rail_gen.generate_rail_network(galaxy)
        
        # Update galaxy with rails
        galaxy = Galaxy(
            id=galaxy.id,
            name=galaxy.name,
            seed=galaxy.seed,
            generation_time=galaxy.generation_time,
            systems=galaxy.systems,
            rails=rails,
            civilizations=galaxy.civilizations,
            source_vein_systems=rail_gen.find_source_vein_systems(galaxy)
        )
        
        progress.update(task, description="Validating network...")
        
        # Validate the network
        is_valid, errors = validate_rail_network(galaxy)
        if not is_valid:
            console.print("[bold red]Validation errors:[/bold red]")
            for error in errors:
                console.print(f"  - {error}")
        
        progress.update(task, description="Saving galaxy...")
        
        # Save galaxy
        loader = GalaxyLoader()
        loader.save_galaxy(galaxy, output_path)
    
    console.print(f"[bold green]Galaxy created successfully![/bold green]")
    console.print(f"Output: {output_path}")
    
    # Print statistics
    stats_table = Table(title="Galaxy Statistics")
    stats_table.add_column("Metric", style="cyan")
    stats_table.add_column("Value", style="magenta")
    
    stats_table.add_row("Total Systems", str(len(galaxy.systems)))
    stats_table.add_row("Connected Systems", str(len(galaxy.connected_systems)))
    stats_table.add_row("Total Rails", str(len(galaxy.rails)))
    stats_table.add_row("Source Vein Systems", str(len(galaxy.source_vein_systems)))
    stats_table.add_row("Total Population", f"{galaxy.total_population:,}")
    
    console.print(stats_table)


@app.command()
def info(
    project_file: str = typer.Argument(help="Path to galaxy project file"),
):
    """Display information about a galaxy project."""
    project_path = Path(project_file)
    
    if not project_path.exists():
        console.print(f"[bold red]Error: File {project_file} not found[/bold red]")
        raise typer.Exit(1)
    
    try:
        loader = GalaxyLoader()
        galaxy = loader.load_galaxy(project_path)
        
        # Display basic info
        console.print(Panel(f"[bold]{galaxy.name}[/bold]", title="Galaxy Information"))
        
        info_table = Table()
        info_table.add_column("Property", style="cyan")
        info_table.add_column("Value", style="magenta")
        
        info_table.add_row("ID", galaxy.id)
        info_table.add_row("Seed", str(galaxy.seed))
        info_table.add_row("Generated", galaxy.generation_time.strftime("%Y-%m-%d %H:%M:%S"))
        info_table.add_row("Total Systems", str(len(galaxy.systems)))
        info_table.add_row("Connected Systems", str(len(galaxy.connected_systems)))
        info_table.add_row("Total Rails", str(len(galaxy.rails)))
        info_table.add_row("Total Population", f"{galaxy.total_population:,}")
        
        console.print(info_table)
        
        # Rail network statistics
        rail_gen = DefaultRailGenerator()
        stats = rail_gen.get_network_statistics(galaxy)
        
        rail_table = Table(title="Rail Network Statistics")
        rail_table.add_column("Metric", style="cyan")
        rail_table.add_column("Value", style="magenta")
        
        rail_table.add_row("Coverage", f"{stats['coverage_percentage']:.1f}%")
        rail_table.add_row("Total Gravitium Cost", f"{stats['total_gravitium_cost']:,.0f} tons")
        rail_table.add_row("Average Length", f"{stats['average_length']:.1f} LY")
        rail_table.add_row("Average Interval", f"{stats['average_interval']:.1f} days")
        
        console.print(rail_table)
        
        # Rail classes
        if stats['rail_classes']:
            class_table = Table(title="Rail Classes")
            class_table.add_column("Class", style="cyan")
            class_table.add_column("Count", style="magenta")
            
            for rail_class, count in stats['rail_classes'].items():
                class_table.add_row(rail_class.value, str(count))
            
            console.print(class_table)
        
        # Validation
        is_valid, errors = validate_rail_network(galaxy)
        if is_valid:
            console.print("[bold green]✓ Network validation passed[/bold green]")
        else:
            console.print("[bold red]✗ Network validation failed[/bold red]")
            for error in errors:
                console.print(f"  - {error}")
        
    except Exception as e:
        console.print(f"[bold red]Error loading galaxy: {e}[/bold red]")
        raise typer.Exit(1)


@app.command()
def validate(
    project_file: str = typer.Argument(help="Path to galaxy project file"),
):
    """Validate a galaxy project for loops and consistency."""
    project_path = Path(project_file)
    
    if not project_path.exists():
        console.print(f"[bold red]Error: File {project_file} not found[/bold red]")
        raise typer.Exit(1)
    
    try:
        loader = GalaxyLoader()
        galaxy = loader.load_galaxy(project_path)
        
        console.print(f"[bold]Validating {galaxy.name}[/bold]")
        
        # Run validation
        is_valid, errors = validate_rail_network(galaxy)
        
        if is_valid:
            console.print("[bold green]✓ All validations passed![/bold green]")
        else:
            console.print("[bold red]✗ Validation failed[/bold red]")
            console.print("\n[bold]Errors found:[/bold]")
            for error in errors:
                console.print(f"  - {error}")
        
        # Check for loops specifically
        loops = detect_loops(list(galaxy.rails.values()))
        if loops:
            console.print(f"\n[bold yellow]⚠ Found {len(loops)} potential closed timelike curves:[/bold yellow]")
            for i, loop in enumerate(loops):
                console.print(f"  Loop {i+1}: {' → '.join(loop)}")
        
    except Exception as e:
        console.print(f"[bold red]Error validating galaxy: {e}[/bold red]")
        raise typer.Exit(1)


@app.command()
def schedule(
    project_file: str = typer.Argument(help="Path to galaxy project file"),
    from_system: Optional[str] = typer.Option(None, "--from", "-f", help="Starting system ID"),
    days: int = typer.Option(30, "--days", "-d", help="Number of days to generate schedule"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file for schedule"),
):
    """Generate travel schedules for a galaxy."""
    project_path = Path(project_file)
    
    if not project_path.exists():
        console.print(f"[bold red]Error: File {project_file} not found[/bold red]")
        raise typer.Exit(1)
    
    try:
        loader = GalaxyLoader()
        galaxy = loader.load_galaxy(project_path)
        
        console.print(f"[bold]Generating schedules for {galaxy.name}[/bold]")
        
        sched_gen = DefaultScheduleGenerator()
        start_date = datetime(3000, 1, 1)  # Future date
        
        if from_system:
            # Generate schedule for specific system
            if from_system not in galaxy.systems:
                console.print(f"[bold red]Error: System {from_system} not found[/bold red]")
                raise typer.Exit(1)
            
            departures = sched_gen.get_system_departures(galaxy, from_system, start_date, days * 2)
            
            if departures:
                dep_table = Table(title=f"Departures from {from_system}")
                dep_table.add_column("Date", style="cyan")
                dep_table.add_column("To System", style="magenta")
                
                for from_sys, dep_time, to_sys in departures:
                    dep_table.add_row(
                        dep_time.strftime("%Y-%m-%d %H:%M"),
                        to_sys
                    )
                
                console.print(dep_table)
            else:
                console.print(f"[bold yellow]No departures found from {from_system}[/bold yellow]")
        
        else:
            # Generate full galaxy schedule report
            report = sched_gen.generate_bulk_schedule_report(galaxy, start_date, days)
            
            if output:
                with open(output, 'w') as f:
                    json.dump(report, f, indent=2, default=str)
                console.print(f"[bold green]Schedule report saved to {output}[/bold green]")
            else:
                console.print(f"[bold]Schedule Report[/bold]")
                console.print(f"Period: {report['schedule_period']}")
                console.print(f"Total Rails: {report['total_rails']}")
                console.print(f"Connected Systems: {report['connected_systems']}")
                
                if 'route_statistics' in report:
                    route_stats = report['route_statistics']
                    console.print(f"Total Routes: {route_stats['total_routes']}")
                    console.print(f"Average Journey Time: {route_stats['average_journey_time_hours']:.1f} hours")
    
    except Exception as e:
        console.print(f"[bold red]Error generating schedule: {e}[/bold red]")
        raise typer.Exit(1)


@app.command()
def export(
    project_file: str = typer.Argument(help="Path to galaxy project file"),
    format: str = typer.Option("json", "--format", "-f", help="Export format (json, yaml, pdf)"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path"),
):
    """Export galaxy data in various formats."""
    project_path = Path(project_file)
    
    if not project_path.exists():
        console.print(f"[bold red]Error: File {project_file} not found[/bold red]")
        raise typer.Exit(1)
    
    try:
        loader = GalaxyLoader()
        galaxy = loader.load_galaxy(project_path)
        
        if output is None:
            output = f"{galaxy.name}.{format.lower()}"
        
        console.print(f"[bold]Exporting {galaxy.name} to {format.upper()}[/bold]")
        
        if format.lower() == "json":
            loader.save_galaxy(galaxy, Path(output))
            console.print(f"[bold green]Exported to {output}[/bold green]")
        
        elif format.lower() == "yaml":
            galaxy_dict = loader.galaxy_to_dict(galaxy)
            with open(output, 'w') as f:
                yaml.dump(galaxy_dict, f, default_flow_style=False, sort_keys=False)
            console.print(f"[bold green]Exported to {output}[/bold green]")
        
        elif format.lower() == "pdf":
            console.print("[bold yellow]PDF export not yet implemented[/bold yellow]")
            # TODO: Implement PDF export
        
        else:
            console.print(f"[bold red]Error: Unknown format '{format}'[/bold red]")
            raise typer.Exit(1)
    
    except Exception as e:
        console.print(f"[bold red]Error exporting galaxy: {e}[/bold red]")
        raise typer.Exit(1)


@app.command()
def systems(
    project_file: str = typer.Argument(help="Path to galaxy project file"),
    filter_by: Optional[str] = typer.Option(None, "--filter", "-f", help="Filter systems by property"),
    limit: int = typer.Option(20, "--limit", "-l", help="Limit number of systems shown"),
):
    """List systems in a galaxy."""
    project_path = Path(project_file)
    
    if not project_path.exists():
        console.print(f"[bold red]Error: File {project_file} not found[/bold red]")
        raise typer.Exit(1)
    
    try:
        loader = GalaxyLoader()
        galaxy = loader.load_galaxy(project_path)
        
        systems = list(galaxy.systems.values())
        
        # Apply filters
        if filter_by:
            if filter_by == "connected":
                systems = [s for s in systems if s.id in galaxy.connected_systems]
            elif filter_by == "isolated":
                systems = [s for s in systems if s.id not in galaxy.connected_systems]
            elif filter_by == "gravitium":
                systems = [s for s in systems if s.gravitium_deposits > 0]
            elif filter_by == "populated":
                systems = [s for s in systems if s.total_population > 0]
        
        # Sort by population
        systems.sort(key=lambda s: s.total_population, reverse=True)
        
        # Limit results
        systems = systems[:limit]
        
        # Display table
        table = Table(title=f"Systems in {galaxy.name}")
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="magenta")
        table.add_column("Star Type", style="yellow")
        table.add_column("Population", style="green")
        table.add_column("Tech Level", style="blue")
        table.add_column("Gravitium", style="red")
        
        for system in systems:
            table.add_row(
                system.id,
                system.name,
                system.star_type.value,
                f"{system.total_population:,}",
                system.tech_level.name,
                f"{system.gravitium_deposits:.1f}" if system.gravitium_deposits > 0 else "-"
            )
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[bold red]Error listing systems: {e}[/bold red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()