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
anymore and needs to be migrated. The migration process can be done by a
migration XSLT stylesheet.


The Migration Process
----------------------

The migration process is as follows:

#. Run the migration script with the stitchfile or the configuration directory as input.

#. Validate the converted configuration.
   Although the migration stylesheet attempts to convert the configuration accurately, some manual adjustments may still be required.

#. Fix any issues found during validation.



.. _migration-req-commands:

Required Commands
-----------------

Before starting the migration process, ensure you have the following commands installed:

* :command:`jing`: Used for validating the Portal configuration against the Portal RNC schema.
* :command:`xmllint`: Used for reading the Docserv XML files.
* :command:`xsltproc`: Used for applying the XSLT stylesheet to convert the configuration.
* :command:`xmlstarlet`: Used for detecting the right XML root elements.

The migration script will not work correctly if any of these commands are missing and responds with an error message.


.. _migration-docserv-input:

Docserv Input Data
------------------

Additionally, make sure you have access to the Docserv stitchfile before starting the migration process.

Use one of the following methods:

* Copy it from the Docserv server using :command:`scp`.

  The Docserv stitchfile, typically located at :file:`/tmp/docserv-stitch-${{DATE}}.xml` (whereas ``${DATE}`` is the ISO date of the stitchfile creation in the YYYY-MM-DD format).

* Create it locally by following the instructions in :ref:`prepare-stitchfile`.

* Point to your local copy of the :gl_xmlconfig:`Gitlab repository <-/tree/main/config.d>` containing the :file:`config.d` directory.


.. _migration-script:

Using the migration script
--------------------------

.. topic:: Command Synopsis

   .. parsed-literal::

      migrate-config.sh [OPTIONS] [DOCSERV_STITCHFILE|CONFIGD_DIR]


The migration script requires one of the following inputs:

* A Docserv stitchfile (e.g., :file:`/tmp/docserv-stitch-YYYY-MM-DD.xml`).

  Converting the stitchfile to the new Portal Schema is done by passing it to the migration script:

  .. code-block:: console
    :caption: Using the stitchfile
    :name: migrate-config-stitchfile

    $ tools/migrate-config.sh /tmp/docserv-stitch-YYYY-MM-DD.xml

* A Docserv config directory (e.g., :file:`config.d/`).
  The migration script will create a stitchfile automatically from the directory before processing it.

  Converting the configuration directory to the new Portal Schema is done by passing it to the migration script:

  .. code-block:: console
    :caption: Using the configuration directory
    :name: migrate-config-example

    $ tools/migrate-config.sh $SUSEDOC_DOCSERVCONFIG/config.d/


Either way, by default, the migration script produces the converted configuration in the :file:`output/` directory.


.. _migration-options:

Available options
-----------------

In most cases, the default options are sufficient for the migration process. The converted configuration will be placed in the :file:`output/` directory. Each product will have its configuration stored in a separate subdirectory within :file:`output/`, xinclude processing is enabled by default, and the Portal schema is copied next to the main configuration file. You can override these defaults using the available command-line options described below.


.. program:: migrate-config.sh

.. rubric:: Output options

.. option:: -d DIR, --dir DIR

   Output directory (Default: :file:`output/`).
   Use a trailing slash to mark it as a directory.

.. option:: -o FILE, --output FILE

   Name of the output file (Default: :file:`portal.xml`).

.. option:: -X, --with-xinclude

   Enable xinclude processing. Generates a Portal configuration file with XIncludes statements referencing other files (Default).

.. option:: --without-xinclude

   Disable xinclude processing. Generates a single Portal configuration file without processing XIncludes.

.. rubric:: Schema options

.. option:: -s FILE, --schema FILE

   Schema file in RNC or RNG format (Default: :file:`portal-config.rnc`).
   How the file is used depends on the schema mode, see :ref:`migration-schema-handling`.

.. option:: -S MODE, --schema-mode MODE

   How to provide the schema in the output directory. ``MODE`` is one of:

   * ``copy`` - Copy the schema file (Default).
   * ``link`` - Create an absolute symbolic link to the schema file.
   * ``none`` - Do not provide a schema file.

.. rubric:: General options

.. option:: -h, --help

   Show the help message.


If you use the default options (or pass :option:`--with-xinclude`), the :file:`output/` directory contains these files and subdirectories:

.. code-block:: text

  output/
  ├── categories/
  ├── categories.xml
  ├── [...]
  ├── portal.xml
  ├── portal-config.rnc
  └── [...]


.. _migration-schema-handling:

Schema handling
---------------

The main configuration file contains an ``<?xml-model?>`` processing instruction that references the schema. Editors and validators use it to find the schema. The schema options control both this reference and the schema file in the output directory:

* With the schema modes ``copy`` and ``link``:

  * If you pass :option:`--schema`, the file must exist, otherwise the script stops with an error.
  * If you omit :option:`--schema`, the :file:`portal-config.rnc` from the docbuild repository is used.
  * The schema is placed next to the main configuration file, and the processing instruction references it by its file name only.
  * If the schema already is in the output directory, it is left untouched.

* With the schema mode ``none``, the value of :option:`--schema` is written unchanged into the processing instruction. It can also be a URL or a path that only exists on the target system.

For example, to link a custom schema instead of copying the default one:

.. code-block:: console

   $ tools/migrate-config.sh --schema-mode link --schema ~/schemas/custom.rnc config.d/

.. note::

   Only the main configuration file carries the ``<?xml-model?>`` processing instruction, not the files referenced by XIncludes.
   Schemas that use ``include`` or ``external`` to reference other schema files are not supported, as only the schema file itself is copied or linked.


.. _prepare-stitchfile:

Manually Creating the Docserv Stitchfile
----------------------------------------

.. note::

   This section explains how to manually prepare the Docserv stitchfile.
   The recommended approach is to use the migration script as described in
   :ref:`migrate-config`, but if you need to create the stitchfile manually, follow the steps below.

   The steps below are a simplified version of what the command :command:`docserv-stitch` does on the Docserv server to create the stitchfile.

   Make sure your Docserv configs are valid.


#. Clone the Docserv config repo if you haven't already:

   .. code-block:: console

      $ git clone https://gitlab.suse.de/susedoc/docserv-config.git
      $ cd docserv-config/config.d

#. Set the result file name and path:

   .. code-block:: console

      $ stitchfile="/tmp/docserv-stitch-$(date --iso-8601).xml"

#. Prepare the header of the stitchfile:

   .. code-block:: console

      $ cat << EOF > "$stitchfile"
      <?xml version="1.0" encoding="UTF-8"?>
      <docservconfig>
      <!-- <hashes>...</hashes> -->

      EOF

#. Copy content from all categories into result:

   .. code-block:: console

      $ xmllint --xpath "/*" _categories.xml >> "$stitchfile"

#. Append all config files to the result and resolve any XInclude elements:

   .. code-block:: console

      $ xmllint --xinclude --xpath "/*" [a-z]*.xml >> "$stitchfile"

#. Close the root element:

   .. code-block:: console

      $ printf "</docservconfig>\n" >> "$stitchfile"
