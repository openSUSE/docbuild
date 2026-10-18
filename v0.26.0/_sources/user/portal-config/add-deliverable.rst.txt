.. _add-deliverable:

Adding Deliverables
===================

A deliverable is a documentation output that docbuild will
either build from source, take as a prebuilt file, or reference from
another deliverable, and publish on the portal:

* **Build with DAPS**

  A deliverable that is built by :command:`daps` from a DocBook XML
  or AsciiDoc source file. It needs a DC file.

  .. code-block:: xml
     :caption: Example of a Deliverable Built from Source

     <deliverable type="dc" xml:id="nas.1.0.overview">
       <dc file="DC-NAS-overview">
         <format epub="0" html="1" pdf="1" single-html="1" />
       </dc>
     </deliverable>

* **Prebuilt file (Antora)**

  A deliverable that is already built and available as a file.
  It can be used for documentation that is not in
  DocBook XML or ADoc format or for documentation that is built
  by a different tool than :command:`daps`:

  .. code-block:: xml
     :caption: Example of a Prebuilt Deliverable

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

* **Cross-Reference**

  A deliverable that points to another deliverable, product, or release
  within the portal configuration:

  .. code-block:: xml
     :caption: Example of a Cross-Reference Deliverable

     <deliverable type="xref">
       <xref linkend="nas.1.0.overview" category="cat.nas" />
     </deliverable>

  See :ref:`create-xrefs` for full details.

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

      <deliverable type="dc" xml:id="nas.1.0.overview">
        <dc file="DC-NAS-overview">
          <format epub="0" html="1" pdf="1" single-html="1" />
        </dc>
      </deliverable>

#. Add as many deliverables as needed.
