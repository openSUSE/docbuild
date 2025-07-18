#!/bin/bash
#
# Bumps the version number for the docbuild project.
#
# This script reads the version from src/docbuild/__about__.py,
# increments the specified part (major, minor, or patch), and
# writes the new version back to the file.

set -e # Exit immediately if a command exits with a non-zero status.
set -u # Treat unset variables as an error when substituting.
set -o pipefail # The return value of a pipeline is the status of the last command.

# --- Get script's directory to resolve paths reliably ---
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
PROJECT_ROOT=$(realpath "${SCRIPT_DIR}/..")

# --- Configuration ---
ABOUT_FILE="${PROJECT_ROOT}/src/docbuild/__about__.py"
old_version="" # Will be populated after reading the file

# --- Functions ---
function usage() {
  echo "Usage: $0 <major|minor|patch>"
  echo "Bumps the semantic version number for the project."
  if [ -n "${old_version}" ]; then
    echo "Current version: ${old_version}"
  fi
}

# --- Main Script ---

# 1. Check if the source file exists
if [ ! -f "${ABOUT_FILE}" ]; then
  echo "Error: Version file not found at '${ABOUT_FILE}'" >&2
  exit 1
fi

# 2. Read and parse the current version
current_version_line=$(grep "^__version__ = " "${ABOUT_FILE}")
if [ -z "${current_version_line}" ]; then
  echo "Error: Could not find a valid version string in ${ABOUT_FILE}" >&2
  echo "Expected format: __version__ = 'x.y.z' or __version__ = \"x.y.z\"" >&2
  exit 1
fi

# Extract the part after the '=' sign and strip whitespace
version_part=$(echo "${current_version_line}" | cut -d'=' -f2 | tr -d ' ')

# Preserve the quote character
quote_char=${version_part:0:1}

# Remove first and last character (quotes)
version_string=${version_part:1:-1}

# Validate the version string format
if ! [[ ${version_string} =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "Error: Parsed version '${version_string}' does not match expected x.y.z format." >&2
    exit 1
fi

# Split version into components
IFS='.' read -r major minor patch <<< "${version_string}"
old_version="${major}.${minor}.${patch}"

# 3. Validate input and determine new version
if [ "$#" -ne 1 ]; then
    usage
    echo -e "\nError: Please provide exactly one argument (major, minor, or patch)." >&2
    exit 1
fi

BUMP_PART=$1

case "${BUMP_PART}" in
  -h|--help)
    usage
    exit 0
    ;;
  major) major=$((major + 1)); minor=0; patch=0 ;;
  minor) minor=$((minor + 1)); patch=0 ;;
  patch) patch=$((patch + 1)) ;;
  *)
    usage
    echo -e "\nError: Invalid argument '${BUMP_PART}'." >&2
    exit 1
    ;;
esac

new_version="${major}.${minor}.${patch}"

# 4. Write the new version back to the file
message="Bumping version: ${old_version} → ${new_version}"
echo "${message}"
sed -i "s/__version__ = ${quote_char}${old_version}${quote_char}/__version__ = ${quote_char}${new_version}${quote_char}/" "${ABOUT_FILE}"

git commit -m "${message}" "${ABOUT_FILE}"

echo "Successfully updated ${ABOUT_FILE}"
