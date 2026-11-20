Building Blocks
===============

The portal schema consists of the following main parts:

* ``<portal>``: The root element of the portal configuration.
* Global settings like a spotlight, categories, product families and series.
* ``<product>``: Defines a product, its lifecycle, and its releases.

In the following sections, we will go through these parts in more detail and explain how to use them to configure your documentation portal.


.. note::
   The portal configuration is very flexible and allows you to define
   your own structure and filenames. The following sections provide
   guidelines and recommendations for a good structure, but you are
   free to deviate from them if it suits your needs better.


Portal Definition
-----------------

The portal configuration is defined with the ``<portal>`` root element.
It has a required ``schemaversion="7.0"`` attribute and contains the following child elements:

* ``<spotlight>`` (optional)

  A spotlight section that can be used to highlight important information
  on the portal. See section :ref:`create-spotlight` for more information.

* ``<categories>`` (required)

  The global category definitions for the portal. See section
  :ref:`global-settings`.

* ``<productfamilies>`` (required)

  The global product family definitions. See section
  :ref:`global-settings`.

* ``<series>`` (required)

  The global series definitions. See section :ref:`global-settings`.

* ``<product>`` (one or more required)

  The products of the portal. Each product is defined with a
  ``<product>`` element (or included with ``<xi:include>``). A portal must have at least one product.
  See section :ref:`product-definition` for more information about products.


.. _global-settings:

Global Settings
---------------

These are the following elements:

* ``<categories>``
* ``<productfamilies>``
* ``<series>``


Category settings
~~~~~~~~~~~~~~~~~

Categories are used to group related deliverables together and give them a common title.

Provide at least English (``lang="en-us"``). Other languages are optional.

A ``<category>`` element consists of the following structure:

* A required ``lang`` attribute for the ``<category>`` element itself.
  The language code consists of a language and a country code,
  for example, ``en-us`` for English (United States) or ``de-de`` for
  German (Germany).

* One or more ``<language>`` elements. Each ``<language>`` element
  contains:

  * A required ``xml:id`` attribute, which is used to reference the category
    from deliverables. Per convention, each category ID should start with
    the ``cat.`` prefix.

  * A required ``<title>`` element, which defines the title of the
    category in this language. This will be used as a headline in
    the product index page.

  If needed, additional text can be added as HTML content (limited).

.. code-block:: xml
   :caption: Example :file:`global_categories.xml` Configuration
   :name: global_categories

   <categories>
      <category lang="en-us">
        <language xml:id="cat.about">
          <title>About</title>
        </language>
        <language xml:id="cat.deployment">
          <title>Deployment</title>
        </language>
        <!-- ... -->
      </category>
      <!-- ... other languages ... -->
   </categories>

For translated categories, the situation is a bit different.

Translated categories don't have an ID. They are linked to the original
English category with the ``linkend`` attribute:

.. code-block:: xml
   :caption: Translations of Categories
   :name: category-translations

   <category lang="de-de">
      <language linkend="cat.about">
        <title>Über</title>
      </language>
   </category>

This design was chosen that it makes possible to identify typos in the category IDs.


Product Family Settings
~~~~~~~~~~~~~~~~~~~~~~~

Product families are used to group related products together. They
form the overall "flavor".
On the main entry page of the portal, the "Products & Solutions" tab
lists all product families:

.. code-block:: xml
   :caption: Example global_productfamilies.xml Configuration
   :name: global_productfamilies

   <productfamilies>
     <item xml:id="f.linux">Linux</item>
     <item xml:id="f.cn">Cloud Native</item>
     <item xml:id="f.suse-edge">SUSE Edge</item>
     <item xml:id="f.suse-ai">SUSE AI</item>
   </productfamilies>


Series settings
~~~~~~~~~~~~~~~

Series are used to group products under a global tab. Each product
can be assigned to only one series.

.. code-block:: xml
   :caption: Example :file:`global_series.xml` Configuration
   :name: global_series

   <series>
    <item xml:id="s.pas">Products &amp; Solutions</item>
    <item xml:id="s.sbp">SUSE Best Practices</item>
    <item xml:id="s.trd">Technical References</item>
    <item xml:id="s.rn">Release Notes</item>
   </series>



.. _product-definition:

Product Definition
------------------

A product is defined with the ``<product>`` element.
It contains the following attributes:

* ``xml:id`` (required)

  The unique identifier for the product.
  It must not start with a number and must be unique across
  the whole portal configuration.
  The product ID should be short and descriptive.

* ``path`` (optional)

  A relative directory name for the product, used for building
  the output path. If not specified, the ``xml:id`` is used as the
  fallback.

* ``family`` (required)

  The product family this product belongs to.
  It must match an existing product family ID that is defined
  in the ``<productfamilies>`` element.

* ``series`` (required)

  The series this product belongs to.
  It must match an existing series ID that is defined
  in the ``<series>`` element.

* ``rank`` (optional)

  A number to determine the order of the products on the portal.
  Look at the existing products to determine a good rank for
  your product.

* ``sitemap`` (optional)

  Whether the product should be included in the sitemap.
  By default, all products are included in the sitemap.
  Set this attribute to "false" to exclude the product
  and all of its releases and deliverables from the sitemap.

