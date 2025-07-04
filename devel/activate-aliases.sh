#!/bin/bash
# If you change this file, update the README.rst file accordingly.

# For testing:
alias upytest="uv run --frozen pytest"

# For the interactive Python shell with the project's environment:
alias uipython="uv run --frozen ipython --ipython-dir=.ipython"

# For executing the project's script:
alias docbuild="uv run --frozen docbuild"

# For managing changelog and news files:
alias towncrier="uv run --frozen towncrier"

# For creating docs:
alias makedocs="uv run --frozen make -C docs html"
