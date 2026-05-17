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

        mkdir -p config.d/nas
        touch config.d/nas/nas.xml

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

#. Add a release.

   Each release is defined with a ``<docset>`` element.
   Depending on the amount of deliverables and the complexity
   of the release, you can either put the
   ``<docset>`` element directly into the product configuration
   file or create a separate file for each release and include
   it in the product configuration.

   We choose the second option and create a file named
   :file:`1.0.xml` for the 1.0 release of the NAS product:

   .. code-block:: xml
      :caption: The 1.0 release of the NAS product :file:`1.0.xml`
      :name: nas.docset

      <docset id="nas-1.0" path="1.0" lifecycle="supported">
        <version>1.0</version>
        <resources>
          <git remote="https://github.com/example/nas.git"/>
          <locale lang="en-us">
            <branch>main</branch>
            <!-- ... deliverables ... -->
          </locale>
        </resources>
      </docset>

   * For the ``<docset>`` element:

     * Add an ``id`` attribute.

       The ID is created by concatenating the product ID and the release version.

     * Add a ``path`` attribute for the ``<docset>`` element.

       The ``path`` is used as part of the URL of the portal. Set it to the version of the release, for example "1.0".

     * Add a ``lifecycle`` attribute for the ``<docset>`` element.

       For new products, set it to "supported".

   * For the ``<resources>`` element:

     * Create a ``<git>`` element to define the Git repository for this release.

     * Create a ``<locale>`` element for the English language (``en-us``) and
       add a ``<branch>`` element to define the Git branch for this release.


#. Add a deliverable.

   Continue with section :ref:`add-deliverable`.
