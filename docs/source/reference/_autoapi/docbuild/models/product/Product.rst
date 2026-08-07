docbuild.models.product.Product
===============================

.. py:class:: docbuild.models.product.Product

   Bases: :py:obj:`BaseProductEnum`

   .. autoapi-inheritance-diagram:: docbuild.models.product.Product
      :parts: 1


   A :class:`~enum.StrEnum` for all known products, including wildcard ``*``.

   The enum value stores the full product name, while :attr:`acronym` exposes
   the canonical short ID used in doctypes and XML product IDs.


   .. py:property:: acronym
      :type: str


      Return the canonical product acronym used in doctypes and XML IDs.
