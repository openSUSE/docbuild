docbuild.utils.shell
====================

.. py:module:: docbuild.utils.shell

.. autoapi-nested-parse::

   Shell command utilities.



Functions
---------

.. autoapisummary::

   docbuild.utils.shell.run_command
   docbuild.utils.shell.execute_git_command


Module Contents
---------------

.. py:function:: run_command(*args: str, cwd: pathlib.Path | None = None, env: dict[str, str] | None = None) -> tuple[int, str, str]
   :async:


   Run an external command and capture its output.

   :param args: The command and its arguments separated as tuple elements.
   :param cwd: The working directory for the command.
   :param env: A dictionary of environment variables for the new process.
   :return: A tuple of (returncode, stdout, stderr).
   :raises FileNotFoundError: if the command is not found.


.. py:function:: execute_git_command(*args: str, cwd: pathlib.Path | None = None, extra_env: dict[str, str] | None = None) -> tuple[str, str]
   :async:


   Execute a Git command asynchronously in a given directory.

   :param args: Command arguments for Git.
   :param cwd: The working directory for the Git command. If None, the
       current working directory is used.
   :param extra_env: Additional environment variables to set for the command.
   :return: A tuple containing the decoded stdout and stderr of the command.
   :raises RuntimeError: If the command fails.
   :raises FileNotFoundError: If `cwd` is specified but does not exist.


