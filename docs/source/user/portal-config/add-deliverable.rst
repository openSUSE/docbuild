.. _add-deliverable:

Adding Deliverables
===================

A deliverable is a documentation output that docbuild will
either build from source, take as a prebuilt file, or reference from
another deliverable, and publish on the portal.

To add a deliverable, proceed as follows:

#. Identify the docset you want to add the deliverable to.

   If you haven't created a docset yet, create one as described in
   section :ref:`create-product`.

   In this example, we want to add a deliverable to the 1.0
   docset of the NAS product.

#. Choose the deliverable type, such as ``dc`` for :term:`DocBook` XML/:term:`ADoc` sources, ``prebuilt`` for prebuilt files, or ``xref`` for cross-references.

#. Create a deliverable.

   In our example, we have a DocBook XML source and a DC file :file:`DC-NAS-overview`. We want to build HTML, PDF, and
   single HTML output, but not EPUB:

   .. code-block:: xml
      :caption: Example of a Deliverable Built from Source

      <deliverable type="dc" xml:id="nas.1.0.overview">
        <dc file="DC-NAS-overview">
          <format epub="0" html="1" pdf="1" single-html="1" />
        </dc>
      </deliverable>

#. Add as many deliverables as needed.



Build with DAPS
---------------

A deliverable that is built by :command:`daps` from a DocBook XML
or AsciiDoc source file. It needs a DC file and the ``format`` attribute to specify the output formats:

.. code-block:: xml
   :caption: Example of a Deliverable Built from Source
   :name: dc-deliverable-example

   <deliverable type="dc" xml:id="nas.1.0.overview">
      <dc file="DC-NAS-overview">
        <format epub="0" html="1" pdf="1" single-html="1" />
      </dc>
   </deliverable>

The Portal schema expects the ``format`` as a boolean value. Use ``1`` or ``true`` for true and ``0`` or ``false`` for false.


You can use ``<subdir>`` on the ``<locale>`` and ``<dc>`` elements to locate
the source files in the Git repository. The locale subdirectory is combined
with the DC subdirectory, in that order. Both values are relative paths, and
the combined path is normalized, resolving ``.`` and ``..`` components.

.. list-table:: Source directory for a DC deliverable
   :header-rows: 1
   :name: dc-deliverable-subdir-table

   * - Locale ``<subdir>``
     - DC ``<subdir>``
     - Directory used
   * - Not set
     - Not set
     - The Git repository root
   * - :file:`l10n/sles/de-de`
     - Not set
     - :file:`l10n/sles/de-de`
   * - Not set
     - :file:`linux/start/wordpress`
     - :file:`linux/start/wordpress`
   * - :file:`l10n/sles/de-de`
     - :file:`linux/start/wordpress`
     - :file:`l10n/sles/de-de/linux/start/wordpress`
   * - :file:`l10n/sles/de-de`
     - :file:`../common/guide`
     - :file:`l10n/sles/common/guide`

For example, the following configuration combines the locale and DC
subdirectories, then resolves the ``..`` component:

.. code-block:: xml
   :caption: Combining Locale and DC Subdirectories
   :name: dc-deliverable-subdir-example

   <locale lang="en-us">
     <subdir>l10n/sles/de-de</subdir>
     <deliverable type="dc" xml:id="nas.1.0.overview">
       <dc file="DC-NAS-overview">
         <subdir>../common/guide</subdir>
         <format html="1" />
       </dc>
     </deliverable>
   </locale>

The resulting source directory is :file:`l10n/sles/common/guide`.

Build with Prebuilt file (Antora)
---------------------------------

A deliverable that is already built and available as a file.
It can be used for documentation that is not in
DocBook XML or ADoc format or for documentation that is built
by a different tool than :command:`daps`:

.. code-block:: xml
    :caption: Example of a Prebuilt Deliverable
    :name: prebuilt-deliverable-example

    <deliverable xml:id="cn.continuous-delivery.latest-en-index.overview" type="prebuilt" category="cat.cloudnative.rancher">
      <prebuilt>
        <title>Overview</title>
        <url format="html" href="/cloudnative/continuous-delivery/latest/en/index.html"/>
        <descriptions>
          <desc lang="en-us">
            <p>Overview of continuous delivery concepts and practices.</p>
          </desc>
        </descriptions>
      </prebuilt>
    </deliverable>


Build with Cross-Reference
--------------------------

A deliverable that points to another deliverable, product, or release
within the portal configuration:

.. code-block:: xml
    :caption: Example of a Cross-Reference Deliverable
    :name: xref-deliverable-example

    <deliverable type="xref">
      <xref linkend="nas.1.0.overview" category="cat.nas" />
    </deliverable>

See :ref:`create-xrefs` for full details.
