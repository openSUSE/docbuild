.. _create-xrefs:

Creating Cross-References
=========================

Some products may be related to another resources: products, releases, or other
deliverables. To avoid replication, use a cross-reference.

To create such cross-reference follow this procedure:

#. Find the deliverable you want to link to and copy the ID. For example,
   our ID would be ``nas.1.0.overview``.

#. Find the release (``<docset>``) you want to appear the deliverable.
   After the ``<locale>`` tag, add the following structure:

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

The previous procedure showed how to refer to a deliverable. However, it's
not limited to just deliverables. As products and releases have also IDs,
you can use them as target as well.
