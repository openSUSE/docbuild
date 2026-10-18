.. _create-xrefs:

Creating Cross-References
=========================

Some products may be related to other resources: products, releases, or other
deliverables. To avoid replication, use a cross-reference.

To create such cross-reference follow this procedure:

#. Find the deliverable you want to link to and copy the ID. For example,
   our ID would be ``nas.1.0.overview``.

#. Find the release (``<docset>``) where you want the deliverable to appear.
   Inside the ``<locale>`` tag, add the following structure:

   .. code-block:: xml
      :name: xref-deliverable
      :caption: Links to another Deliverable

      <locale lang="en-us">
         <!-- [... other deliverables ...] -->
         <deliverable type="xref">
            <xref linkend="nas.1.0.overview" />
         </deliverable>
      </locale>

   Within the list of deliverables, you are free to place the
   cross-reference anywhere.

#. Optionally, customize the cross-reference:

   * To group the reference under a specific heading on the page, add a
     ``category`` attribute to the ``<xref>`` element (e.g.
     ``category="cat.nas"``). If omitted, the category is inherited from the
     target deliverable.
   * To control how the title is displayed, set the ``titleformat``
     attribute on ``<xref>``. Allowed values are ``title`` (default) or
     ``title docset`` (which appends the product and version of the referenced target).
   * To provide a custom description instead of inheriting the target's
     description, add a ``<descriptions>`` child element inside ``<xref>``:

     .. code-block:: xml
        :caption: Cross-Reference with Custom Title Format and Description

        <deliverable type="xref">
           <xref linkend="nas.1.0.overview" category="cat.nas" titleformat="title docset">
              <descriptions>
                 <desc lang="en-us">
                    <p>Overview of NAS architecture and deployment options.</p>
                 </desc>
              </descriptions>
           </xref>
        </deliverable>

   The parent ``<deliverable type="xref">`` element also accepts optional
   attributes:

   * ``xml:id``: Assign an ID if this reference needs to be targeted by
     translated releases.
   * ``gated``: Set to ``"true"`` if access requires authentication.
   * ``sitemap``: Set to ``"false"`` to omit this deliverable from the sitemap.


Valid Target Types
------------------

A cross-reference can point to:

* A **deliverable** (``<deliverable>``)
* A **docset / release** (``<docset>``)
* A **product** (``<product>``)

Referencing any other element with an ``xml:id`` (such as a category
``<item>`` or ``<language>``) is invalid and rejected during validation.


Reference Constraints and Nesting Rules
---------------------------------------

When defining cross-references, the following rules apply:

* **Target existence:** The target ID specified in ``linkend`` must exist.
* **No circular references:** A deliverable cannot reference its own ID.
* **No nested references in English:** An English deliverable cannot
  reference another reference deliverable.
* **Translation indirection (DRY):** A translated deliverable (non-English)
  can reference an English reference deliverable. This allows defining the
  final target ``linkend`` once in English:

  .. code-block:: xml
     :caption: Translation Indirection Example

     <!-- English locale defines the target linkend and carries an xml:id -->
     <locale lang="en-us">
        <branch>main</branch>
        <deliverable type="xref" xml:id="nas.overview.ref">
           <xref linkend="nas.1.0.overview" category="cat.nas"/>
        </deliverable>
     </locale>

     <!-- German translation references the English reference deliverable -->
     <locale lang="de-de">
        <branch>translations</branch>
        <deliverable type="xref">
           <xref linkend="nas.overview.ref"/>
        </deliverable>
     </locale>
