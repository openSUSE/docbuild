"""TOML to reStructuredText (RST) Documentation Generator.

This script parses a TOML configuration file and generates a structured RST reference
suitable for Sphinx documentation. It uses a hybrid parsing approach:
1. Manual line-by-line parsing to extract structured comments and metadata.
2. tomllib (or tomli) to resolve actual default values.

Supported Comment Syntax:

    Section Documentation:
        Comments immediately following a [section] header are treated as the
        section's introductory description. reStructuredText formatting (like lists)
        is preserved.

        [my-section]
        # This is the section description.
        # It can span multiple lines and include:
        #
        # * Bullet points
        # * **Bold text**

    Key Documentation:
        Comments immediately preceding a key-value pair define that key's metadata.
        The first line should follow the `key(type): description` pattern.
        Subsequent lines are appended to the description.

        # timeout(int): The maximum time to wait in seconds.
        # Use 0 for infinite timeout.
        timeout = 30

Key Features:
- Supports bracketed section headers and complex keys (dots/dashes).
- Extracts data types and multi-line descriptions from comments.
- Preserves comment structure (lists, indentation) for valid RST rendering.
- Generates a vertical "definition-style" layout.
- Configurable unique anchors for linking (e.g., :ref:`envtoml-section-key`).
- Prevents duplicate Sphinx labels within a single run.
- CLI with adjustable verbosity and label configuration.
"""

import argparse
from dataclasses import dataclass, field
import logging
from pathlib import Path
import re
import sys
import tomllib
from typing import Any

logger = logging.getLogger(__name__)

# --- Regex patterns for TOML parsing ---

# This pattern defines a single TOML key part, which can be a bare key (unquoted),
# a double-quoted key, or a single-quoted key. This is the building block for
# more complex dotted keys.
KEY_PART_PATTERN = r"""[A-Za-z0-9_-]+|"(?:\\.|[^"\\])*"|'[^']*'"""

# This verbose regex pattern matches a full TOML key (bare, quoted, or dotted).
# A TOML key is composed of one or more "key parts" separated by dots.
DOTTED_KEY_PATTERN = fr"""
    # --- Definition of the first key part ---
    (?:{KEY_PART_PATTERN})

    # --- Optional subsequent, dot-separated parts ---
    (?:                     # A non-capturing group for the rest of the dotted key.
        \s*\.\s*            # A dot separator, surrounded by optional whitespace.

        # The pattern for any subsequent key part is the same as the first.
        (?:{KEY_PART_PATTERN})
    )*                      # This group of subsequent parts can appear zero or more times.
"""

COMMENT_METADATA_REGEX = re.compile(
    fr"""
        ^\s*[#]\s*                                # Leading whitespace and comment marker
        (?P<key>{DOTTED_KEY_PATTERN})           # The full TOML key (captured)
        \((?P<type>[^)]+)\)                     # The type in parentheses (captured)
        :\s*                                    # Colon and optional whitespace
        (?P<description>.*)$                    # The rest of the line is the description (captured)
    """,
    re.VERBOSE,
)
TOML_KEY_VALUE_REGEX = re.compile(
    fr"""
        ^\s*                                    # Leading whitespace
        (?P<key>{DOTTED_KEY_PATTERN})          # The full TOML key (captured)
        \s*=\s*.*$                              # Equals sign, optional whitespace, and the rest of the line
    """,
    re.VERBOSE,
)
TOML_SECTION_REGEX = re.compile(
    fr"""
        ^\s*\[                                  # Leading whitespace and opening bracket
        (?P<name>{DOTTED_KEY_PATTERN})         # The full TOML key as the section name (captured)
        \]\s*$                                  # Closing bracket and optional trailing whitespace
    """,
    re.VERBOSE,
)


@dataclass
class ConfigEntry:
    """Represent a single configuration entry within a TOML section."""

    # The configuration key name.
    key: str
    # The expected data type (extracted from comments).
    data_type: str
    # A list of description lines preceding the key.
    description: list[str]
    # The actual value resolved from the TOML file.
    default_value: str


@dataclass
class ConfigSection:
    """Represent a TOML section containing multiple configuration entries."""

    # The name of the section (e.g., 'server').
    name: str
    # Introductory text for the section.
    description: list[str] = field(default_factory=list)
    # A list of ConfigEntry objects belonging to this section.
    entries: list[ConfigEntry] = field(default_factory=list)


def get_default_value(raw_data: dict[str, Any], section_name: str, key: str) -> str:
    """Safely retrieves a default value from the parsed TOML dictionary."""
    try:
        val = raw_data
        for part in section_name.split("."):
            val = val[part]
        default_val = val[key]
        # Format booleans as lowercase strings (true/false) to match TOML/JSON standard
        return (
            str(default_val).lower()
            if isinstance(default_val, bool)
            else str(default_val)
        )
    except (KeyError, TypeError):
        return "n/a"


def extract_metadata(buffer: list[str]) -> tuple[str, list[str]]:
    """Extract data type and clean description from a comment buffer."""
    v_type = "unknown"
    v_desc = []
    for line in buffer:
        if meta := COMMENT_METADATA_REGEX.match(line):
            v_type = meta.group("type")
            if desc_text := meta.group("description"):
                v_desc.append(desc_text.strip())
        else:
            v_desc.append(line.strip("# ").rstrip())
    return v_type, v_desc


