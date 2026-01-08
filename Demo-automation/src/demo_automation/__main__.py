"""
Allow running the package as a module: python -m demo_automation

Usage:
    python -m demo_automation setup ./MyDemo
    python -m demo_automation validate ./MyDemo
    python -m demo_automation --help
"""

from .cli import main

if __name__ == "__main__":
    main()
