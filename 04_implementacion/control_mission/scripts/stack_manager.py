import os
import sys
import argparse
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parents[1]
ENV_FILE = BASE_DIR / ".env"

def update_env(key, value):
    if not ENV_FILE.exists():
        print(f"Error: {ENV_FILE} not found.")
        return
    
    lines = ENV_FILE.read_text().splitlines()
    new_lines = []
    found = False
    for line in lines:
        if line.startswith(f"{key}="):
            new_lines.append(f"{key}={value}")
            found = True
        else:
            new_lines.append(line)
    
    if not found:
        new_lines.append(f"{key}={value}")
    
    ENV_FILE.write_text("\n".join(new_lines) + "\n")

def set_mode(mode):
    if mode == "active":
        print("Setting Mode: ACTIVE (High Performance)")
        update_env("PLANNING_POLL_INTERVAL_MS", "2000")
        update_env("PLANNING_TIMEOUT_MS", "60000")
    elif mode == "eco":
        print("Setting Mode: ECO (Resource Efficient)")
        update_env("PLANNING_POLL_INTERVAL_MS", "15000")
        update_env("PLANNING_TIMEOUT_MS", "120000")
    else:
        print(f"Unknown mode: {mode}")
        return

    print("Mode updated in .env. Restart stack to apply: docker-compose restart mission-control")

def main():
    parser = argparse.ArgumentParser(description="Mission Control Stack Manager")
    subparsers = parser.add_subparsers(dest="command")
    
    mode_parser = subparsers.add_parser("mode", help="Switch between 'active' and 'eco' modes")
    mode_parser.add_argument("mode", choices=["active", "eco"])
    
    args = parser.parse_args()
    
    if args.command == "mode":
        set_mode(args.mode)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
