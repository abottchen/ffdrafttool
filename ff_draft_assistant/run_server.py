#!/usr/bin/env python3
"""
Startup script for the Fantasy Football Draft Assistant MCP Server
"""

import sys
import os
from pathlib import Path

# Add src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

# Change to src directory for imports
os.chdir(src_path)

if __name__ == "__main__":
    # Print startup messages to stderr to avoid interfering with MCP protocol
    print("Starting Fantasy Football Draft Assistant MCP Server...", file=sys.stderr)
    print(f"Working directory: {os.getcwd()}", file=sys.stderr)
    print(f"Python path: {sys.path[0]}", file=sys.stderr)
    print("Ready for MCP connection...", file=sys.stderr)
    print(file=sys.stderr)
    
    try:
        # Import here to ensure path is set up
        from server import main
        main()  # FastMCP uses sync, not async
    except KeyboardInterrupt:
        print("\nServer shutdown requested", file=sys.stderr)
    except Exception as e:
        print(f"Server error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)