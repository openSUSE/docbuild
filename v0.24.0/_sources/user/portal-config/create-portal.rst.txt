.. _create-portal:

Creating a Portal Configuration
===============================

In this example, we are going to use XInclude to split the configuration into multiple files.

#. Create the directory where you want to store your portal configuration
   files, for example :file:`config.d/`.

#. Create a main portal configuration file named :file:`config.d/portal.xml`
   and add the following content:

   .. code-block:: xml
      :caption: Example :file:`portal.xml` Configuration
      :name: portal.xml

      <portal schemaversion="7.0"
         xmlns:xi="http://www.w3.org/2001/XInclude">
         <!-- <spotlight>...</spotlight> see below -->

         <!-- ... global settings ... -->
         <xi:include href="global_categories.xml"/>
         <xi:include href="global_productfamilies.xml"/>
         <xi:include href="global_series.xml"/>

         <!-- ... product definitions ... -->
         <xi:include href="productA/productA.xml"/>
      </portal>

#. Create the global settings files :file:`global_categories.xml`,
   :file:`global_productfamilies.xml`, and :file:`global_series.xml`
   with the appropriate content for your portal.
   See section :ref:`global-settings` for details on the expected structure.

#. Create a directory for the the first product (in this example, it's
   :file:`productA`) and add a product definition file with the name
   :file:`productA/productA.xml`.
   See section :ref:`product-definition` for details on the expected structure.
