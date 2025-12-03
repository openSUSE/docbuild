docbuild.utils.git.ManagedGitRepo
=================================

.. py:class:: docbuild.utils.git.ManagedGitRepo(remote_url: str, permanent_root: pathlib.Path)

   Manages a bare repository and its temporary worktrees.


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

      If the repository already exists, it logs a message and returns.

      :returns: True if successful, False otherwise.



   .. py:method:: create_worktree(target_dir: pathlib.Path, branch: str, *, is_local: bool = True, options: list[str] | None = None) -> None
      :async:


      Create a temporary worktree from the bare repository.



   .. py:method:: fetch_updates() -> bool
      :async:


      Fetch updates from the remote to the bare repository.

      :return: True if successful, False otherwise.


