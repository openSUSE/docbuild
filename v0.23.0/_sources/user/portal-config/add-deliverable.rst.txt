.. _add-deliverable:

Adding Deliverables
===================

A deliverable is a documentation output that docbuild will
either build from source or take as a prebuilt file and
publish on the portal:

* Build from source

  A deliverable that is built by :command:`daps` from a DocBook XML
  or ADoc source file. It needs a DC file.

  .. code-block:: xml
     :caption: Example of a Deliverable Built from Source

     <deliverable type="dc" id="nas.1.0.overview">
       <dc file="DC-NAS-overview">
         <format epub="0" html="1" pdf="1" single-html="1" />
       </dc>
     </deliverable>

* Prebuilt file

  A deliverable that is already built and available as a file.
  It can be used for example for documentation that is not in
  DocBook XML or ADoc format or for documentation that is built
  by a different tool than :command:`daps`:

  .. code-block:: xml
     :caption: Example of a Prebuilt Deliverable

     <deliverable id="cn.continuous-delivery.latest-en-index.overview" type="prebuilt" category="cat.cloudnative.rancher">
       <prebuilt>
         <title>Overview</title>
         <url format="html" href="/cloudnative/continuous-delivery/latest/en/index.html"/>
       </prebuilt>
     </deliverable>

* Translations

  A deliverable that is a translation of an existing deliverable.
  It is linked to the original deliverable:

  .. code-block:: xml
     :caption: Example of a Translated Deliverable

     <deliverable type="ref">
       <ref linkend="nas.1.0.overview"/>
     </deliverable>


To add a deliverable, proceed as follows:

#. Identify the release you want to add the deliverable to.

   If you haven't created a release yet, create one as described in
   section :ref:`create-product`.

   In this example, we want to add a deliverable to the 1.0
   release of the NAS product.

#. Create a deliverable.

   In our example, we have a DocBook XML source and a DC file :file:`DC-NAS-overview`. We want to build HTML, PDF, and
   single HTML output, but not EPUB:

   .. code-block:: xml
      :caption: Example of a Deliverable Built from Source

      <deliverable type="dc" id="nas.1.0.overview">
        <dc file="DC-NAS-overview">
          <format epub="0" html="1" pdf="1" single-html="1" />
        </dc>
      </deliverable>

#. Add as many deliverables as needed.
