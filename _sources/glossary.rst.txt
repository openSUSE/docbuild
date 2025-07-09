Glossary
========

.. glossary::
   :sorted:

   Changelog
      A record of all notable changes made in a project.

      See also :ref:`create-release`.

   DAPS
      The *Documentation and Publishing System* (DAPS) is a tool to build documentation from DocBook or ADoc files.
      It is used to generate various output formats such as HTML, PDF, and EPUB.

      See https://github.com/openSUSE/daps

   DC File
      The *DAPS Configuration File* (DC file) is a configuration file used by DAPS to define parameters for building documentation. For example, it contains information about the entry file, what stylesheets to use, and other build options.

   Deliverable
      The smallest unit of documentation that can be built. It's mapped to a DC File. A deliverable is usually being built in different formats. 

   DocBook
      A semantic markup language based on :term:`XML` used for writing
      and publishing technical documentation.

      See https://www.docbook.org

   Docset
      Usually a release or version of a project. For example, ``15-SP6``.

   Doctype
      A formal syntax to identify one or many set of documents.
      The syntax is ``[PRODUCT]/[DOCSET][@LIFECYCLES]/LANGS`` and
      contains product, docset, lifecycles, and language.

      See also :ref:`doctype-syntax`.

   IPython
      An interactive command-line interface for Python that enhances
      the standard Python shell with additional features.

      See :ref:`use-ipython`.

   Lifecycle
      Describes the distinct stages a product goes through, from its initial introduction to the market until its eventual decline and retirement.

      This project defines the lifecycle stages ``supported``, ``beta``, ``unsupported`` and ``hidden``.

      See class :class:`~docbuild.models.lifecycle.LifecycleFlag`.

   PEP
      *Python Enhancement Proposal (PEP)* are design documents that
      describe a new feature for Python and documenting the design decisions.

      See https://peps.python.org/

   Product
      A abbreviated name for a SUSE product. For example, ``sles``.

      See class :class:`~docbuild.models.product.Product`.

   :file:`pyproject.toml`
      A configuration file used in Python project to define build system
      requirements and project metadata.

      See :pep:`518`

   Pytest
      A testing framework. It's used to write, organize, and run
      tests for your code, from simple unit tests to complex functional
      testing.

      See https://pytest.org

   Ruff
      A fast extensible linter and code formatter to improve code qualitiy
      and enforce style guidelines.

      See https://docs.astral.sh/ruff/

   SemVer
   Semantic Versioning
      A formal convention for assinging version numbers to software
      releases in a ``MAJOR.MINOR.PATCH`` format.

      This structure conveys the nature of the changes, indicating
      if an update introduces incompatible API changes (``MAJOR``),
      adds backward-compatible features (``MINOR``), or contains
      backward-compatible bug fixes (``PATCH``).

      See https://semver.org

   Sphinx
      A documentation generator for Python projects. It converts
      reStructuredText (reST or RST) files into various output formats
      such as HTML, PDF, or manual pages or more.

      See :ref:`build-docs`.

   UV
      A fast package manager which simplifies the building, installing,
      and managing of this project.

      See https://docs.astral.sh/uv/

   VENV
   Virtual Python Environment
      An isolated and self-contained directory that contains a Python
      installation for a particular version of Python, plus several
      additional packages.

      This prevents dependency conflicts by keeping each project's
      requirements separate from other projects and the main system
      installation.

      By convention, a project's VENV is stored in a directory
      named :file:`.venv` located at the root of the project folder.

      See :ref:`prepare-devel-env`.

   XML
      The *eXtensible Markup Language* is a text-based markup
      language used to structure, store, and transport data in
      a format that is both human- and machine-readable.

   XSLT
      The *eXtensible Stylesheet Language for Transformations*
      is a language that transforms XML documents into other
      formats like HTML, plain text, or new XML structures.