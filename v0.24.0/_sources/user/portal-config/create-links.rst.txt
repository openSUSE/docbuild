.. _create-links:

Creating external Links
=======================

For some products, additional resources may be required. These can be
links to partners or supporting resources outside of the portal.

As these resources are *external* from a portal point of view, use
the ``<external>`` element. Follow this procedure:

#. Find for a product and release the file in your configuration directory.

#. Find the release (``<docset>``) you want to appear the deliverable.
   After the ``</resources>`` end tag and after a ``</internal>`` end tag,
   add the following structure:

   .. code-block:: xml
      :name: external-ref-deliverable
      :caption: Links to external Resource

      <external>
        <link>
          <url href="https://www.example.com/product/" format="html" />
          <descriptions>
            <desc lang="en-us">
              <p>How to ...</p>
            </desc>
          </descriptions>
        </link>
      </external>

#. Change the link in the ``<url href="...">`` element.

   Depending on the target format, you may need to change the ``format``
   attribute too. Currently, only ``html`` and ``pdf`` are supported.

#. Add your descripiton in the ``<desc>`` element.

   The child elements are limited set of HTML.

#. Optionally, add additional translations for the link.

   Use an ``<desc lang="...">`` element for each language. Change the
   language in the ``lang`` attribute.

.. seealso::

   Section :ref:`create-xrefs`.
