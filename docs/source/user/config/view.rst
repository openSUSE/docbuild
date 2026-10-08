.. _config-viewing-docbuild-config-env:

Viewing the Environment Configuration
=====================================

To see the current merged configuration:

.. code-block:: shell

   docbuild config list

Use the ``--flat`` flag to see the dotted-path format, or use ``--app`` or ``--env`` to view only that configuration.
For details on customizing output styling and colors, see :ref:`config-theme`.


.. _config-viewing-unresolved-placeholders:

Viewing Unresolved Placeholders
-------------------------------

By default, :command:`docbuild config list` displays the configuration with all placeholders resolved. To display placeholders without resolving them (useful for debugging), pass the ``-U`` or ``--unresolved`` option:

.. code-block:: shell

   docbuild config list -U

You can combine ``-U`` / ``--unresolved`` with other flags such as ``--flat``, ``--app``, or ``--env``:

.. code-block:: shell

   docbuild config list -U --flat
   docbuild config list -U --env
