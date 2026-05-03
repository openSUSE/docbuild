.. _migrate-config:

Migrating old Docserv Config to new Portal Config
=================================================

.. note::

   This section is used to document the migration process from the old Docserv config to the new Portal Schema. It has to be done only once and is not
   relevant for the regular users of the new Portal Schema or users starting
   from scratch.

With the introduction of the new Portal Schema in version 7, the schema got
a massive overhaul.

Therefore, the old Docserv config is not compatible with the new Portal Schema
anymore  and needs to be migrated. The migration process can be done by a
migration XSLT stylesheet.

You have two options how the result can look like:

* A directory with multiple files.

  This is the recommended approach if you want to organize your configuration
  in a modular way and split the configuration into multiple files.
  It allows for better tracking of changes and easier collaboration.
  Files are referenced by XInclude elements and resolved during the validation
  process.

* A single configuration file.

  This is useful if you want to debug the whole file, want to search for
  specific entries or values, or just prefer a single file.


.. _migration-prerequisites:

Pre-requisites
--------------

Before starting the migration process, ensure you have the following tools installed:

* :command:`xmllint`
* :command:`xsltproc`
* :command:`jing`

Furthermore, you need a Docserv stitchfile:

* Copy it with :command:`scp` from the Docserv server to your local machine.

  The Docserv stitchfile, typically located at
  :file:`/tmp/docserv-stitch-${{DATE}}.xml` (whereas ``${DATE}`` is the
  ISO date of the stitchfile creation in the YYYY-MM-DD format).

* Create it locally by following the instructions in :ref:`prepare-stitchfile`.



.. _prepare-stitchfile:

Preparing the Docserv Stitchfile
--------------------------------

.. note::

   The steps below is what the command :command:`docserv-stitch` does on
   the Docserv server to create the stitchfile. Of course, the script is
   more complex and takes care of validation and other checks, but the above steps are the core of the stitchfile creation process.

   As such, make sure your Docserv configs are valid.


If you don't have access to the Docserv server or prefer to create the stitchfile locally, follow these steps to prepare it:

#. Clone the Docserv config repo if you haven't already:

   .. code-block:: console

      git clone https://gitlab.suse.de/susedoc/docserv-config.git
      cd docserv-config/config.d

#. Set the result file name and path:

   .. code-block:: console

      stitchfile="/tmp/docserv-stitch-$(date --iso-8601).xml"

#. Prepare the header of the stitchfile:

   .. code-block:: console

      cat << EOF > "$stitchfile"
      <?xml version="1.0" encoding="UTF-8"?>
      <docservconfig>
      <!-- <hashes>...</hashes> -->

      EOF

#. Copy content from all categories into result:

   .. code-block:: console

      xmllint --xpath "/*" _categories.xml >> "$stitchfile"

#. Append all config files to the result:

   .. code-block:: console

      xmllint --xpath "/*" [a-z]*.xml >> "$stitchfile"

#. Close the root element:

   .. code-block:: console

      printf "</docservconfig>\n" >> "$stitchfile"


.. _convert-stitchfile:

Converting the Stitchfile
-------------------------

To convert the stitchfile to the new Portal Schema format, use:

* the command :command:`xsltproc` to run the XSLT transformation,
* some of the available XSLT parameters to customize the output as needed (see :ref:`available-xslt-parameters`),
* the migration XSLT stylesheet located at :file:`src/docbuild/config/xml/data/convert-v6-to-v7.xsl`, and
* the stitchfile you prepared in the :ref:`previous section <prepare-stitchfile>`.


.. _available-xslt-parameters:

Available XSLT Parameters
~~~~~~~~~~~~~~~~~~~~~~~~~

The migration XSLT stylesheet accepts the following XSLT parameters:

* ``cat.prefix`` (default ``cat.``)

  The prefix for category IDs.

* ``schemafile`` (default empty)

  The path to the new Portal Schema file (e.g., :file:`portal-config.rnc`).
  The stylesheet recognize the format (RNC or RNG) and changes the ``<?xml-model?>`` PI accordingly.

* ``outputfile`` (default :file:`portal.xml`)

  The name of the main configuration file.

* ``outputdir`` (default :file:`output/`)

  The base directory where the output file(s) will be saved.
  If you want to use the current directory, use ``./``.

* ``use.xincludes`` (default ``false``)

  A boolean parameter that determines whether to use XInclude elements in the output.
  Set it to ``true`` to create a directory with multiple files, or use the
  default to create a single configuration file.

* ``schemaversion`` (default latest)

  The version of the new Portal Schema to target. This is used to determine the necessary transformations to apply during the migration process.


.. _create-config-file-with-multiple-files:

Creating Multiple Files
~~~~~~~~~~~~~~~~~~~~~~~

To create a directory with multiple files, do the following:

#. Run the XSLT transformation with the following command:

   .. code-block:: console

      xsltproc --stringparam outputfile portal.xml \
        --stringparam outputdir "./output/" \
        --param use.xincludes 'true()' \
        src/docbuild/config/xml/data/convert-v6-to-v7.xsl $stitchfile

   This will create all files in the :file:`output/` directory, with the main
   configuration file named :file:`portal.xml` and additional files for
   each category as needed.

#. Copy the generated files to the desired location.

#. Adjust the env configuration to point to the main configuration file,
   use the variable :literal:`paths.config_dir` and :literal:`paths.main_portal_config`.


.. _create-single-config-file:

Creating a Single File
~~~~~~~~~~~~~~~~~~~~~~

To create a single configuration file, , do the following:

#. Run the XSLT transformation with the following command:

   .. code-block:: console

      xsltproc --stringparam schemafile "portal-config.rnc" \
        --stringparam outputfile portal-$(date --iso-8601).xml \
        --stringparam outputdir "./" \
        src/docbuild/config/xml/data/convert-v6-to-v7.xsl $stitchfile

   This will create a file named :file:`portal-<DATE>.xml` in the current directory.

#. Copy the generated output file to the desired location.

#. Adjust the env configuration to point to the main configuration file,
   use the variable :literal:`paths.config_dir` and :literal:`paths.main_portal_config`.
