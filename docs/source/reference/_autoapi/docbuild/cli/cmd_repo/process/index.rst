docbuild.cli.cmd_repo.process
=============================

.. py:module:: docbuild.cli.cmd_repo.process

.. autoapi-nested-parse::

   Clone Git repositories from a stitchfile or a list of repository URLs.



Functions
---------

.. autoapisummary::

   docbuild.cli.cmd_repo.process.process


Module Contents
---------------

.. py:function:: process(context: docbuild.cli.context.DocBuildContext, repos: tuple[str, Ellipsis]) -> int
   :async:


   Process the cloning of repositories.

   :param context: The DocBuildContext object containing configuration.
   :param repos: A tuple of repository selectors. If empty, all repos are used.
   :return: An integer exit code.
   :raises ValueError: If configuration paths are missing.


