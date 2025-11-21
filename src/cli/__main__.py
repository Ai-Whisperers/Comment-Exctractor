"""Entry point for running the CLI as a module.

Usage:
    python -m src.cli extract personalpy facebook personalpy
    python -m src.cli export personalpy --format csv
    python -m src.cli stats personalpy
"""

from .main import main

if __name__ == "__main__":
    main()
