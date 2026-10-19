Running docbuild
================

If you have installed the docbuild tool from the source code, run it using
:command:`uv run` to ensure that the correct Python version and environment are used.

.. code-block:: shell-session

   $ uv run docbuild --help

In case you have installed different Python versions using :command:`uv python install` (see :ref:`prepare-installation`), specify the Python version to use with the ``-P``/``--python <VERSION>`` option:

.. code-block:: shell-session

   $ uv run --python 3.14 docbuild --help

Command aliases
---------------

Use ``ls`` as a shortcut for ``list`` in the ``cache``, ``config``,
``portal``, and ``repo`` command groups. For example,
:command:`docbuild cache ls --type json` lists JSON cache files. All arguments and
options work as with ``list``. Like ``config list``, ``config ls`` displays
configuration without requiring validation; add ``--validate`` to validate it.
