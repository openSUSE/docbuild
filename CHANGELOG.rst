##########
Change Log
##########

All notable changes to this project will be documented in this file.

The format is based on `Keep a Changelog <https://keepachangelog.com/en/1.0.0/>`_
and adheres to `Semantic Versioning <https://semver.org/spec/v2.0.0.html>`_.


Changes for the upcoming release can be found in the
`"changelog.d" directory <https://github.com/openSUSE/docbuild/tree/main/changelog.d>`_ of the repository.

..
   Do *NOT* add changelog entries here!

   This changelog is managed by towncrier and is compiled at release time.

   See https://opensuse.github.io/docbuild/developer/create-release.html
   for details.

.. towncrier release notes start

Version 0.16.0
==============

Breaking Changes
----------------

- Standardized environment configuration keys in ``env.toml``.
  All temporary paths now use the ``tmp_`` prefix (for example, ``tmp_repo_dir`` instead of ``temp_repo_dir``).
  All directory-related keys now consistently use the ``_dir`` suffix, and previous ``_path`` aliases have been removed. (:gh:`102`)


Improved Documentation
----------------------

- Added a comprehensive technical reference for environment configuration keys and a User Guide section for the ``docbuild config env`` subcommand. (:gh:`110`)
- Updated the documentation copyright year and manifest timestamps, and added Sushant Gaurav in authors list. (:gh:`159`)


Features
--------

- Added :command:`check files` subcommand to verify that all DC files defined in XML configurations exist in their respective remote repositories. The implementation includes an optimization to group checks by repository, significantly reducing Git network overhead. (:gh:`78`)
- Implemented a "smart" :class:`~docbuild.models.serverroles.ServerRole` enum that accepts case-insensitive or abbreviated aliases like ``p``, ``prod``, or ``PRODUCTION``. The new value ``devel`` is an alias for ``testing``.
  Refactor CLI error handling to display Pydantic validation failures in a clean, structured format. (:gh:`113`)


Infrastructure
--------------

- Enabled Python 3.14 for GitHub Action (:gh:`131`)
- Enabled GitHub Action for Dependabot config validation. (:gh:`144`)
- Fix permission issue in forks for coverage comment. (:gh:`148`)


Code Refactoring
----------------

- Refactored environment configuration to separate static path placeholders from runtime dynamic placeholders. This prevents invalid directory creation during configuration validation. (:gh:`108`)
- Refactored JSON structure for robust metadata handling in :func:`~docserv.cli.cmd_metadata.metaprocess.store_productdocset_json`. Introduce Pydantic :class:`~docbuild.models.manifest.Manifest` model to encapsulate document metadata, enhancing validation and serialization. (:gh:`140`)
- Refactored how Git repository URLs are parsed and handled.
  Previously, multiple regular expressions were used to identify different
  URL formats (like HTTPS, SSH, plain, and abbreviated notations).
  These have now been consolidated into a single, more robust regular expression.

  Additionally, the :class:`~docbuild.models.repo.Repo` class was
  enhanced with new attributes (:attr:`~docbuild.models.repo.Repo.branch`,
  :attr:`~docbuild.models.repo.Repo.origin`,
  :attr:`~docbuild.models.repo.Repo.treeurl`) to better manage repository details. (:gh:`167`)


Version 0.15.0
==============

Bug Fixes
---------

- Provide a project-defined Git config to prevent issues with user Git config. (:gh:`118`)


Improved Documentation
----------------------

- Fix documentation issues due to renaming of classes with underscores. (:gh:`137`)


Features
--------

- Introduces the new :command:`docbuild metadata` to automate the process of generating and caching documentation metadata. (:gh:`106`)


Infrastructure
--------------

- Add ``pytest_report_header`` from pytest to print additional information
  in the header. (:gh:`123`)
- Add a new GitHub Action for code formatting issues using Ruff. (:gh:`127`)
- Add coverage for GitHub Action CI workflow. Whenever a pull request is made, the CI will add a coverage report comment. If there are new commits, the comment will be updated. (:gh:`128`)
- Colorize the coverage report in the GitHub Actions comment based on a threshold. (:gh:`130`)
- Reformat the source code with Ruff. Removed unused imports and variables, fix docstrings, and use double quotes in strings. (:gh:`135`)


