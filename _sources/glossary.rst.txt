Glossary
========

.. glossary::
   :sorted:

   Changelog
      A record of all notable changes made in a project.

      See also :ref:`update-changelog`.

   DAPS
      The *Documentation and Publishing System* (DAPS) is a tool to build documentation from DocBook or ADoc files.
      It is used to generate various output formats such as HTML, PDF, and EPUB.

   DC File
      The *DAPS Configuration File* (DC file) is a configuration file used by DAPS to define parameters for building documentation. For example, it contains information about the entry file, what stylesheets to use, and other build options.

   Deliverable
      The smallest unit of documentation that can be built. It's mapped to a DC File. A deliverable is usually being built in different formats. 

   Docset
      Usually a release or version of a project. For example, ``15-SP6``.

   Doctype
      A formal syntax to identify one or many set of documents.
      The syntax is ``[PRODUCT]/[DOCSET][@LIFECYCLES]/LANGS`` and
      contains product, docset, lifecycles, and language.

      See also :ref:`doctype-syntax`.

   Lifecycle
      The state of a document in its lifecycle.
      For example, ``supported``, ``beta``, ``unsupported`` or ``hidden``.

      See class :class:`~docbuild.models.lifecycle.LifecycleFlag`.

   Product
      A abbreviated name for a SUSE product. For example, ``sles``.

      See class :class:`~docbuild.models.product.Product`.

   Virtual Python Environment (VENV)
      A self-contained and isolate directory that contains a Python
      installation for a particular version of Python, plus several
      additional packages. 
      It is used to avoid conflicts between package versions
      and to manage dependencies for different projects without
      affecting the global Python installation.