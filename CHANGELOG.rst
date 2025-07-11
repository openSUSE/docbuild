##########
Change Log
##########

All notable changes to this project will be documented in this file.

The format is based on `Keep a Changelog <https://keepachangelog.com/en/1.0.0/>`_, and this project adheres to `Semantic Versioning <https://semver.org/spec/v2.0.0.html>`_.


Changes for the upcoming release can be found in the
`"changelog.d" directory <https://github.com/openSUSE/docbuild/tree/main/changelog.d>`_ of the repository.

..
   Do *NOT* add changelog entries here!

   This changelog is managed by towncrier and is compiled at release time.

   See https://python-semver.rtd.io/en/latest/development.html#changelog
   for details.

.. towncrier release notes start

Version 0.10.0
==============

Bug Fixes
---------

- Replace placeholders in :command:`cli` main command. This ensures that the placeholders in the environment or application configuration are replaced before the subcommands are executed. This is necessary because the subcommands might rely on these placeholders being resolved. (:gh:`20`)
- Correctly convert ``'*'`` for products in :func:`docbuild.model.doctype.Doctype.xpath`

  An XPath ``//*`` created a syntactically correct XPath, but with an
  additional and unnecessary ``[@productid='*']`` predicate. (:gh:`31`)


Improved Documentation
----------------------

- Docs: Improve development and user docs (:gh:`18`)


Features
--------

- Implement cloning of Git repositories

  All repos are "bare" clones, meaning they do not have a working directory.
  This was needed to avoid issues with branches.

  The internal logic is available through some CLI commands:

  * :command:`docbuild repo clone` - Clone a repository into the permanent storage.
    With the help of the :class:`~docbuild.cli.models.repo.Repo` class,
    it can handle different notations of repositories, such as HTTP URLs, SSH URLS, or abbreviated URLs (like ``gh://org/repo``).
  * :command:`docbuild repo dir` - Shows the directory path for permanent storage.
    This is useful for debugging and manual operations.
  * :command:`docbuild repo list` - List all repositories in the permanent storage. (:gh:`3`)
- Support ``.xpath`` method in :class:`~docbuild.model.doctype.Doctype` (:gh:`23`)


Code Refactoring
----------------

- Introduce new :file:`callback.py` file to separate :func:`validate_doctypes` function from the build command. (:gh:`19`)
- Refactor subcommands into packages (:gh:`30`)


Version 0.9.0
=============

Bug Fixes
---------

- Fix problem in logging test

  The test suite reported a ValueError with I/O operations on closed files.
  The fix ensures that we clean all handlers before and after the respective test.


Improved Documentation
----------------------

- Extend design chapter


Features
--------

- Implement :command:`validate` subcommand

  This subcommand is used to validate XML configuration files against a RelaxNG schema. It checks both the structure and semantic correctness of the XML files to ensure they conform to the expected format. (:gh:`5`)
- Implement a timer contextmanager factory in :func:`docbuild.utils.contextmgr.make_timer`.


Infrastructure
--------------

- Create issue templates for bug report, feature request, and
  documentation update. (:gh:`6`)
- Add new type 'refactor' for towncrier
- Format source code with ruff
- GHA: Install xmllint/xsltproc tools
- GHA: Trigger release workflow when tags are pushed
- Implement a bash bump version script. If you pass "major", "minor", or "patch",
  it raises the respective parts. It respects the semver specification.
- Make CLI filenames consistent

  Use prefix ``cmd_`` for real Click commands to distinguish them
  from helper files (like :file:`context.py` which isn't a command).
- Refactor Deliverable to use ``.findtext()``
- Use ``--frozen`` option in aliases to avoid updating :file:`uv.lock`.
  Add new alias :command:`towncrier` (see :file:`devel/activate-aliases.sh`).


Code Refactoring
----------------

- Refactor ``replace_placeholders()`` function

  * Introduce ``PlaceholderResolver`` class to reduce complexity
  * Introduce a ``PlaceholderResolutionError``, derived from KeyError


Version 0.8.0
=============

Breaking Changes
----------------

- Change default of lifecycle in :meth:`~docbuild.models.doctype.Doctype.from_str`

  When you called :meth:`~docbuild.models.doctype.Doctype.from_str` with a string that did not contain a lifecycle, it would default to ``supported``.
  This may prevent XPaths were you want *all* lifecycles.
  This is now changed to ``unknown``.


Features
--------

- Add new list_all_deliverables for XML files

  Generator to yield all deliverables in XML format.
- Implement logging

  Add new functions:

  * :func:`~docbuild.logging.create_base_log_dir`: Create the base log directory if it doesn't exist.
  * :func:`~docbuild.logging.setup_logging`: Set up logging for the application.
  * :func:`~docbuild.logging.get_effective_level`: Return a valid log level, clamped safely.

  The `setup_logging` sets different loggers for the app itself, for Jinja,
  XPath, and Git.


Version 0.7.0
=============

Improved Documentation
----------------------

- Add first docbuild documentation

  * Add sphinx, sphinx-click, sphinx-autoapi, sphinx-copybutton,
    sphinx-autodoc-typehints, and pydata-sphinx-theme to "docs"
    group (pyproject.toml)
  * Add missing ipython in "repl" group
  * Distinguish between a User Guide, Developer Guide, and API Reference
  * Use sphinx-click to "self-document" the docbuild script
  * Use sphinx-autoapi to autogenerate API documentation
  * Fix docstrings in modules, classes etc. to adhere to
    documentation standard


Features
--------

- Implement Deliverable & Metadata classes

  * Deliverable contains an ``etree._Element`` class and represents
    an interface to extract important values from the XML config
  * Metadata is a dataclass that reads the output of "daps metadata" from a file
  * Add test files for each class
  * Add utility function :func:`~docbuild.utils.convert.convert2bool`


Infrastructure
--------------

- Add missing license file (GPL-3.0-or-later)
- Add py.typed in project and pyproject.toml
- Add towncrier to create summarised news files
- Rename ``docbuild.cli.config.{app,env}``

  The names are similar to other files. To make it easier to distinguish,
  these are renamed:

  * ``docbuild.cli.config.{app => application}``
  * ``docbuild.cli.config.{env => environment}``
  * Do the same with the test files
- Update :file:`.gitignore` for :file:`.ipython`


Removed Features
----------------

- Remove tool.setuptools.packages.find
