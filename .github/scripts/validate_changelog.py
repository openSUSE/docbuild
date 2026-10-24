#!/usr/bin/env python3
"""Validate towncrier newsfragment filenames against towncrier.toml types."""

import argparse
import pathlib
import re
import sys
import tomllib


def parse_cli(cliargs: list[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Validate towncrier newsfragments.")
    parser.add_argument(
        "files", nargs="+", type=pathlib.Path, help="List of newsfragment files to validate"
    )
    parser.add_argument(
        "-c",
        "--config",
        type=pathlib.Path,
        default=pathlib.Path("towncrier.toml"),
        help="Path to towncrier configuration file (default: towncrier.toml)",
    )
    return parser.parse_args(cliargs)


def extract_types_from_toml(config_path: pathlib.Path) -> list[str]:
    """Extract valid fragment types from the towncrier configuration."""
    with config_path.open("rb") as f:
        config = tomllib.load(f)
    return list(config["tool"]["towncrier"]["fragment"].keys())


def validate_newsfragment(files: list[pathlib.Path], valid_types: list[str]) -> bool:
    """Validate a list of files against the allowed types pattern."""
    types_pattern = "|".join(re.escape(t) for t in valid_types)

    # Regex:
    # 1. Digits (\d+) OR a plus sign followed by word characters/hyphens (\+[\w-]+)
    # 2. A literal dot followed by a valid type
    # 3. A literal .rst extension
    pattern = re.compile(rf"^(?:\d+|\+[\w-]+)\.({types_pattern})\.rst$")

    all_valid = True
    for file_path in files:
        filename = file_path.name
        if not pattern.match(filename):
            all_valid = False
            print(f"❌ Invalid newsfragment: {file_path}")
            print("   Expected format: '<number>.<type>.rst' or '+<description>.<type>.rst'")
            print(f"   Valid types: {', '.join(valid_types)}")
        else:
            print(f"✅ Valid newsfragment: {file_path}")

    return all_valid


def main(cliargs: list[str] | None = None) -> int:
    """Entry point for the application script.

    :param cliargs: Arguments to parse or None (=use :class:`sys.argv`)
    :return: error code
    """
    try:
        args = parse_cli(cliargs)
        valid_types = extract_types_from_toml(args.config)
        is_valid = validate_newsfragment(args.files, valid_types)

        if not is_valid:
            print(
                "::error title=Invalid Changelog Fragment::One or more newsfragment filenames "
                "are invalid. They must use digits (e.g. issue/PR number) or a '+description' prefix. "
                "Please check the logs.",
                file=sys.stderr
            )
            return 1

        return 0

    except FileNotFoundError as error:
        print(f"::error title=Missing Config::Configuration file not found: {error}", file=sys.stderr)
        return 2
    except KeyError as error:
        print(f"::error title=Invalid Config::Could not find expected keys in towncrier configuration: {error}", file=sys.stderr)
        return 3
    except tomllib.TOMLDecodeError as error:
        print(f"::error title=Invalid TOML::Failed to parse towncrier configuration: {error}", file=sys.stderr)
        return 4


if __name__ == "__main__":
    sys.exit(main())
