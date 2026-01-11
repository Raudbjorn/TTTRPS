#!/usr/bin/env python3
"""
Entry point for the mbed command
"""

import sys
from .cli import app

def main():
    """Main entry point"""
    try:
        app()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()