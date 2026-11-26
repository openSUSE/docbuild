.. _bump-version:

Bumping the Version
===================

This project follows :term:`Semantic Versioning <SemVer>`. To bump the version, use the alias :command:`bump-version.sh`
(see :ref:`prepare-devel-env`). For example, if you want to create the next minor release, run:

.. code-block:: console
   :caption: Bumping the minor part
   :name: sh-bump-version

   $ ./devel/bump-version.sh minor

This script automates the versioning process with the following actions:


.. steps::

   .. step:: Validate the inputs

      Validate that all required files and arguments are present and correctly formatted, ensuring the version string adheres to the MAJOR.MINOR.PATCH (Semantic Versioning) format.

   .. step:: Increment the version

      Increment the version according to the :term:`SemVer` rules:

      * ``major``: increments the ``MAJOR`` number and resets ``MINOR`` and ``PATCH`` to zero.
      * ``minor``: increments the ``MINOR`` number and resets the ``PATCH`` part to zero.
      * ``patch``: increments the ``PATCH`` number.

   .. step:: Write back the version and commit the change
