# Source: https://docs.astral.sh/uv/guides/integration/docker/#non-editable-installs
#
# Build with a pre-configured DAPS toolchain image from openSUSE.
# This version builds a wheel in a builder stage and installs it in a
# clean runtime environment in the final stage.
#
# Build it with:
# $ docker build -t docbuild:latest .
#

ARG OPENSUSE_VERSION=15.6
ARG IMAGE="registry.opensuse.org/documentation/containers/${OPENSUSE_VERSION}/opensuse-daps-toolchain:latest"

# ------- Stage 1: Build the runtime environment ----------------
FROM ${IMAGE} AS builder

# Create a non-root user.
RUN useradd -m app

# Install uv.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set the working directory to the user's home.
WORKDIR /home/app

# Copy all project source files.
COPY . .

# Build the wheel, create a venv, and install the wheel into it.
# This is all done as root to avoid cache permission issues.
RUN --mount=type=cache,target=/root/.cache/uv \
  set -e; export HOME=/home/app && \
  uv build --wheel && \
  uv venv && \
  uv pip install dist/*.whl

# Fix permissions for the runtime files.
RUN chown -R app:users /home/app

# ------- Stage 2: Create the final, lean image --------
FROM ${IMAGE}

# --- OPTIMIZATION STEP ---
# As root, remove unnecessary files to reduce the final image size.
# This must be done as root, before creating the 'app' user.
# RUN set -x; \
#   rpm -v --erase --nodeps --force python3-cssselect python3 python3-base python3-lxml python3-gobject \
#       ca-certificates cracklib cups-config diffutils fdupes \
#       gio-branding-openSUSE gstreamer gtk2-tools gtk3-data gtk3-schema gtk3-tools \
#       hicolor-icon-theme info ncurses-utils netcfg openSUSE-release perl5 pinentry \
#       Mesa Mesa-dri Mesa-gallium Mesa-libEGL1 Mesa-libGL1 libglvnd libgstgl; \
#   rm -rf /usr/include \
#          /usr/lib/{browser-plugins,gstreamer-*,ca-certificates,keyboxd,locale,perl5,git,gpg-*,getconf,scdaemon,ssh,systemd,tmpfiles.d} \
#          /usr/local/* \
#          /usr/sbin/{fdisk,sfdisk,g13-syshelp,fsck.minix,partx,mkswap,zramctl} \
#          /var/log/* \
#          /var/cache/{zypp,ldconfig,fontconfig,cups} \
#          /var/adm/* \
#          /var/lib/{YaST2,alternatives,ca-certificates,selinux,xkb,misc} || true

# --- DIAGNOSTIC STEP ---
# Add this temporary command to see the size of top-level directories
# before the cleanup step. This helps identify what is taking up space.
# RUN du -sh /usr/lib/* | sort -rh | head -n 20 > /du-usrlib-sort.txt


# Create the same non-root user.
RUN useradd -m app

# Copy only the essential runtime directories from the builder.
# This results in a lean final image without build artifacts or source code.
COPY --from=builder --chown=app:users /home/app/.venv /home/app/.venv
COPY --from=builder --chown=app:users /home/app/.local /home/app/.local

# Switch to the non-root user for security.
USER app

# Set the working directory.
WORKDIR /home/app

# Set the PATH to include the virtual environment's bin directory.
ENV PATH="/home/app/.venv/bin:${PATH}"
ENV LANG=en_US.UTF-8
ENV LC_ALL=en_US.UTF-8
ENV TERM=xterm-256color

# Run the application.
# ENTRYPOINT [ "docbuild" ]
# CMD ["docbuild", "--env-config", "env-production.toml", "--help"]
