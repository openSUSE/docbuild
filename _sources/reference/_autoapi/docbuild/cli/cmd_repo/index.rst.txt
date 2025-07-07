docbuild.cli.cmd_repo
=====================

.. py:module:: docbuild.cli.cmd_repo

.. autoapi-nested-parse::

   Manage repositories.



Submodules
----------

.. toctree::
   :maxdepth: 1

   /reference/_autoapi/docbuild/cli/cmd_repo/cmd_clone/index
   /reference/_autoapi/docbuild/cli/cmd_repo/cmd_dir/index
   /reference/_autoapi/docbuild/cli/cmd_repo/cmd_list/index
   /reference/_autoapi/docbuild/cli/cmd_repo/process/index


Functions
---------

.. autoapisummary::

   docbuild.cli.cmd_repo.clone
   docbuild.cli.cmd_repo.cmd_dir
   docbuild.cli.cmd_repo.cmd_list
   docbuild.cli.cmd_repo.repo


Package Contents
----------------

.. py:function:: clone(ctx: click.Context, repos: tuple[str, Ellipsis]) -> None

   Clone repositories into permanent directory.

   :param repos: A tuple of repository selectors. If empty, all repos are cloned.
   :param ctx: The Click context object.


.. py:function:: cmd_dir(ctx: click.Context) -> None

   Show the directory path for permanent repositories.

   Outputs the path to the repository directory defined
   in the environment configuration.

   :param ctx: The Click context object.


.. py:function:: cmd_list(ctx: click.Context) -> None

   List the available permanent repositories.

   Outputs the directory names of all repositories defined in the
   environment configuration.
   If no repositories are defined, it outputs a message indicating that
   no repositories are available.

   :param ctx: The Click context object.


.. py:function:: repo(ctx: click.Context) -> None

   Subcommand to validate XML configuration files.

   :param ctx: The Click context object.


