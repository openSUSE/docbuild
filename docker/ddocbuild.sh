#!/bin/bash

# use --network=host only for trusted containers.
ddocbuild() {
  local cpu_limit=${DDOCBUILD_CPUS:-$(nproc)}
  docker run --rm -it \
     --cpus="$cpu_limit" \
     --init \
     --network=host \
     -v "${XDG_CONFIG_HOME:-$HOME/.config}/docbuild:/home/app/.config/docbuild:ro" \
     -v "${XDG_CACHE_HOME:-$HOME/.cache}/docbuild:/home/app/.cache/docbuild" \
     -v "${XDG_STATE_HOME:-$HOME/.local/state}/docbuild:/home/app/.local/state/docbuild" \
     -v "$PWD:$PWD" \
     -w "$PWD" \
     docbuild:leap160 "$@"
}
