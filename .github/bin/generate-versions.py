#!/usr/bin/env python3
"""Generate version switcher JSON.

Scans the assembled deploy directory to dynamically
build the versions.json file, populating the version-switcher
dropdown menu for your end users.
"""

import argparse
from collections.abc import Iterable
import json
import os
from pathlib import Path
import re

#
BASE = (
    f"https://{os.environ.get('GITHUB_REPOSITORY_OWNER', '')}"
    f".github.io/"
    f"{os.environ.get('GITHUB_REPOSITORY', '').split('/')[-1]}"
)


def parsecli(cli: Iterable[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Generate version switcher JSON.")
    parser.add_argument(
        "-i",
        "--input",
        default=".versions.json",
        help="Input JSON file in the repository root (default: .versions.json)",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="versions.json",
        help="Output JSON filename inside the deploy directory (default: versions.json)",
    )
    parser.add_argument(
        "-k",
        "--keep",
        type=int,
        default=3,
        help="Number of semantic version tags to keep in the dropdown (default: 3)",
    )
    parser.add_argument(
        "-d",
        "--dry-run",
        action="store_true",
        help="Print the generated JSON to the console without writing to the file",
    )
    parser.add_argument(
        "--input-dir",
        default="deploy",
        type=Path,
        help="The input direcotry (default '%(default)s')",
    )
    args = parser.parse_args(cli)
    return args


def main() -> None:
    """Generate version switcher JSON."""
    args = parsecli()

    input_path = Path(args.input)
    deploy = Path(args.input_dir)
    output_path = deploy / args.output

    # 1. Read base versions from the input file if it exists
    versions = []
    if input_path.exists():
        try:
            versions = json.loads(input_path.read_text())
            print(f"Loaded base versions from {args.input}")
        except Exception as e:
            print(f"Warning: Could not parse {args.input}: {e}")

    # Track existing versions to prevent duplicating them
    existing_versions = {v.get("version") for v in versions if isinstance(v, dict)}

    # 2. Add Development/Stable if they exist and aren't in the input file
    if "latest" not in existing_versions and (deploy / "latest").exists():
        versions.append(
            {
                "name": "Development",
                "version": "latest",
                "url": f"{BASE}/latest/",
            }
        )

    if "stable" not in existing_versions and (deploy / "stable").exists():
        versions.append(
            {
                "name": "Stable",
                "version": "stable",
                "url": f"{BASE}/stable/",
            }
        )

    # 3. Find and sort strictly formatted semver tags (e.g. 1.0.0 or v0.18.0)
    tags = sorted(
        [
            p.name
            for p in deploy.iterdir()
            # Strict SemVer match: optional 'v' followed by exactly X.Y.Z
            if p.is_dir() and re.match(r"^v?\d+\.\d+\.\d+$", p.name)
        ],
        key=lambda s: [int(u) for u in re.findall(r"\d+", s)],
        reverse=True,
    )

    # 4. Append the top N semantic tags based on the --keep argument
    for tag in tags[: args.keep]:
        if tag not in existing_versions:
            versions.append(
                {
                    "name": tag,
                    "version": tag,
                    "url": f"{BASE}/{tag}/",
                }
            )

    # Ensure output directory exists and write final JSON
    if args.dry_run:
        print("--- DRY RUN ---")
        print(f"Would write the following {len(versions)} entries to {output_path}:")
        print(json.dumps(versions, indent=2))
    else:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(versions, indent=2))
        print(f"Generated {output_path} containing {len(versions)} version entries.")


if __name__ == "__main__":
    main()
