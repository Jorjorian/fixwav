"""
Entry point for running spindlespace as a module.

Allows running 'python -m spindlespace' to access the CLI.
"""

from .ui.cli import app

if __name__ == "__main__":
    app()