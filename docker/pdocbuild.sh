#!/bin/bash
#
# Combines docbuild with all dependencies inside a rootless Podman
# container. Counterpart of ddocbuild.sh; build the image with podman-build.sh.

# use --network=host only for trusted containers.
pdocbuild() {
  local app_home=${APP_HOME:-$HOME}
  local config_dir="${XDG_CONFIG_HOME:-$HOME/.config}/docbuild"
  local cache_dir="${XDG_CACHE_HOME:-$HOME/.cache}/docbuild"
  local state_dir="${XDG_STATE_HOME:-$HOME/.local/state}/docbuild"
  local image=${DOCBUILD_IMAGE:-docbuild:leap160}

  # Podman, unlike Docker, does not create missing bind-mount sources.
  mkdir -p "$config_dir" "$cache_dir" "$state_dir"

  local mounts=(
    --volume "$config_dir:${app_home}/.config/docbuild:ro"
    --volume "$cache_dir:${app_home}/.cache/docbuild"
    --volume "$state_dir:${app_home}/.local/state/docbuild"
    --volume "$PWD:$PWD"
  )
  [[ -d /var/cache/docbuild ]] && mounts+=(--volume /var/cache/docbuild/:/var/cache/docbuild/)

  # --cpus needs cgroup v2 CPU delegation for rootless users, so it is opt-in.
  local opts=()
  [[ -n ${DDOCBUILD_CPUS:-} ]] && opts+=(--cpus="$DDOCBUILD_CPUS")

  podman run --rm -it \
     --userns=keep-id \
     --init \
     --network=host \
     "${opts[@]}" \
     "${mounts[@]}" \
     -w "$PWD" \
     "$image" "$@"
}

# pdocbuild "$@"
