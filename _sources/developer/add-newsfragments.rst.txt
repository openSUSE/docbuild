.. _add-newsfragments:

Adding News Fragments
=====================
 
If your pull request introduces a significant change, add a *news
fragment file* with a high-level summary of your contribution. These fragments
are collected to automatically generate the project's :term:`Changelog` for
each new release.

It needs the Towncrier tool to manage  news fragment files that are assembled into a  changelogs later. The tool is installed automatically when you :ref:`prepare your environment <prepare-devel-env>`.

.. note:: **Using the Towncrier tool**

   While you can create news fragment files manually, using the ``towncrier
   create`` command is highly recommended. It helps prevent common mistakes,
   such as using an invalid fragment type, and ensures the filename follows
   the correct format.


.. include:: ../../../changelog.d/README.rst
   :start-after: -text-begin-
   :end-before: -text-end-
