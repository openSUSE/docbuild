---
name: run-docs
description: I need to build the documentation and check the output.
license: GPL-3.0-or-later
compatibility: [opencode, github_copilot, claude]
metadata:
  category: documentation
  audience: [developers]
---

# Build HTML Documentation

## When to use this skill

Use this skill when you need to build the project's documentation from the RST sources.

## How to use this skill

1.  Source shell aliases: `source devel/activate-aliases.sh`
2.  Build docs: `makedocs` (fallback: `uv run --frozen make -C docs html`)
3.  Find output in `docs/build/html/`
