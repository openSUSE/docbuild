#!/bin/bash
# If you change this file, update the README.rst file accordingly.
#
# The options that are used in the aliases are:
# --frozen:  Prevents uv from updating the uv.lock file
# --no-sync: Prevents uv from automatically updating or installing
#            anything into the .venv.
#
# Source: https://docs.astral.sh/uv/reference/cli/
#
# This file belongs to the repository https://github.com/openSUSE/docbuild

# For testing:
alias upytest="uv run --frozen --no-sync pytest"

# General Python command
alias upython="uv run --frozen --no-sync python"

# For the interactive Python shell with the project's environment:
alias uipython="uv run --frozen --no-sync ipython --ipython-dir=.ipython"

# For executing the project's script:
alias docbuild="uv run --frozen --no-sync docbuild"

# For managing changelog and news files:
alias towncrier="uv run --frozen --no-sync towncrier"

# For creating docs:
alias makedocs="uv run --frozen --no-sync make -C docs html"
