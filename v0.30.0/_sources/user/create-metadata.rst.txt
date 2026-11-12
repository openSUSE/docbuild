.. _create-metadata:

Creating Metadata
=================

Docbuild relies on metadata to pass information about the deliverable and its documents to the various tasks that process them. This metadata is stored in a JSON file, which is generated from the deliverable's DAPS XML file.

If you build a deliverable with the :command:`docbuild build` subcommand, the metadata is automatically created and stored in the deliverable's metadata cache directory. However, if you want to create or update the metadata without building the deliverable, you can use the :command:`docbuild metadata` subcommand.

.. code-block:: shell
   :caption: Synopsis of :command:`docbuild metadata`

   docbuild metadata [OPTIONS] [DOCTYPES]...

For example, to create metadata for all deliverables of SLES 16.0, run:

.. code-block:: shell

   docbuild metadata sles/16.0

The result is stored in the directory :ref:`envtoml-paths-json-cache-dir`, which is by default :file:`~/.cache/docbuild/default-env/json`. The metadata for each deliverable is stored in a separate JSON file named after the deliverable's doctype, e.g., :file:`sles/16.0.json`.

The process does this:

#. Determine the :term:`doctypes <Doctype>` from the command line.
#. Iterate over all :term:`deliverables <Deliverable>` of the doctypes.
#. For each deliverable, determine the type:

   #. For a deliverable of ``type="dc"`` call :command:`daps metadata` to create the metadata.
   #. For a deliverable of ``type="prebuilt"``, extract the metadata from the HTML's JSON-LD structure.

#. Store the metadata in the cache directory of the deliverable. The cache directory is defined in the env configuration file under ``paths.meta_cache_dir``, see also section :ref:`config-docbuild`.
