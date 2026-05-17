#!/usr/bin/env bash
#
# Parses the GitHub environment to set the DOC_VERSION and
# TARGET_DIR variables, ensuring release tags get a clean "v"
# prefix and test branches are safely sanitized.

set -euo pipefail

if [[ "${GITHUB_REF}" == "refs/heads/main" ]]; then
    echo "DOC_VERSION=latest" >> "$GITHUB_ENV"
    echo "TARGET_DIR=latest" >> "$GITHUB_ENV"

elif [[ "${GITHUB_REF}" == refs/tags/* ]]; then
    RAW_VERSION=${GITHUB_REF#refs/tags/}

    # Ensure the version strictly starts with 'v'
    # (This safely strips 'v' if it somehow already exists, then prepends it)
    VERSION="v${RAW_VERSION#v}"
    echo "DOC_VERSION=${VERSION}" >> "$GITHUB_ENV"
    echo "TARGET_DIR=${VERSION}" >> "$GITHUB_ENV"

else
    # Fallback for testing branches (e.g., refs/heads/test-feature)
    BRANCH_NAME=${GITHUB_REF#refs/heads/}
    # Sanitize branch name to be URL safe
    SAFE_BRANCH=$(echo "${BRANCH_NAME}" | tr -cd 'a-zA-Z0-9-')

    echo "DOC_VERSION=${SAFE_BRANCH}" >> "$GITHUB_ENV"
    echo "TARGET_DIR=${SAFE_BRANCH}" >> "$GITHUB_ENV"
fi
