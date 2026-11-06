#!/bin/bash
#
# Combines docbuild with all dependencies inside a Docker
# container image.

# use --network=host only for trusted containers.
ddocbuild() {
  local cpu_limit=${DDOCBUILD_CPUS:-$(nproc)}
  local APP_HOME="/home/docserv"
  local mounts=(
    --volume /var/cache/docbuild/:/var/cache/docbuild/
    --volume "${XDG_CONFIG_HOME:-$HOME/.config}/docbuild:${app_home}/.config/docbuild:ro"
    --volume "${XDG_CACHE_HOME:-$HOME/.cache}/docbuild:${app_home}/.cache/docbuild"
    --volume "${XDG_STATE_HOME:-$HOME/.local/state}/docbuild:${app_home}/.local/state/docbuild"
    --volume "$PWD:$PWD"
  )

  docker run --rm -it \
     --cpus="$cpu_limit" \
     --init \
     --network=host \
     "${mounts[@]}" \
     -w "$PWD" \
     docbuild:leap160 "$@"
}

# ddocbuild "$@"
