Running IPython
===============

`IPython <https://ipython.org/>`_ is a powerful interactive shell that can be used for development and testing of the code in this repository.

This repository provides a convenient way to run IPython with the current environment, allowing you to easily import and test the code without needing to modify the Python path:

.. code-block:: shell-session
   :caption: Running IPython using |uv| with alias :ref:`uipython <devel-helpers>`
   :name: running-ipython

   $ uipython

If you are inside an interactive IPython session, you can use the normal
import without changing the import path:

.. code-block:: pycon
   :caption: Interactive IPython session

   [...]
   In [1] from docbuild.cli.context import Doctype
   In [2]: Doctype
   Out[2]: docbuild.models.doctype.Doctype