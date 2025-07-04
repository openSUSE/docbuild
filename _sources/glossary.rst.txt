Glossary
========

.. glossary::
   :sorted:

   Changelog
      A record of all notable changes made in a project.
      See also :ref:`update-changelog`.

   Docset
      Usually a release or version of a project. For example, 15-SP6.

   Doctype
      A formal syntax to identify one or many set of documents.
      The syntax is ``[PRODUCT]/[DOCSET][@LIFECYCLES]/LANGS`` and
      contains product, docset, lifecycles, and language.

   Lifecycle
      The state of a document in its lifecycle.
      For example, `supported`, `beta`, `unsupported` or `hidden`.

   Projects
      A name for a SUSE project. For example, `sles`.
      See :class:`~docbuild.models.product.Product`.

   Virtual Python Environment (VENV)
      A self-contained and isolate directory that contains a Python
      installation for a particular version of Python, plus several
      additional packages. 
      It is used to avoid conflicts between package versions
      and to manage dependencies for different projects without
      affecting the global Python installation.