.. _group-deliverables:

Grouping Deliverables with Categories
=====================================

To group related deliverables together, assign them to a category.
A "category" is a title that is displayed on the release index page.

Categories are definied on different levels:

* Global categories

  Global categories are defined under the ``<portal>`` element.
  By conventions, their IDs start with the ``cat.`` prefix.

* Product-specific categories

  "Local" categories that are specific for a product are
  defined under the ``<product>`` element.
  By conventions, their IDs start with the ``cat.`` prefix,
  followed by the product ID.
  For example, ``cat.nas`` for the NAS product.

If possible, use global categories to group deliverables.
Only if there are specific groups that are only relevant
for a single product, use product-specific categories.

To use a category, regardless of its scope, assign the category ID to the ``category`` attribute of the deliverable:

.. code-block:: xml
   :caption: Example of a Deliverable with a Category
   :name: category

   <deliverable id="nas.1.0.overview" type="dc" category="cat.nas">
