#!/usr/bin/env python3
"""Validate towncrier newsfragment filenames against towncrier.toml types."""

import argparse
import pathlib
import re
import sys
import tomllib


def main() -> None:
    """To validate towncrier newsfragment filenames."""
    parser = argparse.ArgumentParser(description="Validate towncrier newsfragments.")
    parser.add_argument(
        "files", nargs="+", type=pathlib.Path, help="List of newsfragment files to validate"
    )
    args = parser.parse_args()

    # Load valid types from towncrier.toml
    toml_path = pathlib.Path("towncrier.toml")
    if not toml_path.exists():
        print(f"::error title=Missing Config::Configuration file {toml_path} not found.")
        sys.exit(1)

    with toml_path.open("rb") as f:
        config = tomllib.load(f)

    try:
        valid_types = list(config["tool"]["towncrier"]["fragment"].keys())
    except KeyError:
        print("::error title=Invalid Config::Could not find [tool.towncrier.fragment] in towncrier.toml.")
        sys.exit(1)

    types_pattern = "|".join(re.escape(t) for t in valid_types)

    # Regex:
    # 1. Digits (\d+) OR a plus sign followed by word characters/hyphens (\+[\w-]+)
    # 2. A literal dot followed by a valid type
    # 3. A literal .rst extension
    pattern = re.compile(rf"^(?:\d+|\+[\w-]+)\.({types_pattern})\.rst$")

    all_valid = True
    for file_path in args.files:
        filename = file_path.name
        if not pattern.match(filename):
            all_valid = False
            print(f"❌ Invalid newsfragment: {file_path}")
            print("   Expected format: '<number>.<type>.rst' or '+<description>.<type>.rst'")
            print(f"   Valid types: {', '.join(valid_types)}")
        else:
            print(f"✅ Valid newsfragment: {file_path}")

    if not all_valid:
        print(
            "::error title=Invalid Changelog Fragment::One or more newsfragment filenames "
            "are invalid. They must use digits (e.g. issue/PR number) or a '+description' prefix. "
            "Please check the logs."
        )
        sys.exit(1)


if __name__ == "__main__":
    """Entry point for the script."""
    main()
