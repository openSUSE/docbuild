.. _create-links:

Creating external Links
=======================

For some products, additional resources may be required. These can be
links to partners or supporting resources outside of the portal.

As these resources are *external* from a portal point of view, use
the ``<external>`` element:

.. steps::

    .. step:: Find the product and release configuration file

    .. step:: Add the external link to the release

         Find the release (``<docset>``) where you want the deliverable to appear.
         After the ``</resources>`` end tag, add the following structure:

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

    .. step:: Set the link URL and options

         Change the link in the ``<url href="...">`` element.

         Depending on the target format, you can set the ``format``
         attribute. The allowed formats are ``html``, ``single-html``, ``pdf``,
         ``epub``, ``zip``, ``tar``, and ``other``.

         The ``<link>`` element also accepts optional attributes:

         * ``category``: assign a category ID to group the link under a specific section.
         * ``gated``: set to ``true`` if the target resource requires authentication.
         * ``titleformat``: specify how titles are displayed.

    .. step:: Add a description

         Add your description in the ``<desc>`` element.

         The child elements are a limited set of HTML.

    .. step:: Add translations (optional)

         Use an ``<desc lang="...">`` element for each language. Change the
         language in the ``lang`` attribute.

.. seealso::

   Section :ref:`create-xrefs`.
