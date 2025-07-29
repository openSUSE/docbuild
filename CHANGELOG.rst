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

Version 0.13.0
==============

Improved Documentation
----------------------

- Add instructions how to install VSCode editor (:gh:`56`)
- Clarify some steps when creating a release. (:gh:`59`)
- Improve documentation clarity and usability:

  * Update external links for ``uv``, ``towncrier``, ``reStructuredText``, Sphinx, ``jing``, and RNC schema to official resources.
  * Remove ``$`` prefixes from shell command examples for easier copy-pasting.
  * Add a brief explanation for the ``--frozen`` flag usage with :command:`uv sync`.
  * Enhance descriptions and links in the "External tools" section. (:gh:`62`)
- Add new glossary terms (:gh:`68`)
- Add new topic about creating pull requests (:gh:`71`)


Infrastructure
--------------

- Use openSUSE image for GH Action (:gh:`65`)
- Fix docker build/push with lowercase GH repo (:gh:`66`)


Code Refactoring
----------------

- Rename ``docbuild.cli.config`` -> ``docbuild.cli.cmd_config`` to
  make it consistent with other CLI commands. (:gh:`57`)


Version 0.12.0
==============

Bug Fixes
---------

- Fix result of ``process_doctype``. (:gh:`51`)
- Correct ``log.error`` call with arguments (:gh:`52`)


Improved Documentation
----------------------

- Improve user documentation.
  Move "XML configuration" section to user guide. Also change title, set an anchor, and make it clear why we need that. Revise "Configuring the Tool" section. (:gh:`47`)


Features
--------

- Implement metadata from a ``daps metadata`` command. (:gh:`16`)
- Add new context manager :class:`~docbuild.utils.contextmgr.PersistentOnErrorTemporaryDirectory`.
  It is derived from :class:`tempfile.TemporaryDirectory` and has a similar behavior, but it does not delete the temporary directory on exit if an exception occurs. (:gh:`49`)
- Allow optional slash in Doctype syntax.
  Now it's allowed to write instead of ``"*/*/*"`` the syntax ``"/*/*/*"`` and all variations of it. It's the same, but helps to avoid accidental errors. (:gh:`50`)
- Implement async-aware context manager (:gh:`52`)


Version 0.11.0
==============

Bug Fixes
---------

- Fix #26 and add missing checks for references in stitchfile (:gh:`41`)
- Make keys in TOML env file consistent (:gh:`43`)


Improved Documentation
----------------------

- Improve developer documentation

  * Add more glossary terms
  * Use ``:term:`` macro to link to glossary terms
  * Add new sections:
    * "Bumping the Version"
    * "Updating the Project"
    * "Knowning the Tools Config Files"
    * "Developing the Project"
  * Rename "Updating Changelog" -> "Adding News Fragments"
  * Rephrase section about IPython and :file:`devel/README.rst` (:gh:`34`)
- Fix doc warnings from Sphinx

  * Have Sphinx warnings written to :file:`docs/sphinx-warnings.log`.
  * Disable ``inherited-members`` option (it creates warnings from a different docstring format).
  * Slightly restructured Reference guide a bit. "Docbuild CLI" is on the top level now, making :file:`modules.rst` obsolete.
  *  Fix some ReST problems in :file:`checks.py` docstrings (mainly missing linebreaks) (:gh:`38`)
- Add project dependencies, add link to ``susedoc/docserv-config`` repo, and amend the glossary (:gh:`40`)
- Rename ``issue`` macro to ``gh``


Infrastructure
--------------

- Improve release workflow (:gh:`45`)


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
