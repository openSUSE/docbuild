.. _create-spotlight:

Create a Notice ("Spotlight")
=============================

To emphasize a new release or a new product and to draw the attention
of the users, use the ``<spotlight>`` element as a direct child of
``<portal>``. It is shown in a prominent place.

Normally you keep it inside the main configuration file. There is no
need to create a separate file for it, because it is a single element
and not very long.

.. code-block:: xml
   :caption: Synopsis of an ``<spotlight>`` Element
   :name: synopsis-spotlight

   <spotlight linkend="..." />
   <spotlight linkend="...">the text</spotlight>

The element requires a ``linkend`` attribute, which points to the ID
of the object you want to highlight.

You have two options:

* An empty element (``<spotlight linkend="..." />``)

  Use this if you the title is retrieved from the linked object. This is the recommended way, because it is more maintainable.
  If you change the title of the linked object, the spotlight title will be updated automatically.

* An element with text content (``<spotlight linkend="...">the text</spotlight>``)

  Use this if you want to have a custom title for the spotlight, which is different than the title of the linked object.
  This is less maintainable and should be avoided.
  If you change the title of the linked object, you also need to update the spotlight title.