* ``enabled`` (optional)

  Whether the product is enabled on the portal. Defaults to "true".
  Set to "false" to disable the product without removing it.

* ``gated`` (optional)

  Whether the product is behind a login.
  A gated product cannot be accessed without logging in.
  By default, products are public. Set this attribute to "true"
  to make the product gated.

* ``docset-sort`` (optional)

  The sort order for the product's docsets (releases).
  Allowed values are ``descending`` (default) or ``ascending``.

* ``schemaversion`` (optional)

  The schema version string (e.g. ``7.0``).

Furthermore, a product contains the following child elements:

* ``<name>`` (required)

  The name of the product.

* ``<sortname>`` (optional)

  An alternative name used for sorting products alphabetically.

* ``<acronym>`` (optional)

  An optional acronym for the product.

* ``<maintainers>`` (required)

  The maintainers of the product. A product must have at
  least one maintainer.

* ``<categories>`` (optional)

  Categories that are specific for this product.
  See section :ref:`group-deliverables` for more information
  about categories.

* ``<descriptions>`` (optional)

  A description of the product. This element contains one
  or more ``<desc>`` elements.
  Each ``<desc>`` element has a ``lang`` attribute for the
  language content.

  A ``<desc>`` element contains additional child elements:

  * ``<title>``

    The title of the product shown in the tile on the main
    portal page.

  * HTML elements (``<p>``, ``<div>``, ``<ul>``, etc.)

    Additional description content that is shown on the product
    page. The allowed HTML elements are limited to a subset of
    HTML5.

* ``<docset>`` (required)

  A release of the product. Each product must have at least
  one release defined with a ``<docset>`` element.
  Each ``<docset>`` element contains the deliverables for
  this release for at least English. Other languages are optional.


.. _single-vs-multifile:

Single vs. Multi File Configuration
-----------------------------------

Technically it doesn't matter if you put all the configuration in a
single file or split it into multiple files and refer to them.

A single configuration file may be helpful when you validate the
file or to get a quick overview of the whole configuration. However,
such a file can get very long (>20.000 lines!)

However, for better maintainability and readability, it is highly
recommended to split the configuration into multiple files.

To refer to other files, use XInclude. This is a standard XML mechanism
to include other XML files and looks like this:

.. code-block:: xml
   :caption: Example XInclude

   <xi:include href="path/to/a/different/unit.xml"
      xmlns:xi="http://www.w3.org/2001/XInclude" />

In most cases, the XInclude namespace can be omitted when you put the namespace
into the root element (which you should do).


Directory Hierarchy
-------------------

When splitting the configuration into multiple files, it is recommended to follow a clear directory hierarchy:

* **A main directory**

  Contains all configuration files. This directory can be named
  as you like. In this documentation, we use :file:`config.d/`
  as an example.

* **A main config file**

  Contains the main configuration for the portal.
  This file can be named as you like. In this documentation,
  we use :file:`portal.xml` as an example.
  This file contains the ``<portal>`` root element and includes
  the other files with XInclude.

* **Optional global setting files**

  These file can be placed directly in the main directory or they can
  be kept inside the main config file. This is basically a matter of taste.
  Examples for global setting files are:

  * :file:`global_categories.xml` for categories
  * :file:`global_productfamilies.xml` for product families
  * :file:`global_series.xml` for series

* **Product directories**

  Each product gets its own directory, for example :file:`productA/`.
  This directory contains the product configuration and all releases
  of this individual product.
  For example:

  * :file:`productA/productA.xml` is the main product configuration
    file, which contains the ``<product>`` element.
    It includes all releases of this product with XInclude.
    By convention, this file should be named the same as the directory
    with the :file:`.xml` suffix.
  * :file:`product/release-1.xml` for release 1
  * :file:`product/release-2.xml` for release 2
  * :file:`product/desc/desc.xml` for additional descriptions of the
    product.
    Usually each language gets its own description file,
    for example :file:`product/desc/en-us.xml` for English
    descriptions. Same applies for other languages.
    All languages are included in the :file:`desc.xml` file.

.. code-block:: text
   :caption: Example Directory Hierarchy

   config.d/
   ├── global_categories.xml
   ├── global_productfamilies.xml
   ├── global_series.xml
   ├── portal.xml
   ├── productA/
   │   ├── productA.xml
   │   ├── release-1.xml
   │   └── release-2.xml
   └── [... more products ...]


About IDs and IDREFs
--------------------

The portal configuration relies heavily on ID/IDREFs to reference to
different parts:

* An ID (an "anchor") is an unique identifier for an element.

  IDs are used for products, releases, deliverables, categories, product families, and series.
  It must not start with a number and must be unique across the
  whole portal configuration.
  It is defined with the ``xml:id`` attribute.
  The value of the ID can be freely chosen, but it is recommended to
  use a clear naming convention.

* An IDREF is a cross reference to an ID.

  It is defined with the ``linkend`` attribute and must match an existing ID.
  However, the attributes ``family``, ``series``, and ``category`` are also
  of type IDREFs.


Both ID and IDREF are checked during validation of the portal configuration.
Possible errors can be:

* The ID is not unique.
  For example, if two deliverables have the same ID.
* The ID does not follow the XML naming rules.
  For example, it starts with a number.
* The IDREF does not match any existing ID.
  For example, if a deliverable references a non-existing category.
