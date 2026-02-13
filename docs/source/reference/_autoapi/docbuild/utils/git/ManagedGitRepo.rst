docbuild.utils.git.ManagedGitRepo
=================================

.. py:class:: docbuild.utils.git.ManagedGitRepo(remote_url: str, rootdir: pathlib.Path, gitconfig: pathlib.Path | None = None)

   Manages a bare repository and its temporary worktrees.


   .. py:method:: clear_cache() -> None
      :classmethod:


      Clear the internal update-state cache.

      This is a small, explicit API intended primarily for tests
      to reset class-level state between test cases. It avoids
      tests touching the private `_is_updated` attribute directly.



   .. py:method:: __repr__() -> str

      Return a string representation of the ManagedGitRepo.



   .. py:property:: slug
      :type: str


      Return the slug of the repository.



   .. py:property:: remote_url
      :type: str


      Return the remote URL of the repository.



   .. py:property:: permanent_root
      :type: pathlib.Path


      Return the permanent root directory for the repository.



   .. py:method:: clone_bare() -> bool
      :async:


      Clone the remote repository as a bare repository.

      If the repository already exists, it updates the repo. Once the repo is
      updated, its status is stored. Further calls won't update the repo
      again to maintain a consistent state. This avoids different states betwen
      different times.

      :returns: True if successful, False otherwise.



   .. py:method:: create_worktree(target_dir: pathlib.Path, branch: str, *, is_local: bool = True, options: list[str] | None = None) -> None
      :async:


      Create a temporary worktree from the bare repository.



   .. py:method:: fetch_updates() -> bool
      :async:


      Fetch updates for all branches from the remote.

      :return: True if successful, False otherwise.



   .. py:method:: ls_tree(branch: str, recursive: bool = True) -> list[str]
      :async:


      List all files in a specific branch of the bare repository.

      :param branch: The branch name to inspect.
      :param recursive: Whether to list files in subdirectories.
      :return: A list of file paths found in the branch.


