.. _create-product:

Creating a Product
==================

A product is the main building block of the portal configuration. To define
a new product, proceed as follows:

#. Determine the product ID.

   This unique ID is used in several places in the configuration.
   The product ID should be short and descriptive.
   In this example, we assume we were asked to create a new product about
   NAS functionality.
   A good product ID would be ``nas``.

#. In your configuration directory :file:`config.d/`, create a new
   directory and the configuration file for the product:

   .. code-block:: shell

        $ mkdir -p config.d/nas
        $ touch config.d/nas/nas.xml

#. Edit the product configuration file and add the following content:

   .. code-block:: xml
      :caption: Example :file:`nas.xml` Configuration
      :name: nas.xml

      <product id="nas" family="f.linux" series="s.pas" rank="...">
         <name>Network Attached Storage</name>
         <acronym>nas</acronym>
         <maintainers>
           <contact>johndoe@example.com</contact>
         </maintainers>

         <!-- ... releases with <docset> elements... -->
      </product>

   * Decide on the ``family`` and ``series`` attributes for this product.

     If you are not sure, you can assign the family to "Linux" (ID=f.linux)
     and the series to "Products & Solutions" (ID=s.pas).

   * For the ``rank`` attribute, assign a number to determine the order
     of the products on the portal. Look at the existing products to
     determine a good rank for your product.

   * Assign a maintainer for the product.

#. Add a docset.

   Continue with section :ref:`create-docset`.
