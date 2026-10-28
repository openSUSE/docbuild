#!/bin/sh

set -eu

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

DOCKER_BUILDKIT=1 docker build \
  -f docker/Dockerfile \
  --build-arg APP_UID="$(id -u)" \
  --build-arg APP_GID="$(id -g)" \
  --build-arg APP_HOME="${HOME:?must be set}" \
  -t "$image" \
  .

docker run --rm -it "$image" doctor
