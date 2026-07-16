docbuild.cli.cmd_repo.cmd_clone
===============================

.. py:module:: docbuild.cli.cmd_repo.cmd_clone

.. autoapi-nested-parse::

   Clone repositories.

   Pass any of the following URLs to clone:

   
   * HTTPS URLs like ``https://github.com/org/repo.git``
   * SSH URLS like git@github.com:org/repo.git
   * Abbreviated URLs like 'org/repo'



Functions
---------

.. autoapisummary::

   docbuild.cli.cmd_repo.cmd_clone.clone


Module Contents
---------------

.. py:function:: clone(ctx: click.Context, repos: tuple[str, Ellipsis]) -> None

   Clone repositories into permanent directory.

   :param repos: A tuple of repository selectors. If empty, all repos are cloned.
   :param ctx: The Click context object.


