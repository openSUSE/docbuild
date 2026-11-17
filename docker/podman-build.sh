#!/bin/sh
#
# Build the docbuild image with rootless Podman (no sudo).
# Uses the same docker/Dockerfile as build.sh.

set -eu

LOCAL_UID=$(id -u)
LOCAL_GID=$(id -g)
APP_HOME=${APP_HOME:-$HOME}

image=${1:-docbuild:leap160}
case $0 in
  */*) script_path=$0 ;;
  *)
    if [ -f "$0" ]; then
      script_path=$(pwd)/$0
    else
      script_path=$(command -v "$0")
    fi
    ;;
esac
script_dir=${script_path%/*}
script_dir=${script_dir:-/}
repo_root=$(CDPATH= cd -- "$script_dir/.." && pwd)

cd "$repo_root"

echo "Using
  APP_UID=${APP_UID:-$LOCAL_UID}
  APP_GID=${APP_GID:-$LOCAL_GID}
  APP_HOME=${APP_HOME}
"

podman build \
  -f docker/Dockerfile \
  --build-arg APP_UID="${APP_UID:-$LOCAL_UID}" \
  --build-arg APP_GID="${APP_GID:-$LOCAL_GID}" \
  --build-arg APP_HOME="${APP_HOME}" \
  -t "$image" \
  .

# keep-id maps the host UID to the same UID inside the container.
podman run --rm -it --userns=keep-id "$image" doctor
