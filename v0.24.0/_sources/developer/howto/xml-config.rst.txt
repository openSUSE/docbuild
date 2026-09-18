XML Config Changes
==================

In this section, we cover how to modify the XML configuration settings, including changing file paths and names for XML configuration files.


.. _xml-config-add-new-element:

Adding a new element
--------------------

To add a new XML element ``<new_element>`` to the Portal schema, follow
these steps:

#. Edit the RNG schema file :file:`src/docbuild/config/xml/data/portal-config.rnc`:

   #. Add the new element definition to the appropriate section of the RNG schema, ensuring it follows the structure and naming conventions of existing elements.

   #. Use the ``db:refname`` element to define the name of the new element.
      Add a description with the ``db.refpurpose`` element:

      .. code-block:: rnc
         :caption: Example of adding a new element to the RNG schema

         [
           db:refname ["new_element"]
           db:refpurpose ["This element is used for ..."]
         ]

   #. Create a ``div`` element and add the appropriate patterns:

      .. code-block:: rnc
         :caption: Example of adding a new element definition to the RNG schema

         div {
           # Add here new attribute definitions if needed
           ds.new-element = element new_element {
             ## This element is used for ...
             # Define the content model for <new_element> here
           }
         }

      Remember that the two hashes (``##``) are used as a RELAX NG comment
      to provide a brief description. This will be used for a XML editor.

   #. Use ``ds.new-element`` to refer to your new element definition somewhere
      else.

#. Adjust the appropriate model in :mod:`docbuild.models.deliverable`.
   Depending on the change, you either need to adjust an existing XPath
   expression, add a new method to access this new element, or both.

#. Write tests. Add positive and negative tests against the Portal schema
   using this new element.

#. Decide if this is something you need to document in the user or
   developer documentation.
