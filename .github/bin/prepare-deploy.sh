#!/usr/bin/env bash
#
# Assembles the deploy/ staging area by merging the newly built
# documentation with the existing historical docs, while also
# managing the stable symlink and root index.html redirect.

set -euo pipefail

mkdir -p deploy

echo "Cloning existing gh-pages branch..."

git clone \
    --depth 1 \
    --branch gh-pages \
    "https://github.com/${GITHUB_REPOSITORY}.git" \
    old-gh-pages || true

if [[ -d old-gh-pages ]]; then
    echo "Preserving existing documentation versions..."
    cp -r old-gh-pages/* deploy/ || true
fi

echo "Replacing current version: ${TARGET_DIR}"

rm -rf "deploy/${TARGET_DIR}"
mkdir -p "deploy/${TARGET_DIR}"

cp -r docs/build/html/* "deploy/${TARGET_DIR}/"

# stable -> latest tagged release
if [[ "${GITHUB_REF}" == refs/tags/* ]]; then
    echo "Updating stable alias..."

    # TARGET_DIR already contains the correctly formatted 'vX.Y.Z' string
    mkdir -p deploy && rm -rf deploy/stable && ln -s "${TARGET_DIR}" deploy/stable
fi

echo "Creating root redirect..."

cat > deploy/index.html <<EOF
<meta http-equiv="refresh" content="0; url=latest/">
EOF
