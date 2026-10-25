# syntax=docker/dockerfile:1
#
# Build with Docker or Podman:
#   docker build -f docker/Dockerfile -t docbuild:leap16 .
#   podman build -f docker/Dockerfile -t docbuild:leap16 .
# Match host ownership for bind mounts with rootful Docker (without userns remapping):
#   docker build -f docker/Dockerfile --build-arg APP_UID="$(id -u)" --build-arg APP_GID="$(id -g)" -t docbuild:local .
# Run a dependency check:
#   podman run --rm docbuild:leap16 doctor
#
# Reuse host configuration, cache, and state with rootless Podman:
#   mkdir -p "$HOME/.config/docbuild" "$HOME/.cache/docbuild" "$HOME/.local/state/docbuild"
#   podman run --rm \
#     --userns=keep-id:uid=1000,gid=1000 \
#     -v "$HOME/.config/docbuild:/home/app/.config/docbuild:ro,Z" \
#     -v "$HOME/.cache/docbuild:/home/app/.cache/docbuild:Z" \
#     -v "$HOME/.local/state/docbuild:/home/app/.local/state/docbuild:Z" \
#     docbuild:leap16 config list --flat --env
# keep-id maps the host user to app (UID/GID 1000) without changing host ownership.
# :Z applies a private SELinux label; use :z for directories shared by containers.
# The host shell expands $HOME; container paths must match the image's HOME (/home/app).


ARG OPENSUSE_VERSION=16.0
ARG UV_VERSION=0.13.5

# Pin the build tool in its own stage; it is not included in the runtime.
FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv

# ------- Stage 1: Shared operating system and documentation tools -------
# Sharing the base keeps the builder and runtime Python libraries compatible.
FROM registry.opensuse.org/opensuse/leap:${OPENSUSE_VERSION} AS base

# Documentation:Tools supplies DAPS 4 and SUSE's DocBook stylesheets.
RUN zypper --non-interactive addrepo \
    https://download.opensuse.org/repositories/Documentation:/Tools/16.0/ \
    Documentation_Tools && \
  zypper --gpg-auto-import-keys --non-interactive refresh && \
  zypper --non-interactive install --no-recommends \
    ca-certificates python313 shadow \
    git-core openssh-clients rsync tar gzip \
    daps jing trang libxml2-tools libxslt-tools \
    suse-xsl-stylesheets geekodoc rsvg-convert dejavu-fonts && \
  zypper clean --all

# ------- Stage 2: Build a non-editable Python environment -------
FROM base AS builder

# uv is needed only during the build; pin it rather than following latest.
COPY --from=uv /uv /usr/local/bin/uv

WORKDIR /app
ENV UV_PYTHON_DOWNLOADS=never \
  UV_LINK_MODE=copy

# Install locked runtime dependencies before copying frequently changing source.
# trang in the shared base generates RNG schemas during project packaging.
COPY pyproject.toml uv.lock uv.toml _docbuild_backend.py README.md LICENSE ./
RUN --mount=type=cache,target=/root/.cache/uv \
  uv sync --frozen --python /usr/bin/python3.13 \
    --no-dev --no-install-project --no-editable

COPY src/ ./src/
RUN --mount=type=cache,target=/root/.cache/uv \
  uv sync --frozen --python /usr/bin/python3.13 --no-dev --no-editable

# ------- Stage 3: Runtime without uv or the source checkout -------
FROM base AS runtime

ARG APP_UID=1000
ARG APP_GID=1000

# Configuration, caches, and build output must be writable by the runtime user.
RUN (getent group "${APP_GID}" >/dev/null || groupadd --gid "${APP_GID}" app) && \
  useradd --create-home --uid "${APP_UID}" --gid "${APP_GID}" app && \
  mkdir -p /app /workspace /run/docbuild && \
  chown "${APP_UID}:${APP_GID}" /app /workspace /run/docbuild && \
  chmod 0700 /run/docbuild

COPY --from=builder --chown=${APP_UID}:${APP_GID} /app/.venv /app/.venv
COPY --chown=0:0 --chmod=0644 docker/env.production.toml /etc/docbuild/env.production.toml
RUN chmod 0755 /etc/docbuild

ENV PATH="/app/.venv/bin:${PATH}" \
  HOME=/home/app \
  XDG_RUNTIME_DIR=/run/docbuild \
  LANG=C.UTF-8 \
  PYTHONUNBUFFERED=1

WORKDIR /workspace
USER app

# Arguments after the image name are passed directly to docbuild.
ENTRYPOINT ["docbuild"]
CMD ["--help"]
