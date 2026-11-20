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

.. py:function:: run_command(args: collections.abc.Sequence[str], *, cwd: pathlib.Path | None = None, env: dict[str, str] | None = None) -> subprocess.CompletedProcess
   :async:


   Run an external command and capture its output.

   :param args: The command and its arguments separated as tuple elements.
   :param cwd: The working directory for the command.
   :param env: A dictionary of environment variables for the new process.
   :return: a :class:`~subprocess.CompletedProcess` object.
   :raises FileNotFoundError: if the command is not found.


.. py:function:: execute_git_command(*args: str, cwd: pathlib.Path | None = None, extra_env: dict[str, str] | None = None, gitconfig: pathlib.Path | None = None) -> subprocess.CompletedProcess[str]
   :async:


   Execute a Git command asynchronously in a given directory.

   :param args: Command arguments for Git.
   :param cwd: The working directory for the Git command. If None, the
       current working directory is used.
   :param extra_env: Additional environment variables to set for the command.
   :param gitconfig: The path to a separate Git configuration file. If None,
       the default config from etc/git/gitconfig is used.
   :return: a :class:`~subprocess.CompletedProcess` object.
   :raises RuntimeError: If the command fails.
   :raises FileNotFoundError: If `cwd` is specified but does not exist.


