---
name: run-docs
description: Run docs in the repository.
---

# Build HTML Documentation

1.  Source shell aliases: `source devel/activate-aliases.sh`
2.  Build docs: `makedocs` (fallback: `uv run --frozen make -C docs html`)
3.  Find output in `docs/build/html/`
