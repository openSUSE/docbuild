Creating Metadata
=================

The :command:`docbuild metadata` subcommand is used to create metadata from a :command:`daps metadata` call. 


.. code-block:: shell
   :caption: Synopsis of :command:`docbuild metadata`

   docbuild metadata [OPTIONS] [DOCTYPES]...

The process does this:

#. Determine the :term:`doctypes <Doctype>` from the command line.
#. Iterate over all :term:`deliverables <Deliverable>` of the doctypes.
#. For each deliverable, call :command:`daps metadata` to create the metadata.
#. Store the metadata in the cache directory of the deliverable. The cache directory is defined in the env configuration file under ``paths.meta_cache_dir``, see also section :ref:`config-docbuild`.