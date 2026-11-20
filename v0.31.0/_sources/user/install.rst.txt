.. _install-docbuild:

Installing docbuild
===================

To install the docbuild tool, follow these steps:


#. :ref:`qs-prepare-installation` - Prepare your environment for installation.

#. :ref:`qs-install-docbuild` - Install the docbuild tool itself.

#. :ref:`get-xml-config` - Get the XML configuration files required for building documentation.

#. :ref:`config-docbuild` - Configure the docbuild tool to suit your needs.




.. _get-xml-config:

Getting the XML configuration
-----------------------------

Formerly known as the *Docserv XML configs*. These configuration files defines the :term:`products <Product>`, their :term:`releases <Docset>`, their :term:`lifecycle <Lifecycle>` status and more.

The tool needs the XML configuration to build the documentation correctly. The XML configuration is not part of the docbuild tool itself, but it is required to run the tool.

Clone the |gl_xmlconfig| to your machine where you can access it easily.
As an alternative, use the `RNC schema <https://www.oasis-open.org/committees/relax-ng/compact-20021121.html>`_ from :gh_tree:`src/docbuild/config/xml/data/` to create your own configuration.
