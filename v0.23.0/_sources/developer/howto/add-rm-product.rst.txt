Adding or removing a new product
================================

Product names are checked against typos. Whenever you change a product acronym,
you need to update the enum class :class:`docbuild.models.product.Product`, see
the file :file:`src/docbuild/models/product.py`.

The :class:`~docbuild.models.product.Product` members are the source of
truth:

* the member name (for example, ``sle_ha``) maps to the acronym ``sle-ha``
* the member value contains the full product name

Some recommendations, when modifying a product:

* Use the acronym as the enum member name, and the full product name as the value.
* Use only lowercase letters.
* Use underscores in the enum member name. This is automatically converted to hyphens in the acronym.
* Try to keep the enum members in alphabetical order, to make it easier to find them.

Example: If you want to add a new product with the acronym ``sle-foo``and the
full name ``SUSE Linux Enterprise Foo``, you would add the following enum member:

.. code-block:: python
   :caption: Adding a new product to the :class:`Product` class

   class Product(BaseProductEnum):
      # --- snip ---
      sle_foo = "SUSE Linux Enterprise Foo"
