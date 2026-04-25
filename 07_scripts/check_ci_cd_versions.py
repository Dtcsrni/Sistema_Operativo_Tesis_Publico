#!/usr/bin/env python3
import sys
import re
from pathlib import Path

def check_ci_cd_versions():
    workflows_dir = Path(".github/workflows")
    if not workflows_dir.exists():
        return 0

    # Whitelist of valid stable versions
    allowed_versions = {
        "actions/checkout": "v4",
        "actions/setup-python": "v5",
        "actions/upload-artifact": "v4",
        "actions/configure-pages": "v4",
        "actions/upload-pages-artifact": "v3",
        "actions/deploy-pages": "v4"
    }

    errors = []

    # Regex to find uses: <action>@<version>
    pattern = re.compile(r"uses:\s+([^@]+)@([^\s]+)")

    for yaml_file in workflows_dir.glob("*.yml"):
        with open(yaml_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        for i, line in enumerate(lines, 1):
            match = pattern.search(line)
            if match:
                action = match.group(1).strip()
                version = match.group(2).strip()

                if action in allowed_versions:
                    expected = allowed_versions[action]
                    if version != expected:
                        errors.append(
                            f"{yaml_file.name}:{i}: Invalid version for {action}. "
                            f"Expected @{expected}, got @{version}"
                        )

    if errors:
        print("CI/CD Version check failed!")
        for error in errors:
            print(f"  - {error}")
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(check_ci_cd_versions())
