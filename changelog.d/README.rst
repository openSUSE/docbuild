The ``changelog.d`` Directory
=============================

.. This file is also included into the documentation

.. -text-begin-

A "Changelog" is a record of all notable changes made to a project. Such
a changelog, in our case the :file:`CHANGELOG.rst`, is read by our *users*.
Therefor, any description should be aimed to users instead of describing
internal changes which are only relevant to developers.

The directory :file:`changelog.d` contains "newsfragments" which are short
ReST-formatted files. Each newsfragment describes a change in the project. A change is usually from a pull request or issue.
On release, those news fragments are compiled into our :file:`CHANGELOG.rst`.

We recommend to follow the steps to make a smooth integration of your changes:

#. After you have created a new pull request (PR), add a new file into the
   directory :file:`changelog.d`. Each filename follows the syntax::

    <ISSUE>.<TYPE>.rst

   where ``<ISSUE>`` is the GitHub pull request or issue number.
   If you have changes that are not associated with an issue or pull request,
   start with a ``+`` (plus) sign and a short description
   The ``<TYPE>`` is one of:

   * ``breaking``: describes a change that breaks backward compatibility.
   * ``bugfix``: fixes a reported bug.
   * ``deprecation``: informs about deprecation or removed features.
   * ``doc``: improves documentation.
   * ``feature``: adds new user facing features.
   * ``refactor``: refactors code without changing the user facing API.
   * ``removal``: removes obsolete or deprecated features.
   * ``infra``: improves the infrastructure, e.g. build or test system.

   For example, these are valid filenames: ``123.feature.rst``, ``456.bugfix.rst``, ``+add-json.feature.rst`` etc.

   Create the new file with the command:

   .. code-block:: shell
      :caption: Create a new newsfragment file
      :name: towncrier-create

      towncrier create -c "Description" 123.feature.rst

   The file is created int the :file:`changelog.d/` directory.

#. Open the file and describe your changes in RST format.

   * Wrap symbols like modules, functions, or classes into double backticks
     so they are rendered in a ``monospace font``.
   * Prefer simple past tense or constructions with "now".

#. Check your changes with::

     towncrier check

#. Optionally, build a draft version of the changelog file with the command::

    towncrier build --draft

#. Commit all your changes and push it.


This finishes your steps.

On release, the maintainer compiles a new :file:`CHANGELOG.rst` file by running::

   towncrier build

This will remove all newsfragments inside the :file:`changelog.d` directory,
making it ready for the next release.



.. _Towncrier: https://pypi.org/project/towncrier