Code Refactoring
----------------

- Refactor the ``run_command`` and ``run_git_command`` to return :class:`~subprocess.CompletedProcess`
  instead of tuples. This makes the two commands more consistent. (:gh:`121`)
- Improve several tests to improve coverage, readability, reduce dependency to private functions or attributes, and refactor for better modularity. (:gh:`124`)
- In function :func:`validate_rng`, use ``CompletedProcess``  as return object.
  Replace tuple with CompletedProcess. This is used in other functions too and this change makes it consistent with other. (:gh:`125`)
- Reduce complexity of :func:`~docbuild.cli.cmd_validate.process.process_file`. Split into smaller functions. (:gh:`135`)


Version 0.14.0
==============

Bug Fixes
---------

- Fixes incorrect jing command arguments in validate_rng function. (:gh:`80`)
- Fixed a bug where `INFO` and `DEBUG` level logs were not written to the log file. The logging system is now non-blocking and fully configurable via `pyproject.toml`. (:gh:`83`)
- Fix regression in lock files (:gh:`93`)
- GHA: Test for different Python versions (3.12 and 3.13) (:gh:`94`)
- The application now features comprehensive validation for the Environment Configuration (`env.toml`) using Pydantic. This ensures all configuration files strictly adhere to the required schema, enforcing correct data types for fields (for example, paths, URLs, network addresses) and immediately catching errors like missing keys or incorrect values. This change stabilizes the configuration loading process and eliminates runtime errors caused by misconfigured environments. (:gh:`101`)
- Fix case sensitivity in :class:`~docbuild.models.repo.Repo` handling.

  Previously, the model treated URLs with different casing (e.g., ``github.com``
  vs ``GitHub.com``) as unequal. This commit normalizes URLs to ensure that
  casing differences do not result in duplicate or distinct records for the
  same repository. (:gh:`107`)


Improved Documentation
----------------------

- Explain project overview of files and directories (:gh:`74`)
- Add new examples to improves the documentation for the docbuild build command. (:gh:`81`)


Features
--------

- Display current Python version when calling :command:`docbuild --version` (:gh:`70`)
- Support additional RNG validation with lxml. This provides an alternative when jing is not available or preferred. (:gh:`79`)
- Implemented concurrency control to prevent multiple `docbuild` instances from running simultaneously using the same environment configuration file. (:gh:`89`)
- Implemented strict Pydantic validation for the Application Configuration (AppConfig), including a precise, nested schema for all logging parameters (formatters, handlers, loggers). This prevents runtime errors due to configuration typos and ensures data integrity at startup. (:gh:`91`)
- Centralize Git and shell operations for better code reuse across modules (:gh:`99`)


Infrastructure
--------------

- Added macOS to the test CI workflow. (:gh:`76`)
- Added a check to the release workflow to ensure the branch version matches the code's __version__ string. (:gh:`86`)
- Aligned the 'uv' setup in the CI workflow for macOS and Ubuntu to ensure consistent and reliable dependency management across platforms. This resolves a 'docker: command not found' error on the macOS runner. (:gh:`87`)


Code Refactoring
----------------

- Refactor :class:`~docbuild.models.lifecycle.LifecycleFlag`.
  Dynamically created class didn't work well with VSCode and
  attribute access. (:gh:`53`)
- Rename cli command test directories to make it consistent with the
  :file:`src/docbuild/cli` directory. (:gh:`73`)
- Refactored the :class:`~docbuild.models.language.LanguageCode` model to be more idiomatic to Pydantic by removing a custom ``__init__`` initializer and using a :meth:`~docbuild.models.language.LanguageCode.model_validator` method for string parsing. (:gh:`85`)


Version 0.13.0
==============

Improved Documentation
----------------------

- Add instructions how to install VSCode editor (:gh:`56`)
- Clarify some steps when creating a release. (:gh:`59`)
- Improve documentation clarity and usability:

  * Update external links for ``uv``, ``towncrier``, ``reStructuredText``,
    Sphinx, ``jing``, and RNC schema to official resources.
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
