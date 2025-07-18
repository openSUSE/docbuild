# Source: https://docs.astral.sh/uv/guides/integration/docker/#non-editable-installs
#
# Build it with:
# $ docker build -t docbuild:latest .
#  -- or --
# $ docker buildx build -t docbuild:latest .
#
# If you want to skip the jing installation step, use:
# $ docker build --build-arg WITH_JING=false -t docbuild:latest .

ARG PYTHON_VERSION=3.13-slim

# ------- Stage 1: Build the environment ----------------
FROM python:${PYTHON_VERSION} AS builder

# Create a non-root user
RUN useradd -m app
USER app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Change the working directory
WORKDIR /app

# Install dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
  --mount=type=bind,source=uv.lock,target=uv.lock \
  --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
  uv sync --frozen --no-install-project --no-editable

# Copy the project into the intermediate image
ADD --chown=app:app . /app

# Sync the project
RUN --mount=type=cache,target=/root/.cache/uv \
  uv sync --frozen --no-editable

# ------- Stage 2: Build/provide the application --------
FROM python:${PYTHON_VERSION}

# Allow conditional installation of jing for XML validation
ARG WITH_JING=true

# Install runtime dependencies like jing for XML validation
RUN if [ "$WITH_JING" = "true" ]; then \
        apt-get update && apt-get install -y --no-install-recommends jing && rm -rf /var/lib/apt/lists/*; \
    fi

# Create a non-root user to match the builder stage
RUN useradd -m app

# Copy the environment, but not the source code
COPY --from=builder --chown=app:app /app/.venv /app/.venv

# Set the working directory
WORKDIR /app

# Add the virtual environment's bin directory to the PATH
ENV PATH="/app/.venv/bin:${PATH}"

# Switch to the non-root user for security
USER app

# Run the application
CMD ["docbuild"]
