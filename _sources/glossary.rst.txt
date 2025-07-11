Glossary
========

.. glossary::
   :sorted:

   ADoc
   ASCIIDoc
      A lightweight markup language, similar to Markdown, but with a more powerful and extensive syntax designed for writing complex technical documentation, articles, and books.

      See also :term:`DocBook`, https://docs.asciidoctor.org/asciidoc/latest/.

   Argument
      * Python: A value or object that you pass into a function/method.
      * Command-line: Data that the command operates on, usually a file name, a directory path, a URL, or a string of text that the program needs to perform its primary function.

      See also :term:`Option`.

   Asynchronous Programming
      A style of concurrent programming that allows a program to start long-waiting operations (like a network request) and then perform other work while waiting for the original operation to complete.
      With the ``async`` and ``await`` keywords, this method prevents the application from blocking on slow I/O tasks, keeping it efficient and responsive.

   asyncio
      Python's standard library for writing concurrent code using the ``async``/``await`` syntax.

      See also :term:`Asynchronous Programming`

   Changelog
      A record of all notable changes made in a project.

      See also :ref:`create-release`.

   Concurrency
      The ability of a system to manage and make progress on multiple tasks over an overlapping time period. It's about dealing with many things at once, but not necessarily executing them at the exact same instant. A single CPU core can be concurrent by rapidly switching between tasks.

      See also :term:`Asynchronous Programming`, :term:`asyncio`, :term:`Parallelism`

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

      See also :term:`ADoc`, https://www.docbook.org

   Docset
      Usually a release or version of a project. For example, ``15-SP6``.

   Doctype
      A formal syntax to identify one or many set of documents.
      The syntax is ``[PRODUCT]/[DOCSET][@LIFECYCLES]/LANGS`` and
      contains product, docset, lifecycles, and language.

      See section :ref:`doctype-syntax`.

   GIL
   Global Interpreter Lock
      A mutex (a lock) in the standard CPython interpreter that ensures only one thread can execute Python bytecode at any given time within a single process. This lock effectively prevents multi-threaded, CPU-bound Python programs from achieving true parallelism on multi-core processors, as only one thread can run on one core at a time.

      See also :term:`Mutex`.

   IPython
      An interactive command-line interface for Python that enhances
      the standard Python shell with additional features.

      See section :ref:`use-ipython`.

   Lifecycle
      Describes the distinct stages a product goes through, from its initial introduction to the market until its eventual decline and retirement.

      See class :class:`~docbuild.models.lifecycle.LifecycleFlag`.

   Module
      In Python context, a single Python file containing code.

      See also :term:`Package`.

   Mutex
      Short for *Mutual Exclusion*  is a locking mechanism in concurrent programming that ensures only one thread can access a shared resource at any given time. By requiring a thread to "acquire" the lock before using the resource and "release" it afterward, it prevents race conditions and protects shared data from being corrupted.

      See also :term:`Concurrency`.

   Option
      * Python: An optional settings that modify the function's behavior.
      * Command-line: a flag or switch that modifies a program's execution or triggers a specific behavior.

      See also :term:`Argument`.

   Package
      In Python context, a directory containing one or more Python modules.
      The Python interpreter treats a directory as a regular package if it contains a :file:`__init__.py` file.

      See also :term:`Module`

   Parallelism
      The simultaneous execution of multiple tasks at the exact same instant, which requires a system with multiple hardware resources like CPU cores.

      *Parallelism* is about executing multiple tasks simultaneously. This requires multiple CPU cores

      See also :term:`Concurrency`

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

      See section :ref:`build-docs`.

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

      See section :ref:`prepare-devel-env`.

   XML
      The *eXtensible Markup Language* is a text-based markup
      language used to structure, store, and transport data in
      a format that is both human- and machine-readable.

   XSLT
      The *eXtensible Stylesheet Language for Transformations*
      is a language that transforms XML documents into other
      formats like HTML, plain text, or new XML structures.