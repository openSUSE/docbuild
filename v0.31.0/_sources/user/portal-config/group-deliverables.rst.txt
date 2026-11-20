.. _group-deliverables:

Grouping Deliverables with Categories
=====================================

To group related deliverables together, assign them to a category.
A "category" is a title that is displayed on the release index page.

Categories are defined on different levels:

* Global categories

  Global categories are defined under the ``<portal>`` element.
  By convention, their IDs start with the ``cat.`` prefix.

* Product-specific categories

  "Local" categories that are specific for a product are
  defined under the ``<product>`` element.
  By convention, their IDs start with the ``cat.`` prefix,
  followed by the product ID.
  For example, ``cat.nas`` for the NAS product.

If possible, use global categories to group deliverables.
Only if there are specific groups that are only relevant
for a single product, use product-specific categories.

To use a category, regardless of its scope, assign the category ID to the ``category`` attribute of the deliverable:

.. code-block:: xml
   :caption: Example of a Deliverable with a Category
   :name: category

   <deliverable xml:id="nas.1.0.overview" type="dc" category="cat.nas">
     <dc file="DC-NAS-overview">
       <format html="1" pdf="1" single-html="1" epub="0"/>
     </dc>
   </deliverable>