def split_buffer_for_section(buffer: list[str]) -> tuple[list[str], list[str]]:
    """Split buffer into section description and key metadata."""
    desc, remaining = [], []
    for line in buffer:
        if not COMMENT_METADATA_REGEX.match(line) and not remaining:
            desc.append(line.strip("# ").rstrip())
        else:
            remaining.append(line)
    return desc, remaining


def parse_toml_contents(
    toml_path: Path, raw_toml_data: dict[str, Any]
) -> list[ConfigSection]:
    """Parse the TOML file line-by-line to extract sections and entries."""
    lines = toml_path.read_text(encoding="utf-8").splitlines()
    sections: list[ConfigSection] = []

    current_section: ConfigSection | None = None
    comment_buffer: list[str] = []
    waiting_for_first_key = False

    for line in lines:
        clean = line.strip()

        # 1. Handle Section Headers
        if section_match := TOML_SECTION_REGEX.match(clean):
            current_section = ConfigSection(name=section_match.group("name"))
            sections.append(current_section)
            comment_buffer, waiting_for_first_key = [], True
            continue

        # 2. Handle Comments
        if clean.startswith("#"):
            comment_buffer.append(clean)
            continue

        # 3. Handle Key-Value Pairs
        if (kv_match := TOML_KEY_VALUE_REGEX.match(clean)) and current_section:
            key = kv_match.group("key")

            if waiting_for_first_key:
                current_section.description, comment_buffer = split_buffer_for_section(
                    comment_buffer
                )
                waiting_for_first_key = False

            v_type, v_desc = extract_metadata(comment_buffer)

            current_section.entries.append(
                ConfigEntry(
                    key=key,
                    data_type=v_type,
                    description=v_desc,
                    default_value=get_default_value(
                        raw_toml_data, current_section.name, key
                    ),
                )
            )
            comment_buffer = []
            continue

        # 4. Handle Gaps
        if not clean and not waiting_for_first_key:
            comment_buffer = []

    return sections


def get_unique_label(base: str, generated_labels: set[str]) -> str:
    """Normalize a string into a unique Sphinx label."""
    label = base.lower().replace(".", "-").replace("_", "-")
    if label not in generated_labels:
        generated_labels.add(label)
        return label

    counter = 1
    while f"{label}-{counter}" in generated_labels:
        counter += 1

    final_label = f"{label}-{counter}"
    generated_labels.add(final_label)
    return final_label


def render_rst(sections: list[ConfigSection], use_labels: bool, prefix: str) -> str:
    """Convert a list of ConfigSection objects into a valid RST string."""
    generated_labels: set[str] = set()
    rst = [
        ":orphan:",
        "",
        ".. note:: This page is automatically generated from the project's",
        "  TOML configuration. DO NOT EDIT this file directly.",
        "",
        ".. -text-begin-",
        "",
    ]

    for section in sections:
        if use_labels:
            lbl = get_unique_label(f"{prefix}-section-{section.name}", generated_labels)
            rst.extend([f".. _{lbl}:", ""])

        header = f"[{section.name}]"
        rst.extend([header, "-" * len(header), ""])

        if section.description:
            rst.extend([*section.description, ""])

        for entry in section.entries:
            if use_labels:
                lbl = get_unique_label(
                    f"{prefix}-{section.name}-{entry.key}", generated_labels
                )
                rst.extend([f".. _{lbl}:", ""])

            rst.append(f"``{entry.key}``")
            rst.append(
                f"    :Type: :code:`{v_type}`"
                if (v_type := entry.data_type)
                else "    :Type: unknown"
            )
            rst.append(f"    :Default: ``{entry.default_value}``")
            rst.append("")
            # Indent multi-line description text
            rst.extend([f"    {line}" for line in entry.description])
            rst.append("")

    return "\n".join(rst)


def generate_toml_reference(
    toml_input_path: Path,
    rst_output_path: Path,
    use_labels: bool = True,
    prefix: str = "envtoml",
) -> None:
    """Coordinate parsing and rendering (main entry point)."""
    # 1. Load TOML structure for default values
    with open(toml_input_path, "rb") as f:
        raw_toml_data = tomllib.load(f)

    # 2. Parse source file for comments and sections
    sections = parse_toml_contents(toml_input_path, raw_toml_data)

    # 3. Render and write output
    rst_string = render_rst(sections, use_labels, prefix)
    rst_output_path.write_text(rst_string, encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate RST documentation from TOML."
    )
    parser.add_argument("input", type=Path, help="Input TOML file")
    parser.add_argument("output", type=Path, help="Output RST file")
    parser.add_argument(
        "--labels",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Generate unique Sphinx labels (default: %(default)s)",
    )
    parser.add_argument(
        "--prefix",
        default="envtoml",
        help="Prefix for generated labels (default: '%(default)s')",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    try:
        generate_toml_reference(
            args.input, args.output, use_labels=args.labels, prefix=args.prefix
        )
    except Exception as e:
        logger.error(f"Failed to generate documentation: {e}")
        sys.exit(1)
