# Spindlespace Rail Network & World Generator

A procedural generator for the Spindlespace hard science fiction universe, creating coherent star systems, Krasnikov rail networks, and setting data for campaigns and stories.

## Overview

Spindlespace is a patch-work interstellar network linked by Krasnikov "rails"—one-way, mass-limited spacetime corridors built in straight lines by slow, century-long construction missions. This tool generates the infrastructure, politics, and worlds that make up this unique setting.

## Features

- **Procedural Star Systems**: Generate realistic star systems with planets, populations, and resources
- **Rail Network Generation**: Build minimum spanning tree rail networks with cycle detection
- **Loop-Feedback Explosion Prevention**: Validates networks to prevent closed timelike curves
- **Schedule Generation**: Create firing schedules and travel calendars for rail networks
- **Interactive CLI**: Command-line interface for generation, validation, and export
- **Multiple Export Formats**: JSON, YAML, and planned PDF booklet export
- **Extensible Plugin System**: Add custom generators and modifications

## Installation

```bash
# Install from source
git clone https://github.com/your-org/spindlespace.git
cd spindlespace
pip install -e .

# Or install from PyPI (when available)
pip install spindlespace
```

## Quick Start

### Generate a New Galaxy

```bash
# Create a new galaxy with 50 systems
spindle new "My Galaxy" --systems 50 --seed 12345

# Create a larger galaxy
spindle new "Sector Alpha" --systems 200 --radius 150 --seed 42
```

### Explore Your Galaxy

```bash
# Get basic information
spindle info "My Galaxy.spindle.json"

# List systems
spindle systems "My Galaxy.spindle.json" --filter connected

# Generate travel schedules
spindle schedule "My Galaxy.spindle.json" --from SYS-ABC123 --days 30

# Validate network integrity
spindle validate "My Galaxy.spindle.json"
```

### Export Data

```bash
# Export to different formats
spindle export "My Galaxy.spindle.json" --format yaml
spindle export "My Galaxy.spindle.json" --format pdf  # Coming soon
```

## Core Concepts

### Rail Classes

- **RFC-A**: 1M t/yr capacity (core-core routes)
- **RFC-B**: 50k t/mo capacity (regional routes)
- **RFC-C**: 5k t/day capacity (frontier routes)
- **RFC-D**: 500 t/day capacity (frontier routes)

### Gravitium Economy

Gravitium (Gv-490m) is the anchor material for rails and inertial dampeners. Found only in rare supernova-remnant deposits, every rail consumes its mass forever, making it the basis of interstellar currency.

### Network Topology

Rails are one-way and fire on fixed schedules. The generator ensures no closed timelike curves exist, preventing catastrophic Loop-Feedback Explosions (LFEs).

## API Usage

```python
from spindlespace import Galaxy, DefaultStarGenerator, DefaultRailGenerator
from spindlespace.core.models import Coordinate
from datetime import datetime

# Create generators
star_gen = DefaultStarGenerator(seed=12345)
rail_gen = DefaultRailGenerator(seed=12345)

# Generate star systems
coords = star_gen.generate_coordinates(50, radius=100.0)
systems = {}
for i, coord in enumerate(coords):
    system = star_gen.generate_system(coord, f"System {i+1}")
    systems[system.id] = system

# Create galaxy
galaxy = Galaxy(
    id="GAL-001",
    name="Test Galaxy",
    seed=12345,
    generation_time=datetime.now(),
    systems=systems,
    rails={},
    civilizations={},
    source_vein_systems=[]
)

# Generate rail network
rails = rail_gen.generate_rail_network(galaxy)
galaxy.rails = rails

# Validate network
from spindlespace.core.validators import validate_rail_network
is_valid, errors = validate_rail_network(galaxy)
print(f"Network valid: {is_valid}")
```

## Project Structure

```
spindlespace/
├── core/              # Core data models and validators
│   ├── models.py      # System, Planet, Rail, Galaxy classes
│   └── validators.py  # Loop detection and validation
├── generators/        # Procedural generators
│   ├── stargen.py     # Star system generation
│   ├── railgen.py     # Rail network construction
│   └── schedgen.py    # Schedule generation
├── io/               # Input/output utilities
│   └── loader.py     # JSON/YAML serialization
├── ui/               # User interfaces
│   └── cli.py        # Command-line interface
├── viz/              # Visualization (planned)
└── export/           # Export utilities (planned)
```

## Configuration

The tool uses deterministic generation based on seeds. All generation parameters can be customized:

```python
# Custom star generator
star_gen = DefaultStarGenerator(seed=42)
star_gen.gravitium_rarity = 0.1  # 10% chance instead of 5%

# Custom rail generator  
rail_gen = DefaultRailGenerator(seed=42)
rail_gen.redundancy_factor = 0.2  # More redundant connections
```

## Development

### Running Tests

```bash
pytest tests/
```

### Code Formatting

```bash
black spindlespace/
flake8 spindlespace/
```

### Type Checking

```bash
mypy spindlespace/
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## Roadmap

- [ ] 2D/3D visualization with matplotlib/plotly
- [ ] PDF export with system sheets and fold-out maps
- [ ] Textual TUI interface
- [ ] Web interface with Streamlit
- [ ] Plugin system for custom generators
- [ ] Real star catalog integration
- [ ] Foundry VTT integration

## License

MIT License - see LICENSE file for details.

## Background

Based on the Spindlespace hard science fiction setting, where infrastructure is destiny and time becomes tactical terrain. The universe features:

- **Asymmetric Development**: Colonies with medieval tech coexist beside hypercities
- **Metaphysical Themes**: AI civilizations choose transcendence over expansion
- **Strategic Resources**: Gravitium scarcity drives interstellar politics
- **Temporal Mechanics**: Relativistic lag and rail schedules create unique storytelling opportunities

Perfect for campaigns and stories exploring the intersection of hard science constraints with space opera scale.

## Support

- Documentation: [docs.spindlespace.dev](https://docs.spindlespace.dev)
- Issues: [GitHub Issues](https://github.com/your-org/spindlespace/issues)
- Discussions: [GitHub Discussions](https://github.com/your-org/spindlespace/discussions)