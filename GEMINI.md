# Project: Docbuild

Docbuild is a project to build documentation either from DocBook or ADoc code. It maintains a set of XML configuration files, clones the repositories, calls the `daps` executable, takes care of metadata and syncs the result deliverables to its target directory.

## General instructions

- Make minimal changes
- Leave the code base untouched as much as possible

## Coding Standards

Ensure the generated code conforms to these points:

- Python Version: Use Python 3.12 or higher. Adapt code style, type hints, and docstrings accordingly.

- Type Hints: Use type hints for functions and variables where feasible.

- Docstrings: Add Sphinx-style docstrings. Document the purpose of the code in a short line, followed by the arguments and their purpose.

- Clarity & Maintainability: Focus on clean, maintainable code. Adhere to the single responsibility principle (one function, one purpose).
