.. Using IPython
   =============

.. -text-begin-

This repository provides a convenient way to run :term:`IPython`
with the current environment, allowing you to easily import and
test the code without needing to modify the Python path.

To start an interactive IPython shell with pre-loaded project
modules, use the ``uipython`` alias (see :ref:`devel-helpers`).
This is useful for experimenting with the project's code and for debugging.

.. code-block:: shell-session
   :caption: Running IPython using |uv| with alias :ref:`uipython <devel-helpers>`
   :name: sh-running-ipython

   $ uipython


After the IPython shell is loaded, you can use the normal import without changing the import path:

.. code-block:: pycon
   :caption: Interactive IPython session

   [...]
   In [1]: from docbuild.cli.context import Doctype
   In [2]: Doctype
   Out[2]: docbuild.models.doctype.Doctype