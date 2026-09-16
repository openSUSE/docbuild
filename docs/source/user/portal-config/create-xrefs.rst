.. _create-xrefs:

Creating Cross-References
=========================

Some products may be related to another resources: products, releases, or other
deliverables. To avoid replication, use a cross-reference.

To create such cross-reference follow this procedure:

#. Find the deliverable you want to link to and copy the ID. For example,
   our ID would be ``nas.1.0.overview``.

#. Find the release (``<docset>``) where you want the deliverable to appear.
   Inside the ``<locale>`` tag, add the following structure:

   .. code-block:: xml
      :name: internal-ref-deliverable
      :caption: Links to another Deliverable

      <locale lang="en-us">
         <!-- [... other deliverables ...] -->
         <deliverable type="xref">
            <ref linkend="nas.1.0.overview" />
         </deliverable>
      </locale>

   Within the list of deliverables, you are free to place the
   cross-reference anywhere.

#. Optionally, if you want to group the reference under a specific title,
   add a ``category`` attribute to the ``<ref>`` element.


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
  final target ``linkend`` once in English.
