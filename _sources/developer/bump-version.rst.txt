.. _bump-version:

Bumping the Version
===================

This project follows :term:`Semantic Versioning <SemVer>`. To bump the version, use the alias :command:`bump-version.sh`
(see :ref:`prepare-devel-env`). For example, if you want to create the next minor release, run:

.. code-block:: shell-session
   :caption: Bumping the minor part
   :name: sh-bump-version

   $ ./devel/bump-version.sh minor

This script automates the versioning process with the following actions:

1. Validates that all required files and arguments are present and correctly formatted, ensuring the version string adheres to the MAJOR.MINOR.PATCH (Semantic Versioning) format.

1. Increments the version according to the :term:`SemVer` rules:

   * ``major``: increments the ``MAJOR`` number and resets ``MINOR`` and ``PATCH`` to zero.
   * ``minor``: increments the ``MINOR`` number and resets the ``PATCH`` part to zero.
   * ``patch``: increments the ``PATCH`` number.

1. It writes back the version and commits the change.