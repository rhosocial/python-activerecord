#!/usr/bin/env python3
# build_script.py
"""Build script for different packaging modes.

Usage:
    python build_script.py [mode]
    
Modes:
    default - Only source code and essential files (default)
    test    - Include test package for dependent packages
    docs    - Include documentation files
    dev     - Include everything for development
    all     - Build all modes

Examples:
    python build_script.py default
    python build_script.py test
    HATCH_BUILD_MODE=test python -m build
"""

import os
import subprocess
import sys
from pathlib import Path


def run_command(cmd: list, env_vars: dict = None) -> int:
    """Run a command with optional environment variables."""
    env = os.environ.copy()
    if env_vars:
        env.update(env_vars)
    
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, env=env)
    return result.returncode


def clean_dist():
    """Clean the dist directory."""
    dist_dir = Path("dist")
    if dist_dir.exists():
        import shutil
        shutil.rmtree(dist_dir)
        print("Cleaned dist directory")


def build_mode(mode: str) -> int:
    """Build package for specific mode."""
    print(f"\n=== Building {mode} mode ===")
    
    # Set environment variable for build mode
    env_vars = {'HATCH_BUILD_MODE': mode}
    
    # Build both wheel and source distribution
    build_cmd = ["python", "-m", "build"]
    if run_command(build_cmd, env_vars) != 0:
        print(f"Failed to build {mode} mode")
        return 1
    
    print(f"Successfully built {mode} mode")
    return 0


def main():
    """Main function."""
    if len(sys.argv) > 1:
        mode = sys.argv[1]
    else:
        mode = "default"
    
    # Handle help option
    if mode in ["-h", "--help", "help"]:
        print(__doc__)
        return 0
    
    valid_modes = ["default", "test", "docs", "dev", "all"]
    
    if mode not in valid_modes:
        print(f"Invalid mode: {mode}")
        print(f"Valid modes: {', '.join(valid_modes)}")
        print("Use --help for more information.")
        return 1
    
    # Check if build module is available
    try:
        import build
    except ImportError:
        print("Error: 'build' module not found. Install it with: pip install build")
        return 1
    
    # Clean previous builds
    clean_dist()
    
    if mode == "all":
        # Build all modes
        for build_mode_name in ["default", "test", "docs", "dev"]:
            if build_mode(build_mode_name) != 0:
                return 1
    else:
        # Build specific mode
        if build_mode(mode) != 0:
            return 1
    
    print("\n=== Build completed successfully ===")
    print("\nBuilt packages:")
    dist_dir = Path("dist")
    if dist_dir.exists():
        for file in sorted(dist_dir.iterdir()):
            print(f"  {file.name}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())